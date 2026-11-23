# The Hugging Face page

https://huggingface.co/spaces/christianpure/bible-search is a free static Space: an information page with screenshots and install steps, not the running app. Hugging Face runs Docker apps only on its Pro plan ($9 a month, checked 23 Nov 2026), and the owner chose the free page instead.

It holds two files from this folder: `README.md` (the Space's settings and card) and `index.html` (the page). The screenshots load from this repository's `docs/` folder on GitHub, so they update when those files change.

To change it, edit the two files here, then commit them to the Space while signed in to huggingface.co as christianpure: in Chrome's console on any huggingface.co page, POST the files as base64 to `/api/spaces/christianpure/bible-search/commit/main` (the same method as `output/github-ideas-2026-11-19/hf-sync.js` in the Christian Pure workspace), or upload them on the Space's Files page.

To run the app itself on Hugging Face later, the Space would need the Pro plan, `sdk: docker` with `app_port: 8417`, and a Dockerfile of two lines: `FROM ghcr.io/christianpure/bible-search:0.1.0` and `ENV STUDY_SOURCE=huggingface`.
