# Selecta Vision Stremio Addon

A community-maintained Stremio addon that provides access to restoration projects from various anime sources.

## Disclaimer

This addon is **independent and unofficial**. It is not affiliated with, maintained by, or endorsed by any content owner.

If you are the content owner and believe this should be removed, contact: ederr@ederr.com

## Roadmap

- [x] Dragon Ball (1989-1996) - Dual Audio 1080p - **COMPLETED**
- [ ] Dragon Ball Z (1996-2024) - Ongoing releases
- [ ] Dragon Ball GT
- [ ] Dragon Ball Super
- [ ] Other anime projects

## What is this?

A Stremio addon that provides anime episodes from various restoration projects. The videos are high-quality rips from Blu-ray sources.

## How it works

The addon is **static** - no server required:
1. Python script scrapes source websites
2. Generates JSON files for each episode
3. Deploys to GitHub Pages
4. Stremio fetches these JSON files directly
5. Videos stream directly from source servers

## Stack

- **Python 3.11** - stdlib only, no dependencies
- **GitHub Actions** - daily builds
- **GitHub Pages** - static hosting

## Install in Stremio

Coming soon...

## Local Development

```bash
cd src
python main.py
cd dist
python -m http.server 8080
```

Open: `http://localhost:8080/manifest.json`

## License

MIT License
