"""Build the 'Songs of Innocence' Chrome theme from the reference watercolours.

Usage:  python tools/build.py              # builds both variants
        python tools/build.py --corner on  # only the variant with the bottom-left vignette
        python tools/build.py --corner off # only the variant without it
Output: theme/            -> with the bottom-left vignette (theme_ntp_attribution)
        theme-no-corner/  -> same theme, vignette switched off
Load either folder via chrome://extensions -> Load unpacked.
"""
import argparse, json, os, random, shutil
from PIL import Image, ImageFilter, ImageEnhance, ImageChops, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "source")
REF_LAND = os.path.join(SRC, "roses-crescent-village.png")   # roses, crescent sun, village
REF_ROAD = os.path.join(SRC, "lane-sheep-church.png")        # lane, sheep, church

ap = argparse.ArgumentParser()
ap.add_argument("--corner", choices=["both", "on", "off"], default="both",
                help="bottom-left new-tab vignette: build with it, without it, or both variants")
ARGS = ap.parse_args()

OUT = os.path.join(ROOT, "build-tmp")      # shared images, copied into each variant
IMG = os.path.join(OUT, "images")

PAPER = (243, 231, 203)   # parchment base, also the NTP fill colour
INK = (74, 58, 42)
TOOLBAR = (248, 239, 216)  # lighter parchment for toolbar / active tab

shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(IMG, exist_ok=True)
random.seed(1794)


