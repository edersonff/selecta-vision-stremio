# SelectaVision Stremio Addon

Stremio addon for Dragon Ball Z in Blu-ray 1080p with Dual Audio.

## About

This addon provides Dragon Ball Z (1989-1996) in high quality, using the Spanish Blu-ray from Selecta Vision as video source.

## Content

**Dragon Ball Z – 1989/1996**
- **Video**: AVC / 4:3 / 23.976 FPS / 1080p
- **Bitrates**: 30.000 kbps / 10.000 kbps / 2.500 kbps
- **Audio**: Dual Audio (PT-BR / JP) in FLAC
  - Portuguese Brazil (Álamo) – FLAC 2.0 / 48 kHz / 313 kbps
  - Japanese – FLAC 2.0 / 48 kHz / 512 kbps

## Source

- **Video**: Selecta Vision Blu-ray (Spain)
- **Audio**: Ripped from Crunchyroll via Prime Video

## Install

1. Open Stremio
2. Go to Settings → Addons
3. Paste: `https://edersonff.github.io/selecta-vision-stremio/manifest.json`
4. Click Install

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  MemoriaTV  │────▶│    Worker    │────▶│   Stremio   │
│   (Drime)   │     │ (Cloudflare) │     │   (Addon)   │
└─────────────┘     └──────────────┘     └─────────────┘
```

- **Python**: Scraper that extracts Drime links from MemoriaTV
- **Cloudflare Worker**: HLS proxy with cookie authentication
- **GitHub Actions**: Auto-refresh every 90 minutes

## Local Development

```bash
# Worker
cd worker
npm install
npx wrangler dev --local

# Addon
cd addon/src
python main.py
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CF_ACCOUNT_ID` | Cloudflare Account ID |
| `CF_KV_NAMESPACE_ID` | KV Namespace for cookies |
| `CF_API_TOKEN` | Cloudflare API Token |
| `DRIME_HASH` | Drime share link hash |

## Disclaimer

This addon is independent and not affiliated with Selecta Vision or MemoriaTV.

If you are the rights holder and want this addon removed, contact: ederr@ederr.com

## Credits

- **Video**: Selecta Vision (Spanish Blu-ray)
- **Audio**: Crunchyroll / Prime Video
- **Original Project**: MemoriaTV (CaNNiBal)

## License

MIT
