# Royal Murshad AIOS — Public UI Prototype

A responsive, standalone HTML/CSS/JavaScript public-facing product showcase inspired by the supplied Royal Murshad AIOS reference images.

## Files
- `index.html` — application shell and public-facing page
- `styles.css` — responsive black/gold visual system
- `app.js` — app directory, category filters, search, interactive demo chat, modal flows, optional backend reachability test
- `assets/royal-lion.png` — user-provided lion artwork

## Run locally
Open `index.html` in a modern browser. For best behavior, serve the folder with a local static web server. No build step or external JavaScript dependency is required.

## Included functionality
- Responsive sidebar and mobile navigation
- Search across 60 ecosystem entries
- Filters for AI, Work, Automation, and Business
- App preview dialogs with explicit prototype disclaimers
- Interactive local demo chat (prewritten local responses; no AI API call)
- Backend connection test using `/openapi.json`; browser CORS must permit the site origin
- Contact/demo request placeholder clearly reports missing manual configuration
- Keyboard shortcut `Ctrl+K` / `Cmd+K` for search

## Important limitations / manual configuration
1. This is a **public-facing prototype**, not the private admin control panel.
2. No authentication, user accounts, payments, real chat model, voice capture, or privileged computer control is implemented.
3. Backend reachability only proves `/openapi.json` is reachable; it does not validate all feature endpoints.
4. Before public deployment, set the real API base URL and CORS allowlist, implement a secure contact form, add privacy/legal pages, review image rights, and test security, accessibility, mobile layouts, and production hosting.
5. Keep admin routes and operational data behind authentication. Do not expose private registry data or admin endpoints publicly.

## Verification
Run `node test.js` if Node.js is installed. The test checks required files, 60 catalog entries, expected interaction hooks, and prohibited external dependencies. Browser-level checks are still recommended before production deployment.