def paper_texture(w, h, base_col=PAPER):
    """Cream watercolour paper: low-frequency mottling + fine grain."""
    base = Image.new("RGB", (w, h), base_col)
    mott = Image.effect_noise((max(1, w // 24), max(1, h // 24)), 40).resize((w, h), Image.BICUBIC)
    mott = mott.filter(ImageFilter.GaussianBlur(6))
    grain = Image.effect_noise((w, h), 18)
    tint_dark = Image.new("RGB", (w, h), (226, 208, 170))
    tint_lite = Image.new("RGB", (w, h), (251, 244, 226))
    out = Image.composite(tint_lite, base, mott.point(lambda v: max(0, v - 128) * 2))
    out = Image.composite(tint_dark, out, ImageChops.invert(mott).point(lambda v: max(0, v - 165)))
    grain_rgb = Image.merge("RGB", [grain] * 3)
    return ImageChops.blend(out, ImageChops.multiply(out, grain_rgb.point(lambda v: 200 + v // 5)), 0.35)


def make_tileable_x(im, overlap):
    """Cross-fade the right edge into the left so the strip tiles horizontally."""
    w, h = im.size
    core = im.crop((0, 0, w - overlap, h))
    tail = im.crop((w - overlap, 0, w, h))
    head = core.crop((0, 0, overlap, h))
    mask = Image.linear_gradient("L").rotate(-90).resize((overlap, h))  # 255 at left -> 0 at right
    blended = Image.composite(tail, head, mask)
    core.paste(blended, (0, 0))
    return core


land = Image.open(REF_LAND).convert("RGB")
land = land.crop((48, 48, land.width - 48, land.height - 48))  # drop rounded white corners
road = Image.open(REF_ROAD).convert("RGB")

# ---------- frame (title / tab strip): watercolour sky with clouds ----------
sky = land.crop((420, 380, 2220, 640))           # cloud band below the sun rays
sky = sky.resize((int(sky.width * 220 / sky.height), 220), Image.LANCZOS)
sky = ImageEnhance.Brightness(sky).enhance(1.04)
sky = make_tileable_x(sky, 260)
frame = Image.new("RGB", (sky.width * 2, sky.height))
frame.paste(sky, (0, 0)); frame.paste(sky, (sky.width, 0))
frame.save(os.path.join(IMG, "theme_frame.png"))
ImageEnhance.Color(ImageEnhance.Brightness(frame).enhance(1.06)).enhance(0.55) \
    .save(os.path.join(IMG, "theme_frame_inactive.png"))

# ---------- toolbar / active tab: parchment ----------
paper_texture(2400, 160, TOOLBAR).save(os.path.join(IMG, "theme_toolbar.png"))

# ---------- inactive tabs: thin wash of the sky over parchment ----------
tab_bg = Image.blend(paper_texture(2400, 160), frame.crop((0, 40, 2400, 200)).resize((2400, 160)), 0.45)
tab_bg.save(os.path.join(IMG, "theme_tab_background.png"))

# ---------- new tab page ----------
# Chrome draws the image at native CSS size, centred. Keep the illustration
# ~860 px tall so even a 125%-scaled laptop shows the crescent, and surround it
# with parchment so wide/tall windows never see a hard edge.
H = 860
art = land.resize((int(land.width * H / land.height), H), Image.LANCZOS)
W = art.width
canvas = paper_texture(3840, 1800)
cw, ch = canvas.size
fade = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(fade)
edge = 90
for i in range(edge):
    d.rectangle((i, i, W - 1 - i, H - 1 - i), outline=int(255 * (i / edge) ** 1.6))
d.rectangle((edge, edge, W - edge, H - edge), fill=255)
fade = fade.filter(ImageFilter.GaussianBlur(8))
canvas.paste(art, ((cw - W) // 2, (ch - H) // 2), fade)
canvas.save(os.path.join(IMG, "theme_ntp_background.png"))

# A small attribution vignette from the second painting (sheep & roses) for the NTP corner.
vig = road.crop((1150, 1050, 2100, 1632)).resize((380, 232), Image.LANCZOS)
vm = Image.new("L", vig.size, 0)
ImageDraw.Draw(vm).ellipse((10, 10, vig.width - 10, vig.height - 10), fill=255)
vm = vm.filter(ImageFilter.GaussianBlur(18))
attr = paper_texture(*vig.size); attr.paste(vig, (0, 0), vm)
attr.save(os.path.join(IMG, "theme_ntp_attribution.png"))

# ---------- extension icon: a rose from the border ----------
rose = land.crop((40, 600, 260, 820)).resize((128, 128), Image.LANCZOS)
im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
m = Image.new("L", (128, 128), 0); ImageDraw.Draw(m).ellipse((2, 2, 125, 125), fill=255)
im.paste(rose, (0, 0), m)
im.save(os.path.join(OUT, "icon128.png"))

# ---------- manifest ----------
manifest = {
    "manifest_version": 3,
    "name": "Songs of Innocence — 天真之歌",
    "version": "1.0.0",
    "description": "水彩羊皮纸、新月光芒与玫瑰田园：仿《天真与经验之歌》插画风的 Chrome 主题。",
    "icons": {"128": "icon128.png"},
    "theme": {
        "images": {
            "theme_frame": "images/theme_frame.png",
            "theme_frame_inactive": "images/theme_frame_inactive.png",
            "theme_toolbar": "images/theme_toolbar.png",
            "theme_tab_background": "images/theme_tab_background.png",
            "theme_ntp_background": "images/theme_ntp_background.png",
            "theme_ntp_attribution": "images/theme_ntp_attribution.png",
        },
        "colors": {
            "frame": [178, 202, 220],
            "frame_inactive": [206, 216, 222],
            "toolbar": list(TOOLBAR),
            "tab_text": list(INK),
            "tab_background_text": [52, 70, 86],
            "tab_background_text_inactive": [96, 108, 118],
            "bookmark_text": [90, 70, 50],
            "toolbar_text": list(INK),
            "toolbar_button_icon": [122, 88, 62],
            "omnibox_background": [251, 245, 230],
            "omnibox_text": [59, 46, 34],
            "ntp_background": list(PAPER),
            "ntp_text": list(INK),
            "ntp_link": [150, 74, 58],
            "ntp_header": [196, 128, 104],
            "button_background": [0, 0, 0, 0.0],
        },
        "tints": {
            "buttons": [0.08, 0.35, 0.40],
        },
        "properties": {
            "ntp_background_alignment": "center",
            "ntp_background_repeat": "no-repeat",
            "ntp_logo_alternate": 1,
        },
    },
}


def write_variant(name, corner):
    dst = os.path.join(ROOT, name)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(OUT, dst)
    m = json.loads(json.dumps(manifest))
    if not corner:
        os.remove(os.path.join(dst, "images", "theme_ntp_attribution.png"))
        del m["theme"]["images"]["theme_ntp_attribution"]
        m["name"] += "（无角图）"
    with open(os.path.join(dst, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
    print(f"ok -> {name}/  (corner vignette {'on' if corner else 'off'}):",
          ", ".join(sorted(os.listdir(os.path.join(dst, "images")))))


if ARGS.corner in ("both", "on"):
    write_variant("theme", True)
if ARGS.corner in ("both", "off"):
    write_variant("theme-no-corner", False)
shutil.rmtree(OUT, ignore_errors=True)
