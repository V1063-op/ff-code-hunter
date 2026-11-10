# FF CODE HUNTER

A free, static Chrome dashboard plus a scheduled GitHub Actions scanner. It monitors configured public RSS feeds, extracts code-shaped candidates from linked articles, and asks Gemini to filter candidates. The dashboard shows the newest 15 discovered candidates.

**Important:** Gemini is an extraction assistant, not a code validator. Every result remains `UNVERIFIED` until Garena accepts it. This project does not automatically redeem codes, sign in to game accounts, solve CAPTCHAs, or bypass redemption limits.

## What runs where?

- **Website:** GitHub Pages (free for public repositories).
- **Scheduled scanner:** GitHub Actions, configured for four runs per hour (every 15 minutes, at minutes 7, 22, 37, and 52 UTC).
- **AI extraction:** Gemini API. The API key is stored as a GitHub Actions secret and is never sent to the browser.
- **Storage:** `data/codes.json`, committed by the scheduled workflow.

GitHub may delay scheduled runs during high load. The schedule is not an exact-time guarantee. GitHub documents a minimum scheduled interval of five minutes and notes that scheduled runs can be delayed or dropped during high load.

## 1. Create the project repository

1. Sign in to GitHub and create a **new public repository** named `ff-code-hunter`.
2. Download and unzip this project.
3. Upload all files and folders from this project into the repository's default branch (usually `main`). Keep the `.github` folder.
4. Commit the upload.

A public repository is needed for the free GitHub Pages option. The dashboard and discovered codes will be public. Never put passwords, account details, or API keys in the repository.

## 2. Add your Gemini API key safely

1. Create a Gemini API key in Google AI Studio: https://aistudio.google.com/app/apikey
2. In the GitHub repository, open **Settings → Secrets and variables → Actions**.
3. Choose **New repository secret**.
4. Name it exactly `GEMINI_API_KEY`.
5. Paste the key as the secret value and save.

Do not put the key in `app.js`, `index.html`, `sources.json`, or any public file. If a key is accidentally published, revoke it in AI Studio and create a new one.

The scanner currently uses `gemini-3.8-flash`. If Google changes model availability for your account, edit `GEMINI_MODEL` in `.github/workflows/scan.yml` to a model currently enabled for your API key.

## 3. Turn on GitHub Actions

1. Open the repository's **Actions** tab.
2. If GitHub asks, enable workflows.
3. Select **FF Code Hunter scan**.
4. Choose **Run workflow** once to test it.
5. Open the run and inspect the log. A successful run should end with `Scan complete`.

The workflow runs automatically every 15 minutes after it exists on the default branch. GitHub's schedule uses UTC; this project uses minute 7, 22, 37, and 52 to avoid the top of the hour.

If the workflow cannot push its data update:
- Open **Settings → Actions → General**.
- Under **Workflow permissions**, enable **Read and write permissions**.
- Save, then run the workflow again.

## 4. Publish the website

1. Open **Settings → Pages**.
2. Under **Build and deployment**, choose **Deploy from a branch**.
3. Select branch `main` and folder `/ (root)`.
4. Save.
5. Wait for GitHub Pages to publish. The URL will look like:
   `https://YOUR-GITHUB-USERNAME.github.io/ff-code-hunter/`

Open that URL in Chrome on your phone. Use the browser menu → **Add to Home screen** if you want an app-like shortcut.

## 5. Change the sources

Edit `scanner/sources.json`. The starter feed searches Google News for Sunday Guardian Free Fire redeem-code articles. You can add other public RSS feed URLs to `rss_feeds`.

Example:
```json
{
  "rss_feeds": [
    "https://news.google.com/rss/search?q=site%3Asundayguardianlive.com+Free+Fire+redeem+codes&hl=en-IN&gl=IN&ceid=IN%3Aen"
  ],
  "max_articles_per_scan": 12,
  "article_lookback_hours": 72
}
```

Use sources you are allowed to access. The scanner reads public pages politely and does not attempt to get around logins, paywalls, CAPTCHAs, or site restrictions.

## 6. Alerts and limitations

- The scanner keeps running even when your phone is off.
- The dashboard refreshes its data while open.
- Browser notifications work only while the dashboard is open and the browser has granted notification permission. This static setup does **not** deliver push notifications to a closed browser or powered-off phone.
- GitHub scheduled jobs can be delayed or disabled after long periods without repository activity on public repositories. Check the Actions tab if scans stop.
- Google News RSS and article layouts can change. If a publisher blocks automated requests, that article may be skipped.
- The free Gemini API tier has usage limits. A scan only calls Gemini when it finds candidate strings, but usage is not guaranteed to be free or unlimited. Check AI Studio usage and current terms.

## Troubleshooting

**No codes appear:** Open Actions → latest scan → logs. Check that the secret exists, the feed is reachable, and the article actually contains a code-shaped string near redeem-related wording.

**Dashboard says data unavailable:** Confirm GitHub Pages has finished deploying and that `data/codes.json` exists on `main`.

**The workflow cannot push:** Enable read/write workflow permissions as described above.

**A code is shown but doesn't work:** The app only detects possible code strings. It cannot determine whether a code is expired, region-restricted, account-limited, or already redeemed. Check only through the official Garena page: https://reward.ff.garena.com/

## Project structure

```text
ff-code-hunter/
├── .github/workflows/scan.yml
├── data/codes.json
├── scanner/scan.py
├── scanner/sources.json
├── index.html
├── styles.css
├── app.js
├── .nojekyll
└── README.md
```
