---
project: skirts-history
url: https://skirts-history.shellnode.lol
vps: ghost
port: 8181
stack: Astro 4, nginx:1.27-alpine, SWAG
standards_version: "2.0"
security: done
ux_ui: done
repo_cleanup: done
readme: done
last_session: "2026-03-10"
has_blockers: false
---

# Project Status — skirts-history

## Last Session
Date: 2026-03-09
Agent: Claude Code

### Completed
- [P1] Added SWAG labels and swag-network to docker-compose.yml — was missing entirely, container would not route through SWAG
- [P1] Updated .dockerignore — added .claude, .github, .gitignore, README.md, *.md, .env, .env.*, .DS_Store
- [P2] Added Permissions-Policy header to nginx.conf
- [P2] Added dotfile blocking (location ~ /\.) to nginx.conf
- [P2] Created README.md from template
- [P3] Added Open Graph meta tags to BaseLayout.astro (og:title, og:description, og:type, og:url)
- [P3] Added inline SVG favicon to BaseLayout.astro (crimson/red square matching --crimson var)

### Incomplete
- None — all identified issues addressed

### Blocked — Needs Matt
- None

## Backlog
- [P3] Assets folder is 97MB (120 WebP images) — total Docker image will be large; consider whether all era images are needed or if count can be trimmed

## Done
- [x] Fix gzip_min_length: 1024 → 256 per STANDARDS spec — 2026-03-10 — commit 52a3c60
- [x] Add MIT LICENSE — 2026-03-10 — commit a1bf3e0
- [x] Remove scroll-behavior: smooth from BaseLayout.astro and [slug].astro (anti-pattern #9) — 2026-03-10
- [x] Security audit — 2026-03-09
- [x] Repo/README cleanup — 2026-03-09
- [x] UX/UI meta audit — 2026-03-09

## Decisions Log
- "Did not change nginx:1.27-alpine to nginx:alpine — pinned version is more secure than floating tag, deviates from STANDARDS wording but not intent" (2026-03-09)
- "Used --crimson (#9b1c1c) for favicon SVG fill — matches project design system rather than STANDARDS default #1A1A1A" (2026-03-09)
- "Removed scroll-behavior: smooth from BaseLayout.astro and [slug].astro — Matt confirmed; kept prefers-reduced-motion block's transition-duration: 0.01ms override, removed only scroll-behavior: auto line from it" (2026-03-10)
- "Set homepage.group=Projects in SWAG labels — generic fallback since no group was specified" (2026-03-09)

## Project Notes
- Astro 4 multi-page static site with TypeScript; NOT a single-file project
- Multi-stage Docker build: node:20-alpine builder → nginx:1.27-alpine server
- 120 WebP images in assets/ across 12 era subdirectories; original JPG/PNG excluded from git via .gitignore
- research.json holds 12 era objects with full prose content
- Has email capture component (EmailCapture.astro) and Trend Revival Clock tool page
- nginx.conf is a root-level events+http config (not just a server block) because multi-stage Dockerfile copies to /etc/nginx/nginx.conf, not /etc/nginx/conf.d/default.conf
