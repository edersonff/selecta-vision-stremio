# SelectaVision Stremio Addon

A community-maintained Stremio addon that provides access to Dragon Ball and Dragon Ball Z from Selecta Vision restoration project.

## Disclaimer

This addon is **independent and unofficial**. It is not affiliated with, maintained by, or endorsed by the Selecta Vision team.

If you are the content owner and believe this should be removed, contact: ederr@ederr.com

## What is this?

A Stremio addon that provides Dragon Ball and Dragon Ball Z episodes from Selecta Vision. The videos are:
- **1080p NTSC 23.976fps**
- **H.264 video**
- **Dual audio** (Japanese, Portuguese)
- **Multiple subtitle tracks**

## How it works

The addon uses a **static + proxy** architecture:
1. Python script scrapes Drime links from MemoriaTV
2. Cloudflare Worker proxies HLS streams with authentication
3. GitHub Actions deploys daily
4. Stremio fetches stream URLs from the Worker

## Stack

- **Python 3.11** - scraping and generation
- **Cloudflare Workers** - HLS proxy with KV storage
- **GitHub Actions** - daily builds and deployments
- **GitHub Pages** - static hosting for addon manifest

## Install in Stremio

1. Open Stremio
2. Go to Settings (gear icon)
3. Click "Add addon"
4. Paste: `https://edersonff.github.io/selecta-vision-stremio/manifest.json`
5. Click "Install"

## Environment Variables

### Cloudflare Worker
- `CF_ACCOUNT_ID` - Cloudflare account ID
- `CF_KV_NAMESPACE_ID` - KV namespace for cookies
- `CF_API_TOKEN` - Cloudflare API token

### Cookie Refresh
- `CF_ACCOUNT_ID`
- `CF_KV_NAMESPACE_ID`
- `CF_API_TOKEN`
- `DRIME_HASH` - Drime share link hash

## Local Development

```bash
# Worker
cd worker
npm install
npx wrangler dev --local

# Addon
cd addon
cd src
python main.py
```

## License

MIT License
