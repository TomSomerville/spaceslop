# Sources audit (2026-11-19)

Every feed below was fetched and parsed with `collect.parse_feed` (the collector's own parser)
on 2026-11-19 before it was added. "Newest" is the newest item date on that day.

## Added to `scripts/sources.json` (rss)

| Name | Feed | Site | Newest | Why |
|---|---|---|---|---|
| SpaceQ | https://spaceq.ca/feed/ | https://spaceq.ca/ | 2026-11-19 | Canadian space industry and policy |
| Via Satellite | https://www.satellitetoday.com/feed/ | https://www.satellitetoday.com/ | 2026-11-18 | Satellite business and satcom |
| Breaking Defense (Space) | https://breakingdefense.com/category/space/feed/ | https://breakingdefense.com/category/space/ | 2026-11-19 | Military space, Space Force, SDA |
| Space Intel Report | https://www.spaceintelreport.com/feed/ | https://www.spaceintelreport.com/ | 2026-11-19 | Satellite and launch business (Peter de Selding) |
| Defense News (Space) | https://www.defensenews.com/arc/outboundfeeds/rss/category/space/?outputType=xml | https://www.defensenews.com/space/ | 2026-11-19 | Military space |
| GeekWire Space | https://www.geekwire.com/space/feed/ | https://www.geekwire.com/space/ | 2026-11-18 | Pacific Northwest space companies (Blue Origin, Amazon Leo, Starlink) |
| TechCrunch Space | https://techcrunch.com/category/space/feed/ | https://techcrunch.com/category/space/ | 2026-11-03 | Space startup funding |
| SpaceWatch.Global | https://spacewatch.global/feed/ | https://spacewatch.global/ | 2026-11-19 | European and Middle East space business |
| China in Space | https://china-in-space.com/feed/ | https://china-in-space.com/ | 2026-11-19 | Chinese launches and programmes |
| ROOM Space Journal | https://room.eu.com/rss/news | https://room.eu.com/ | 2026-11-16 | European space industry news |
| Quilty Space | https://www.quiltyspace.com/blog-feed.xml | https://www.quiltyspace.com/ | 2026-11-19 | Space industry analysis |
| Main Engine Cut Off | https://mainenginecutoff.com/feed | https://mainenginecutoff.com/ | 2026-11-16 | Launch and policy podcast show notes |
| ULA Blog | https://blog.ulalaunch.com/blog/rss.xml | https://www.ulalaunch.com/ | 2026-11-17 | ULA's official blog (mission updates) |

Agency and company feeds (JAXA, CNES, ASI, UKSA, EUMETSAT, EUSPA, Space Force, DARPA, Amazon
Leo, SpaceX IR and others) went into `scripts/companies.json` instead, so they are tracked as
official newsrooms. `scripts/newsrooms.py` now reads RSS/Atom feeds as well as HTML pages.

## Google News queries added

Earth observation, servicing and debris, military space (SDA, SSC, Golden Dome, NRO), satcom and
direct-to-device, India and Japan, Korea/Australia/NZ, Middle East and Latin America, UK and
Nordic spaceports. Each was fetched and returned current results.

## Checked and not added

| Candidate | Result |
|---|---|
| The Space Review | `https://www.thespacereview.com/articles.xml` exists and is current, but it has Windows-1252 bytes under a UTF-8 declaration, so the collector's XML parser rejects it. It would need a lenient decode in `collect.py`. |
| Parabolic Arc | parabolicarc.com now serves the SpaceNews homepage; no Parabolic Arc feed. SpaceNews is already a source. |
| Spaceflight Insider | Placeholder site ("coming back"), feed has 0 items. |
| Orbital Today | Unreachable from this environment (proxy CONNECT 502). |
| Supercluster | https://www.supercluster.com/api/rss.xml works, but much of it is astronomy and culture. Left out to keep the beat. |
| Air & Space Forces Magazine | Feed works, but most items are Air Force, not space. |
| Universe Today | Mostly astronomy (out of beat). |
| Space Explored | Feed works but the newest item was 17 days old. |
| C4ISRNET (space) | Newest item was 2 months old. |
| The Verge (space) | Mixed science and consumer coverage. |
| Everyday Astronaut | Site feed stale since 2025-07; the YouTube channel feed is current but is videos only. |
| The Orbital Index | Feed valid but no issue since 2026-01-07. |
| SpaceNews Andrew Jones author feed | Only one item since August 2026. SpaceNews main feed is already a source. |
| ISRO, IN-SPACe, NSIL | No official feeds. ISRO's press page was added as a newsroom instead. |
| ESA section feeds | ESA's per-section RSS feeds now 404. TopNews (already a source) is the only working one. |
| FAA, FCC, Space Systems Command, NRO, Roscosmos | Block automated fetches (403/Akamai). Not worked around. |

# Stations, Moon/Mars bases and rovers (2026-11-21)

Added to widen coverage of station construction, lunar and Mars base building, and rovers.
Every feed and page was checked with the collector's parser or `newsrooms.check()` on
2026-11-21.

## New feeds in `scripts/sources.json`

| Name | Feed | Newest |
|---|---|---|
| NASA Commercial Space | https://www.nasa.gov/humans-in-space/commercial-space/feed/ | 2026-11-02 |
| NASA Artemis missions | https://www.nasa.gov/missions/artemis/feed/ | 2026-11-12 |
| NASA CLPS | https://www.nasa.gov/missions/artemis/clps/feed/ | 2026-10-20 |
| ESA Human & Robotic Exploration | https://www.esa.int/rss/human-and-robotic-exploration.rss | 2026-11-18 |
| ESA Space Transportation | https://www.esa.int/rss/space-transportation.rss | 2026-11-06 |
| Payload · Lunar | https://payloadspace.com/category/lunar/feed/ | 2026-11-13 |
| NASASpaceflight · Moon / ISS / Mars / Artemis / Rovers | https://www.nasaspaceflight.com/tag/{moon,iss,mars,artemis,rover}/feed/ | 2026-10-19 to 2026-11-20 |
| Space.com · Moon base / ISS / Tiangong | https://www.space.com/feeds/tag/{moon-base,international-space-station,tiangong} | 2026-11-19 to 2026-11-20 |
| SpaceNews · Mars | https://spacenews.com/tag/mars/feed/ | 2026-11-10 |
| The Space Review | https://www.thespacereview.com/articles.xml | 2026-11-16 (now parses: `collect.py` decodes leniently) |
| Magna Petra | https://magnapetra.com/feed/ | 2026-05-26 (posts rarely) |

Tag feeds overlap with the main feeds; `collect.py` already drops duplicates by URL.

Google News queries added: commercial stations; station construction and ISS transition;
Moon base construction; lunar infrastructure and ISRU; rovers; Mars base and missions;
China and international lunar; habitat and ISRU builders; rover and lunar power builders.

## New newsrooms in `scripts/companies.json`

ICON (https://www.iconbuild.com/newsroom), Zeno Power (https://www.zenopower.com/news),
Venturi Space (https://venturi.space/en/feed/?post_type=article), Moon Village Association
(https://moonvillageassociation.org/feed/), Space Applications Services
(https://www.spaceapplications.com/news/feed/), Dymon (https://dymon.co.jp/en/news/),
ISS National Lab (https://www.issnationallab.org/press-releases/feed/), ISRO Human Spaceflight
(https://www.isro.gov.in/Archives.html). Blue Origin's query now also matches Honeybee Robotics.

## Checked, covered by Google News only

| Organisation | Why no newsroom |
|---|---|
| Max Space | No news page; homepage only links to outside coverage |
| AI SpaceFactory | Rebranded to spacefactory.ai; no news section |
| Starpath Robotics | JavaScript-only site, no feed |
| Lunar Resources | Only two posts, no news section |
| Interlune / Astrolab | Already watched; both pages still work |
| Interstellar Lab | Blocks automated fetches (Vercel challenge) |
| Honeybee Robotics | Site now redirects to Blue Origin (rate-limited) |
| OffWorld | News page and feed stale since 2023 |
| Helios | Press feed stale (2025-08) and mostly about steel |
| Spacebit | Site down |
| Toyota Lunar Cruiser | Only Toyota's car-heavy corporate newsroom; JAXA feed already covers it |
| MBRSC | Own site not updated since 2025-03; news goes out via Dubai Media Office |
| KASA (Korea) | Blocks automated fetches |
| Moon Daily / Mars Daily | spacedaily.com feeds are blocked; the standalone domains are now off-topic content-farm sites |
| SpaceNews station/lunar tags | Tag archives stopped updating in 2025 |
