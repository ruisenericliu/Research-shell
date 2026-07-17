# FRONTEND.md

Standards for the visualization layer (`src/vis/`).

## Format

- Each visualization is a single self-contained `.html` file with inline CSS and JS
- No build tools, no npm, no bundlers, no compile steps
- The file must be openable directly in a browser with no local server required

## Libraries

- Lightweight CDN-loaded libraries (e.g., Chart.js, Alpine.js) are acceptable
- Keep CDN dependencies to a minimum — prefer vanilla JS when the logic is simple
- React, Vue, Angular, and similar SPA frameworks are out of scope for this project

## Agent Legibility

- Inline JS and CSS are preferred over external files so an agent can read and modify the full visualization in a single file read
- Use clear HTML `id` and `class` names that describe intent — agents navigate by semantics
- Avoid minification; keep code readable

## Location

- All frontend files live in `src/vis/`
- File names should describe the visualization (e.g., `fatfire.html`, `dcf-sensitivity.html`)
