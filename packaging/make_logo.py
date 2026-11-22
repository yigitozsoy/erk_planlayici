"""erk logosu: Göktürk "e" harfi (dikey gövde; üstten sola inen, alttan sağa çıkan iki kısa eğik kol).

Üretir: erk/assets/logo.png (beyaz harf, saydam; arayüzde tema rengine boyanır) ve logo.ico
(açık gri yuvarlak kare üstünde koyu harf, 16-256 px). Logo değişirse bir kez çalıştırılır:
    python packaging/make_logo.py
Kurulum sihirbazı görselleri (make_meta.py) ve telefon sayfasının simgeleri (erk-site-yukle/erk/) logo.png'den
üretilir: --site ile o simgeler de yeniden yazılır.
"""
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "erk", "assets")
SITE = os.path.join(ROOT, "erk-site-yukle", "erk")

# Harf, yükseklik = 1 birim; tüm çizgiler aynı kalınlıkta (T), kollar 45°.
T = 0.135                       # çizgi kalınlığı
ARM = 0.19                      # kolun yatay uzunluğu (gövdenin dışında)
SL = T * 2 ** 0.5               # 45° kolun dikey kalınlığı (dik kalınlık = T)
STEM_X = ARM                    # gövdenin sol kenarı
W = ARM + T + ARM               # harf genişliği


def glyph_polys():
    x0, x1 = STEM_X, STEM_X + T
    stem = [(x0, 0.0), (x1, 0.0), (x1, 1.0), (x0, 1.0)]
    # üst kol: gövdenin sol üst köşesinden sola aşağı iner, ucu dikey kesik (tablodaki gibi "1"in bayrağı)
    top = [(x0, 0.0), (0.0, ARM), (0.0, ARM + SL), (x0, SL)]
    # alt kol: gövdenin dibinden sağa yukarı çıkar (üst kolun 180° döndürülmüşü)
    bottom = [(W - x, 1.0 - y) for x, y in top]
    return [stem, top, bottom]


def draw_glyph(img, box, color):
    """box = (x, y, yükseklik) — harfin sol üst köşesi ve yüksekliği (piksel)."""
    x, y, h = box
    d = ImageDraw.Draw(img)
    for poly in glyph_polys():
        d.polygon([(x + px * h, y + py * h) for px, py in poly], fill=color)


def make_png(path, ss=8):
    w, h = 286, 306                              # alpha'nın eski logosuyla aynı tuval (yerleşim değişmesin)
    big = Image.new("RGBA", (w * ss, h * ss), (255, 255, 255, 0))
    gh = (h - 60) * ss
    draw_glyph(big, ((w * ss - W * gh) / 2, 30 * ss, gh), (255, 255, 255, 255))
    big.resize((w, h), Image.LANCZOS).save(path)


def tile(size, ss=8):
    n = size * ss
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    grad = Image.new("RGBA", (n, n))
    gd = ImageDraw.Draw(grad)
    for yy in range(n):                          # üstten alta açık griden biraz koyuya
        v = int(236 - (236 - 191) * yy / max(1, n - 1))
        gd.line([(0, yy), (n, yy)], fill=(v, v, v, 255))
    mask = Image.new("L", (n, n), 0)
    r = int(n * 0.19)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, n - 1, n - 1], r, fill=255)
    img.paste(grad, (0, 0), mask)
    ImageDraw.Draw(img).rounded_rectangle([ss // 2, ss // 2, n - 1 - ss // 2, n - 1 - ss // 2], r,
                                          outline=(150, 150, 150, 255), width=max(1, ss // 2))
    gh = n * (0.64 if size > 24 else 0.78)
    draw_glyph(img, ((n - W * gh) / 2, (n - gh) / 2, gh), (24, 24, 24, 255))
    return img.resize((size, size), Image.LANCZOS)


def make_ico(path):
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    imgs = [tile(s) for s in sizes]
    imgs[-1].save(path, sizes=[(s, s) for s in sizes], append_images=imgs[:-1])


def site_icon(size, ss=4):
    """Telefon ana ekranı simgesi: siyah kare üstünde beyaz harf (sayfa AMOLED siyah)."""
    n = size * ss
    img = Image.new("RGBA", (n, n), (0, 0, 0, 255))
    gh = n * 0.58
    draw_glyph(img, ((n - W * gh) / 2, (n - gh) / 2, gh), (255, 255, 255, 255))
    return img.resize((size, size), Image.LANCZOS).convert("RGB")


if __name__ == "__main__":
    make_png(os.path.join(ASSETS, "logo.png"))
    make_ico(os.path.join(ASSETS, "logo.ico"))
    if "--site" in sys.argv and os.path.isdir(SITE):
        make_png(os.path.join(SITE, "logo.png"))
        for s in (192, 512):
            site_icon(s).save(os.path.join(SITE, f"icon-{s}.png"))
    print("ok")
