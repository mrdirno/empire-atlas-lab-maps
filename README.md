# Empire Atlas Lab · map films

Code that draws the films on the YouTube channel Empire Atlas Lab. The maps are rendered in code from public historical border data, and the scripts were written with AI help.

## Data
Borders come from [historical-basemaps](https://github.com/aourednik/historical-basemaps) by A. Ourednik, licensed under GPL-3.0. They are approximate: the dataset's BORDERPRECISION field is 1 for these features.

## Films
| Film | Script | Snapshots used |
|---|---|---|
| How long did the Ottomans last? (c.1299–1922) | scripts/render_ottoman_life.py | world_1400, 1492, 1500, 1530, 1600, 1650, 1700, 1715, 1783, 1800, 1815, 1878, 1880, 1900, 1914, 1920 (`Ottoman Empire` / `Ottoman Sultanate`). 1299 is a point at Söğüt, because the data has no 1299 polygon |

Each film is drawn between two consecutive snapshots, so the borders shown between snapshot years are blends, not records.

## Run
Python 3 with numpy and Pillow, plus ffmpeg:
`python3 scripts/render_ottoman_life.py <dir with world_YYYY.geojson> <frames dir>`

## License
GPL-3.0, the same licence as the data. See LICENSE.
