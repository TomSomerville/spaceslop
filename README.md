# SpaceSlop

Space industry news aggregator: rocketry, spaceflight, space stations, moon bases, in-space manufacturing. Not astronomy.

Hosted on GitHub Pages at https://spaceslop.beached.lol

## How it works

- `scripts/collect.py` pulls RSS feeds, the Spaceflight News API and Launch Library 2
  (sources in `scripts/sources.json`) and writes new items to `data/candidates.json`.
- A scheduled Claude Code cloud routine follows [ROUTINE.md](ROUTINE.md): it runs the
  collector, picks the newsworthy stories, reads the sources, writes articles into
  `_posts/` and pushes to `main`.
- GitHub Pages builds the Jekyll site from `main`.

To change what gets covered or how it's written, edit `ROUTINE.md`. To add sources,
edit `scripts/sources.json`.
