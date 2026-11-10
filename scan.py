import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "codes.json"
SOURCES_FILE = Path(__file__).with_name("sources.json")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
USER_AGENT = "FFCodeHunter/1.0 (public article monitor)"
CODE_RE = re.compile(r"(?<![A-Z0-9])[A-Z0-9]{12,16}(?![A-Z0-9])")
CONTEXT_WORDS = ("redeem", "reward", "code", "free fire", "garena", "claim")

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self.skip += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self.skip:
            self.skip -= 1
    def handle_data(self, data):
        if not self.skip:
            clean = " ".join(data.split())
            if clean:
                self.parts.append(clean)

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def read_json(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()

def parse_feed(url):
    raw = fetch(url)
    root = ET.fromstring(raw)
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if link:
            items.append({"title": title, "url": link, "description": desc, "published": pub})
    return items

def html_to_text(raw):
    parser = TextExtractor()
    parser.feed(raw.decode("utf-8", errors="ignore"))
    return " ".join(parser.parts)

def candidate_codes(text):
    upper = text.upper()
    found = []
    for match in CODE_RE.finditer(upper):
        code = match.group(0)
        if not any(ch.isalpha() for ch in code) or not any(ch.isdigit() for ch in code):
            continue
        start, end = max(0, match.start()-100), min(len(upper), match.end()+100)
        context = upper[start:end]
        if any(word.upper() in context for word in CONTEXT_WORDS):
            found.append({"code": code, "context": text[start:end].replace("\n", " ")})
    unique = {}
    for item in found:
        unique[item["code"]] = item
    return list(unique.values())[:30]

def gemini_filter(candidates, article_title):
    if not GEMINI_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured in repository secrets.")
    prompt = (
        "You are a strict extraction filter. From the candidate strings below, return only "
        "strings that the provided snippets explicitly present as Free Fire / Garena redeem codes. "
        "Never invent, repair, complete, or alter a string. Every returned code MUST exactly equal "
        "one candidate. Exclude player IDs, dates, phone numbers, hashtags, product IDs, and unrelated "
        "alphanumeric strings. If uncertain, return no code. Output JSON only as "
        '{"codes":[{"code":"EXACT_CANDIDATE","reason":"short evidence"}]}.\\n'
        f"Article title: {article_title}\\nCandidates: {json.dumps(candidates, ensure_ascii=False)}"
    )
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0}
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_KEY},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
    text = payload["candidates"][0]["content"]["parts"][0]["text"]
    result = json.loads(text)
    allowed = {item["code"] for item in candidates}
    accepted = []
    for item in result.get("codes", []):
        code = str(item.get("code", "")).upper().strip()
        if code in allowed and code not in {x["code"] for x in accepted}:
            accepted.append({"code": code, "reason": str(item.get("reason", ""))[:180]})
    return accepted

def main():
    if not GEMINI_KEY:
        raise RuntimeError("Add GEMINI_API_KEY as a GitHub Actions repository secret before scanning.")
    config = read_json(SOURCES_FILE, {"rss_feeds": []})
    data = read_json(DATA_FILE, {"updated_at": None, "codes": [], "scan_status": "Not scanned yet", "last_error": None})
    existing = {item.get("code") for item in data.get("codes", [])}
    new_codes = []
    scanned_articles = 0
    article_limit = int(config.get("max_articles_per_scan", 12))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=int(config.get("article_lookback_hours", 72)))
    for feed_url in config.get("rss_feeds", []):
        try:
            entries = parse_feed(feed_url)
        except Exception as exc:
            print(f"Feed error for {feed_url}: {exc}")
            continue
        for entry in entries[:article_limit]:
            try:
                article_html = fetch(entry["url"])
                article_text = html_to_text(article_html)
            except Exception as exc:
                print(f"Article fetch failed: {entry['url']} ({exc})")
                article_text = entry["description"]
            combined = f"{entry['title']} {article_text} {entry['description']}"
            candidates = candidate_codes(combined)
            candidates = [x for x in candidates if x["code"] not in existing]
            if not candidates:
                continue
            scanned_articles += 1
            try:
                accepted = gemini_filter(candidates, entry["title"])
            except Exception as exc:
                print(f"Gemini filter failed for {entry['url']}: {exc}")
                continue
            for result in accepted:
                if result["code"] in existing:
                    continue
                existing.add(result["code"])
                new_codes.append({
                    "code": result["code"],
                    "source_title": entry["title"][:240],
                    "source_url": entry["url"],
                    "found_at_utc": now_iso(),
                    "gemini_note": result["reason"],
                    "status": "unverified"
                })
            time.sleep(1)
    data["codes"] = (new_codes + data.get("codes", []))[:500]
    data["updated_at"] = now_iso()
    data["scan_status"] = f"Scan complete · {scanned_articles} article(s) analysed · {len(new_codes)} new candidate(s)"
    data["last_error"] = None
    write_json(DATA_FILE, data)
    print(data["scan_status"])

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SCAN FAILED: {exc}")
        current = read_json(DATA_FILE, {"codes": []})
        current["updated_at"] = now_iso()
        current["scan_status"] = "Scan failed — check GitHub Actions logs"
        current["last_error"] = str(exc)[:300]
        write_json(DATA_FILE, current)
        raise
