# The History of the Skirt

A material archive of the skirt across 5,000 years of civilisation — documented in twelve epochs.

## Live

https://skirts-history.shellnode.lol

## Stack

- Astro 4 static site (TypeScript)
- nginx:1.27-alpine container
- Ghost VPS / Docker
- SSL via SWAG + Cloudflare DNS

## Run Locally

    npm install
    npm run dev

Or via Docker:

    docker build -t skirts-history .
    docker run -p 8181:80 skirts-history

## Deploy

    docker context use vps2
    docker compose up -d --build

## Data Sources

- `research.json` — LLM-generated era content (12 epochs, Ancient Egypt → 21st century)
- `assets/` — WebP images acquired via icrawler (Bing/Baidu sources), one subfolder per era
