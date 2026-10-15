# 귀찮음 박멸 노트 - 실사 배경(Pixabay 무료 영상) + 자막 세로 영상
# 사용법: python3 make_real_video.py spec.json out.mp4
# spec = {"scenes": [
#   {"type": "text", "bg": "clip1.mp4", "lines": ["윗줄", "강조줄"], "accent": 1, "sec": 2.5},
#   {"type": "list", "bg": "clip2.mp4", "title": "제목", "items": ["...", "..."], "sec": 6},
#   {"type": "poll", "bg": "clip3.mp4", "title": ["질문1", "질문2"], "options": ["..",".."], "cta": "댓글로 숫자만 남겨줘", "sec": 4.5}
# ]}
# bg 영상은 Pixabay API(https://pixabay.com/api/videos/)로 받은 것만 사용 (Pixabay Content License: 상업 이용 가능, 출처 표기 불필요)
import json, os, subprocess, sys, tempfile, shutil, glob
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
YEL, NAVY, WHITE, RED = "#FFE45C", "#1E2A44", "#FFFFFF", "#FF4D4D"
F = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
B = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
def font(p, s): return ImageFont.truetype(p, s, index=1)

def ease(t):
    t = max(0, min(1, t)); c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2

def fit(d, s, p, size, maxw):
    while size > 30:
        f = font(p, size)
        if d.textlength(s, font=f) <= maxw: return f
        size -= 4
    return font(p, size)

def shadow_text(im, xy, s, f, fill, anchor="mm"):
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((xy[0] + 4, xy[1] + 6), s, font=f, fill=(0, 0, 0, 200), anchor=anchor)
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(im).text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=3, stroke_fill=(0, 0, 0, 160))

def bg_frames(src, sec, tmp, tag):
    out = f"{tmp}/{tag}"
    os.makedirs(out)
    vf = f"scale=-2:{H},crop={W}:{H},eq=brightness=-0.08:saturation=1.05,fps={FPS}"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-stream_loop", "-1", "-i", src, "-t", str(sec),
                    "-vf", vf, f"{out}/%05d.jpg"], check=True)
    return sorted(glob.glob(f"{out}/*.jpg"))

def overlay_base(bg):
    im = Image.open(bg).convert("RGBA")
    shade = Image.new("RGBA", (W, H), (10, 16, 30, 95))
    im.alpha_composite(shade)
    g = Image.new("RGBA", (W, 420), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    for y in range(420): gd.line((0, y, W, y), fill=(0, 0, 0, int(170 * y / 420)))
    im.alpha_composite(g, (0, H - 420))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((W / 2 - 230, H - 205, W / 2 + 230, H - 135), 35, fill=YEL)
    d.text((W / 2, H - 170), "귀찮음 박멸 노트", font=font(B, 42), fill=NAVY, anchor="mm")
    d.text((W / 2, H - 95), "@gwichanm_note", font=font(B, 34), fill=(255, 255, 255, 210), anchor="mm")
    return im

def s_text(sc, t, im):
    d = ImageDraw.Draw(im); lines = sc["lines"]; acc = sc.get("accent", len(lines) - 1)
    y0 = H * 0.40 - (len(lines) - 1) * 80
    for i, s in enumerate(lines):
        k = ease(t * 3 - i * 0.35)
        if k <= 0.02: continue
        size = int((112 if i == acc else 88) * k)
        shadow_text(im, (W / 2, y0 + i * 165), s, fit(d, s, F, max(10, size), W - 140), YEL if i == acc else WHITE)

def s_list(sc, t, im):
    d = ImageDraw.Draw(im); items = sc["items"]; n = len(items)
    shadow_text(im, (W / 2, 420), sc["title"], fit(d, sc["title"], F, int(96 * max(.02, ease(t * 3))), W - 160), YEL)
    gap = min(175, 860 / max(1, n))
    for i, s in enumerate(items):
        k = ease(t * (n + 2) - i - 0.5)
        if k <= 0.02: continue
        y = 640 + i * gap; x = 90 + (1 - min(1, k)) * 220
        panel = Image.new("RGBA", (W, H), (0, 0, 0, 0)); pd = ImageDraw.Draw(panel)
        pd.rounded_rectangle((x, y - 62, W - 90, y + 62), 62, fill=(255, 255, 255, int(235 * min(1, k))))
        im.alpha_composite(panel); d = ImageDraw.Draw(im)
        d.ellipse((x + 18, y - 44, x + 106, y + 44), fill=RED)
        d.text((x + 62, y), str(i + 1), font=font(F, 54), fill=WHITE, anchor="mm")
        d.text((x + 132, y), s, font=fit(d, s, B, 56, W - x - 270), fill=NAVY, anchor="lm")

def s_poll(sc, t, im):
    d = ImageDraw.Draw(im)
    for i, s in enumerate(sc["title"]):
        k = ease(t * 3 - i * 0.4)
        if k > 0.02:
            shadow_text(im, (W / 2, 470 + i * 150), s, fit(d, s, F, int(100 * k), W - 140), WHITE if i == 0 else YEL)
    a = max(0.0, min(1.0, t * 2 - 0.5)); opts = sc.get("options", [])
    y0 = 520 + len(sc["title"]) * 150 + 60
    for i, o in enumerate(opts):
        if a * len(opts) > i:
            y = y0 + i * 160
            d.rounded_rectangle((170, y - 60, W - 170, y + 60), 60, fill=WHITE)
            d.text((W / 2, y), o, font=fit(d, o, B, 54, W - 420), fill=NAVY, anchor="mm")
    if a > 0.95 and sc.get("cta"):
        y = y0 + len(opts) * 160 + 30
        d.rounded_rectangle((W / 2 - 330, y - 50, W / 2 + 330, y + 50), 50, fill=RED)
        d.text((W / 2, y), sc["cta"], font=fit(d, sc["cta"], B, 48, 600), fill=WHITE, anchor="mm")

R = {"text": s_text, "list": s_list, "poll": s_poll}

def render(spec, out, base_dir="."):
    tmp = tempfile.mkdtemp(); fr = f"{tmp}/out"; os.makedirs(fr); n = 0
    for si, sc in enumerate(spec["scenes"]):
        bgs = bg_frames(os.path.join(base_dir, sc["bg"]), sc.get("sec", 3), tmp, f"bg{si}")
        for i, b in enumerate(bgs):
            im = overlay_base(b); R[sc["type"]](sc, i / len(bgs), im)
            im.convert("RGB").save(f"{fr}/{n:05d}.jpg", quality=92); n += 1
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{fr}/%05d.jpg",
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-c:a", "aac",
                    "-movflags", "+faststart", out], check=True)
    shutil.rmtree(tmp); return out

if __name__ == "__main__":
    sp = json.load(open(sys.argv[1], encoding="utf-8"))
    print(render(sp, sys.argv[2], os.path.dirname(os.path.abspath(sys.argv[1]))))
