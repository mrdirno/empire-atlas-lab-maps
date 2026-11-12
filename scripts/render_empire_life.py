# Series defaults (lead 11-12 07:12): question held 1.2 s as a header; event labels at the YEARS size with a ring on the place;
# land mask from a full-claim year (1914); no label on its own ring.
# MAP-MOTION 'How long did X last?' renderer: an empire's whole life, START -> END, 12 s loop. PIL + numpy only.
# Usage: render_empire_life.py <data_dir> <frames_dir> <film.json>  (the film's years, names, events, places, view, camera, text)
# Borders: historical-basemaps by A. Ourednik (GPL-3.0). The start year is a point (start_point) when the data has no polygon for it.
# Dates and labels come from the film json; each film keeps its source map beside it.
import json, math, sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

DATA, OUT = sys.argv[1], sys.argv[2]
CFG = json.load(open(sys.argv[3]))
os.makedirs(OUT, exist_ok=True)
W, H, FPS = 1080, 1920, 30
LON0, LON1, LAT_C = CFG['view']
K = math.cos(math.radians(LAT_C)); SCALE = W / ((LON1 - LON0) * K); MAP_CY = 980
def xy(lon, lat): return ((lon - LON0) * K * SCALE, MAP_CY - (lat - LAT_C) * SCALE)

def mask_for(year, names=None, everything=False):
    m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m)
    for f in json.load(open(f'{DATA}/world_{year}.geojson'))['features']:
        if not f.get('geometry'): continue
        if not everything and f['properties'].get('NAME') not in names: continue
        g = f['geometry']; ps = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        for p in ps:
            d.polygon([xy(*q[:2]) for q in p[0]], fill=255)
            for h in p[1:]: d.polygon([xy(*q[:2]) for q in h], fill=0)
    return m
def arr(im): return np.asarray(im, dtype=np.float32) / 255

YEARS = CFG['years']
NAMES = CFG['names']
START, END = CFG['start'], CFG['end']
land = np.maximum(arr(mask_for(1914, everything=True)), arr(mask_for(1700, everything=True)))   # full-claim year: no false seas
SNAP = {y: arr(mask_for(y, NAMES)) for y in YEARS}
# start year: a small disc at start_point
sx, sy = xy(*CFG['start_point']); yy, xx = np.mgrid[0:H, 0:W]
SNAP[START] = (np.hypot(xx - sx, yy - sy) <= 14).astype(np.float32)
KEYS = [START] + YEARS + [END]
SNAP[END] = SNAP[YEARS[-1]] * CFG.get('end_scale', 1.0)
PEAK = SNAP[CFG['peak_year']]

OCEAN = np.array([12, 18, 30], np.float32); LAND = np.array([56, 60, 66], np.float32)
RED = np.array([196, 28, 44], np.float32); GOLD = np.array([255, 196, 0], np.float32)
base = OCEAN * (1 - land[..., None]) + LAND * land[..., None]

DISPLAY = '/System/Library/Fonts/Supplemental/Rockwell.ttc'
def font(s, idx=2):
    try: return ImageFont.truetype(DISPLAY, s, index=idx)
    except Exception: return ImageFont.truetype(DISPLAY, s, index=0)
