const DATA_URL = "./data/codes.json";
const $ = (id) => document.getElementById(id);

function safeDate(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString();
}
function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  }[c]));
}
function relativeTime(value) {
  if (!value) return "Unknown time";
  const mins = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000));
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} hr ago`;
  return `${Math.floor(hours / 24)} day(s) ago`;
}
function render(data) {
  const all = Array.isArray(data.codes) ? data.codes : [];
  const latest = all.slice().sort((a,b) => new Date(b.found_at_utc) - new Date(a.found_at_utc)).slice(0,15);
  $("totalCount").textContent = all.length;
  $("shownCount").textContent = latest.length;
  $("lastScan").textContent = data.updated_at ? new Date(data.updated_at).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"}) : "—";
  $("scanMessage").textContent = data.scan_status || "Waiting for first scan";
  $("statusPill").textContent = data.updated_at ? "SCAN DATA LOADED" : "WAITING";
  $("statusPill").className = "pill " + (data.updated_at ? "ok" : "muted");
  if (data.last_error) {
    $("errorBox").textContent = "Latest scan note: " + data.last_error;
    $("errorBox").classList.remove("hidden");
  } else {
    $("errorBox").classList.add("hidden");
  }
  $("emptyState").classList.toggle("hidden", latest.length > 0);
  $("codeList").innerHTML = latest.map((item, index) => `
    <article class="code-card">
      <div class="code-top">
        <div class="code">${escapeHTML(item.code)}</div>
        <span class="status">UNVERIFIED</span>
      </div>
      <p class="code-meta">
        Discovered ${escapeHTML(relativeTime(item.found_at_utc))}<br>
        ${escapeHTML(item.source_title || "Public article")}<br>
        ${item.source_url ? `<a href="${escapeHTML(item.source_url)}" target="_blank" rel="noopener">View source ↗</a>` : ""}
      </p>
      <div class="code-bottom">
        <small>#${String(index + 1).padStart(2,"0")} · Not confirmed by Garena</small>
        <button class="copy" data-code="${escapeHTML(item.code)}">Copy code</button>
      </div>
    </article>`).join("");
  document.querySelectorAll(".copy").forEach(button => {
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.code);
        button.textContent = "Copied!";
        setTimeout(() => button.textContent = "Copy code", 1300);
      } catch {
        button.textContent = "Copy unavailable";
      }
    });
  });
  checkForNewCodes(latest);
}
let firstLoad = true;
function checkForNewCodes(codes) {
  const newest = codes.map(x => x.code);
  const previous = JSON.parse(localStorage.getItem("ffhc_seen") || "[]");
  if (!firstLoad && Notification.permission === "granted") {
    const added = newest.filter(code => !previous.includes(code));
    if (added.length) new Notification("FF CODE HUNTER", {body: `${added.length} new code(s) discovered. Open the dashboard to view them.`});
  }
  localStorage.setItem("ffhc_seen", JSON.stringify(newest));
  firstLoad = false;
}
async function loadData() {
  $("refreshBtn").disabled = true;
  $("refreshBtn").textContent = "Loading…";
  try {
    const response = await fetch(`${DATA_URL}?t=${Date.now()}`, {cache:"no-store"});
    if (!response.ok) throw new Error(`Could not load data (${response.status}).`);
    render(await response.json());
  } catch (error) {
    $("errorBox").textContent = error.message + " The scan may not have run yet, or GitHub Pages may still be publishing.";
    $("errorBox").classList.remove("hidden");
    $("statusPill").textContent = "DATA UNAVAILABLE";
    $("statusPill").className = "pill muted";
  } finally {
    $("refreshBtn").disabled = false;
    $("refreshBtn").textContent = "Refresh";
  }
}
$("refreshBtn").addEventListener("click", loadData);
$("notifyBtn").addEventListener("click", async () => {
  if (!("Notification" in window)) {
    alert("This browser does not support web notifications.");
    return;
  }
  const permission = await Notification.requestPermission();
  $("notifyBtn").textContent = permission === "granted" ? "Alerts enabled" : "Alerts blocked";
});
if ("Notification" in window && Notification.permission === "granted") $("notifyBtn").textContent = "Alerts enabled";
loadData();
setInterval(loadData, 120000);
