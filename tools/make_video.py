# 귀찮음 박멸 노트 - 세로 모션그래픽 영상 만들기
# 사용법: python3 make_video.py spec.json out.mp4
# spec = {"scenes": [
#   {"type": "text", "lines": ["윗줄", "강조줄"], "accent": 1, "sec": 2.5},
#   {"type": "list", "title": "자기 전 루틴", "items": ["...", "..."], "sec": 5},
#   {"type": "poll", "title": ["질문 1줄", "질문 2줄"], "options": ["① ..", "② .."], "cta": "댓글로 번호만 남겨줘", "sec": 4}
# ]}
import json, math, os, subprocess, sys, tempfile, shutil
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
BG, PANEL, NAVY, RED, WHITE, GRAY = "#FFE45C", "#FFF6C2", "#1E2A44", "#FF4D4D", "#FFFFFF", "#8A93A6"
def _f(names):
    for n in names:
        if os.path.exists(n):
            return n
    raise SystemExit("한글 폰트 없음: apt-get install -y fonts-noto-cjk")
F = _f(["/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"])
B = _f(["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"])
def font(path, size): return ImageFont.truetype(path, size, index=1)
small, tiny = font(B, 52), font(B, 40)

def ease(t):
    t = max(0, min(1, t)); c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2

def fit(d, s, path, size, maxw):
    while size > 30:
        f = font(path, size)
        if d.textlength(s, font=f) <= maxw:
            return f
        size -= 4
    return font(path, size)

def center(d, y, s, path, size, fill, scale=1.0, maxw=W - 200):
    if scale <= 0.02: return
    f = fit(d, s, path, max(10, int(size * scale)), maxw)
    d.text((W / 2, y), s, font=f, fill=fill, anchor="mm")

def base():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((60, 260, W - 60, H - 300), 60, fill=PANEL)
    d.text((W / 2, H - 170), "귀찮음 박멸 노트", font=small, fill=NAVY, anchor="mm")
    d.text((W / 2, H - 110), "@gwichanm_note", font=tiny, fill=GRAY, anchor="mm")
    return im, d

def s_text(sc, t):
    im, d = base()
    lines = sc["lines"]; acc = sc.get("accent", len(lines) - 1)
    y0 = H / 2 - (len(lines) - 1) * 75 - 100
    for i, s in enumerate(lines):
        center(d, y0 + i * 150, s, F, 100 if i == acc else 84, RED if i == acc else NAVY, ease(t * 3 - i * 0.35))
    return im

def s_list(sc, t):
    im, d = base()
    center(d, 430, sc["title"], F, 92, NAVY, ease(t * 3))
    items = sc["items"]; n = len(items)
    gap = min(190, 900 / max(1, n))
    for i, s in enumerate(items):
        k = ease(t * (n + 2) - i - 0.5)
        if k <= 0.02: continue
        y = 640 + i * gap
        x = 120 + (1 - min(1, k)) * 200
        d.ellipse((x, y - 45, x + 90, y + 45), fill=RED)
        d.text((x + 45, y), str(i + 1), font=font(F, 56), fill=WHITE, anchor="mm")
        f = fit(d, s, B, 58, W - x - 260)
        d.text((x + 120, y), s, font=f, fill=NAVY, anchor="lm")
    return im

def s_poll(sc, t):
    im, d = base()
    for i, s in enumerate(sc["title"]):
        center(d, 520 + i * 140, s, F, 96, NAVY, ease(t * 3 - i * 0.4))
    a = max(0.0, min(1.0, t * 2 - 0.5))
    opts = sc.get("options", [])
    y0 = 560 + len(sc["title"]) * 140 + 60
    for i, o in enumerate(opts):
        if a * len(opts) > i:
            y = y0 + i * 150
            d.rounded_rectangle((180, y - 55, W - 180, y + 55), 55, fill=WHITE, outline=NAVY, width=6)
            d.text((W / 2, y), o, font=fit(d, o, B, 52, W - 420), fill=NAVY, anchor="mm")
    if a > 0.95 and sc.get("cta"):
        d.text((W / 2, y0 + len(opts) * 150 + 40), sc["cta"], font=small, fill=RED, anchor="mm")
    return im

R = {"text": s_text, "list": s_list, "poll": s_poll}

def render(spec, out):
    tmp = tempfile.mkdtemp()
    n = 0
    for sc in spec["scenes"]:
        frames = int(sc.get("sec", 3) * FPS)
        for i in range(frames):
            R[sc["type"]](sc, i / frames).save(f"{tmp}/f{n:05d}.png")
            n += 1
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{tmp}/f%05d.png",
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "24", "-c:a", "aac",
                    "-movflags", "+faststart", out], check=True)
    shutil.rmtree(tmp)
    return out

if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    print(render(spec, sys.argv[2]))