def text_c(d, y, s, size, fill=(255, 255, 255), idx=2):
    f = font(size, idx); w = d.textlength(s, font=f)
    while w > W - 90 and size > 30:                     # shrink to fit the frame with a 45 px margin
        size -= 4; f = font(size, idx); w = d.textlength(s, font=f)
    d.text(((W - w) / 2, y), s, font=f, fill=fill, stroke_width=max(3, size // 16), stroke_fill=(0, 0, 0))
def ease(t): return t * t * (3 - 2 * t)

def empire_at(year):
    for a, b in zip(KEYS, KEYS[1:]):
        if a <= year <= b:
            p = (year - a) / (b - a) if b > a else 1.0
            return SNAP[a] * (1 - p) + SNAP[b] * p
    return SNAP[END]

def paint(emp, ghost=None):
    img = base.copy()
    if ghost is not None: img = img * (1 - ghost[..., None] * 0.35) + RED * ghost[..., None] * 0.35
    img = img * (1 - emp[..., None] * 0.93) + RED * emp[..., None] * 0.93
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

PLACES = {int(k): tuple(v) for k, v in CFG['places'].items()}
def zoom_xy(plon, plat, z, lon, lat):
    px, py = xy(plon, plat)
    if z <= 1.0: return px, py
    cx, cy = xy(lon, lat); cw, ch = W / z, H / z
    x0 = min(max(cx - cw / 2, 0), W - cw); y0 = min(max(cy - ch / 2, 0), H - ch)
    return (px - int(x0)) * z, (py - int(y0)) * z

def zoomed(im, z, lon, lat):
    if z <= 1.0: return im
    cx, cy = xy(lon, lat); cw, ch = W / z, H / z
    x0 = min(max(cx - cw / 2, 0), W - cw); y0 = min(max(cy - ch / 2, 0), H - ch)
    return im.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.LANCZOS)

EVENTS = [tuple(e) for e in CFG['events']]
T0, T1, DUR = 0.5, 10.8, 12.0     # clock runs START -> END between T0 and T1
def year_at(t):
    if t < T0: return float(START)
    if t >= T1 - 0.7: return float(END)
    return START + (END - START) * (t - T0) / (T1 - 0.7 - T0)

def frame(t):
    yr = year_at(t)
    # camera: tight on the start point, out to wide by turn_year, slow push toward camera.end during the fall
    C = CFG['camera']; PK = CFG['turn_year']
    if t < T0: z, lon, lat = 1.0, *C['wide']
    else:
        g = min(max((yr - START) / (PK - START), 0), 1)
        if yr <= PK: z, lon, lat = C['z0'] - (C['z0'] - 1.0) * ease(g), C['start'][0] + (C['wide'][0] - C['start'][0]) * g, C['start'][1] + (C['wide'][1] - C['start'][1]) * g
        else:
            h = (yr - PK) / (END - PK) if yr < END else 1.0
            extra = max(0.0, t - (T1 - 0.7)) * 0.15
            z, lon, lat = 1.0 + C['z_end_add'] * ease(h) + extra, C['wide'][0] + (C['end'][0] - C['wide'][0]) * h, C['wide'][1] + (C['end'][1] - C['wide'][1]) * h
    if t < T0:
        im = zoomed(paint(PEAK * 0.45), 1.0, *C['wide']); d = ImageDraw.Draw(im)
        text_c(d, 200, CFG['q1'], 76); text_c(d, 300, CFG['q2'], 88, fill=(255, 196, 0))
        return im
    if t >= T1:
        # end card 1.2 s over moving picture: the last remnant shrinks back to the start point (the loop)
        w = ease((t - T1) / (DUR - T1))
        emp = SNAP[END] * (1 - w) + SNAP[START] * w
        z_e = 1.0 + C['z_end_add']
        el = C.get('loop_to', C['start'])
        cf = C.get('card_from', C['end'])
        im = zoomed(paint(emp), z_e + 0.35 * w, cf[0] + (el[0] - cf[0]) * w, cf[1] + (el[1] - cf[1]) * w); d = ImageDraw.Draw(im)
        text_c(d, 190, f'{END - START:,} YEARS', 150 if END - START < 1000 else 130, fill=(255, 196, 0))
        text_c(d, 1250, 'NAME ONE THAT', 90); text_c(d, 1350, 'LASTED LONGER', 90)
        return im
    im = zoomed(paint(empire_at(yr)), z, lon, lat); d = ImageDraw.Draw(im)
    for (ey, (plon, plat)) in PLACES.items():
        if ey <= yr < ey + 60:
            ph = ((t * 2.0) % 1.0)
            cx, cy = zoom_xy(plon, plat, z, lon, lat)
            for rr, al in ((34 + 56 * ph, 255), (18, 255)):
                d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(255, 196, 0), width=8 if rr == 18 else 7)
    if t < 1.2:
        text_c(d, 150, CFG['q1'], 76); text_c(d, 250, CFG['q2'], 88, fill=(255, 196, 0))
        text_c(d, 380, str(int(yr)), 120, fill=(255, 255, 255))
    else:
        text_c(d, 170, str(int(yr)), 210, fill=(255, 196, 0))                      # the date: largest type
        text_c(d, 400, f'{int(yr) - START:,} YEARS', 76)
    for show, ey, label in EVENTS:
        if show <= yr < show + CFG.get('label_years', 60) or (show == END and yr >= END):                                              # each label ~1.2 s
            ly = 1260
            if ey in PLACES:
                ry = zoom_xy(*PLACES[ey], z, lon, lat)[1]
                if 1150 < ry < 1560: ly = int(ry) - 330 if ry > 1300 else int(ry) + 110   # never on its own ring
                ly = max(560, min(ly, 1420))
            text_c(d, ly, label.split(' · ')[0], 84, fill=(255, 196, 0)); text_c(d, ly + 100, label.split(' · ')[1], 78 if len(label) < 24 else 70)
    if yr < START + CFG.get('intro_years', 40): text_c(d, 1300, CFG['intro'], 64)
    return im

for i in range(int(DUR * FPS)):
    frame(i / FPS).save(f'{OUT}/f{i:04d}.png', compress_level=1)
print('frames', int(DUR * FPS))
