"""3B vücut kare paketi: muscle-body/ modelinden alphaapp/assets/body_frames.zip üretir (yerelde, bir kez).

    python packaging/make_body.py [model.OBJ ya da .zip]

Model (ZBrush OBJ, ~260 bin dörtgen, kaslara bölünmemiş) depoda yok; lisansı belli olmadığından paket de
.gitignore'da. Paket yoksa uygulama body3d.Body3D'yi (elipsoidlerden basit model) kullanır.

Adımlar (numpy + Pillow gerekir, uygulamanın kendisi gerektirmez):
  1. OBJ oku, köşe normalleri.
  2. Kaslara ayır: SEEDS'teki yüzey noktalarına (x, y, yön) en yakınlık; sonra komşu çoğunluğuyla yumuşat.
  3. 72 açı (5°) için nokta serpme + z-tampon ile çiz; piksel = 1 + kas × 13 + gölge (Bayer titreme).
     Uygulamada renk tablosu değiştirilerek boyanır (body3d.ModelView).
Birimler model gibi santimetre: y yukarı (ayak 0, baş ~182), z ileri (yüz +z), x yanlar (sağ kol +x).
"""
import io
import json
import math
import os
import sys
import time
import zipfile

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# model (lisansı belirsiz, depoya girmez): önce assets/muscle-body/anatomy.OBJ, yoksa eski yer
SRC = next((p for p in (os.path.join(ROOT, "assets", "muscle-body", "anatomy.OBJ"),
                        os.path.join(ROOT, "muscle-body", "source", "zremesh anatomy muhammet.zip"))
            if os.path.exists(p)), os.path.join(ROOT, "assets", "muscle-body", "anatomy.OBJ"))
OUT = os.path.join(ROOT, "alphaapp", "assets", "body_frames.zip")

KEYS = ["skin", "chest", "front_delts", "side_delts", "rear_delts", "biceps", "triceps", "forearms", "abs",
        "obliques", "traps", "lats", "upper_back", "lower_back", "glutes", "quads", "hamstrings", "adductors", "calves"]
NS = 13                                  # gölge basamağı (19 × 13 + 1 ≤ 256)
N_FR, W, H, PITCH = 72, 520, 860, 5

# kas → [(x, y, yön)] sağ taraf; x ≠ 0 olanlar aynalanır. yön: front / back (en öndeki / arkadaki yüzey),
# out / in (o yükseklikte uzvun dış / iç yüzü).
SEEDS = {
    "traps": [(6, 155, "back"), (11, 152, "back"), (16, 149, "back"), (4, 145, "back"), (9, 154, "front"),
              (14, 151, "front"), (0, 138, "back"), (3, 130, "back"), (8, 143, "back"), (19, 148, "back")],
    "front_delts": [(25, 140, "front"), (23, 136, "front"), (27, 143, "front")],
    "side_delts": [(31, 138, "out"), (30, 133, "out"), (30, 143, "out")],
    "rear_delts": [(26, 141, "back"), (27, 135, "back")],
    "chest": [(6, 138, "front"), (12, 140, "front"), (5, 130, "front"), (12, 129, "front"), (18, 135, "front"),
              (17, 140, "front"), (20, 131, "front")],
    "biceps": [(28, 124, "front"), (30, 117, "front"), (31, 112, "front")],
    "triceps": [(28, 125, "back"), (31, 118, "back"), (35, 121, "out"), (33, 112, "back"), (30, 128, "back")],
    "forearms": [(33, 103, "front"), (34, 96, "front"), (34, 101, "back"), (37, 98, "out"), (31, 99, "in"),
                 (35, 92, "back"), (33, 90, "front")],
    "abs": [(3, 123, "front"), (3, 116, "front"), (3, 108, "front"), (3, 100, "front"), (7, 121, "front"),
            (7, 112, "front"), (7, 104, "front"), (9, 117, "front"), (9, 109, "front"), (8, 101, "front")],
    "obliques": [(14, 116, "front"), (16, 110, "out"), (13, 106, "front"), (16, 118, "out"), (15, 124, "front"),
                 (15, 102, "out")],
    "lats": [(13, 125, "back"), (18, 121, "out"), (13, 116, "back"), (18, 128, "back"), (10, 113, "back"),
             (16, 115, "back"), (10, 121, "back"), (14, 109, "back"), (17, 112, "out"), (17, 124, "out"),
             (8, 116, "back"), (5, 117, "back"), (8, 111, "back")],
    "upper_back": [(8, 136, "back"), (16, 136, "back"), (11, 131, "back"), (21, 134, "back")],
    "lower_back": [(3, 104, "back"), (4, 98, "back"), (6, 109, "back")],
    "glutes": [(8, 92, "back"), (14, 90, "back"), (7, 85, "back"), (18, 93, "out"), (13, 84, "back")],
    "quads": [(12, 76, "front"), (15, 68, "front"), (11, 61, "front"), (19, 62, "out"), (9, 55, "front"),
              (14, 53, "front"), (19, 72, "out")],
    "adductors": [(4, 76, "in"), (6, 68, "in"), (5, 80, "front"), (7, 62, "in")],
    "hamstrings": [(12, 74, "back"), (14, 63, "back"), (10, 58, "back"), (8, 68, "back"), (17, 57, "back")],
    "calves": [(16, 37, "back"), (19, 34, "back"), (12, 34, "in"), (22, 33, "out"), (16, 28, "back"),
               (15, 43, "back"), (19, 42, "back"), (13, 41, "in"), (22, 40, "out")],
    "skin": [(0, 172, "front"), (0, 172, "back"), (6, 168, "out"), (0, 162, "front"), (0, 155, "front"),
             (4, 158, "front"), (0, 160, "back"), (1, 85, "front"), (4, 90, "front"), (16, 47, "front"),
             (20, 46, "out"), (11, 46, "in"), (16, 32, "front"), (17, 22, "front"), (18, 14, "front"),
             (19, 13, "back"), (22, 18, "out"), (16, 18, "in"), (21, 3, "front"), (20, 3, "back"),
             (32, 84, "front"), (33, 84, "back"), (36, 85, "out"), (29, 85, "in"), (10, 94, "front"),
             (15, 95, "front"), (19, 92, "front"), (19, 96, "out")],
}


def load(path):
    if path.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            name = next(n for n in zf.namelist() if n.lower().endswith(".obj"))
            lines = io.TextIOWrapper(zf.open(name), encoding="utf-8", errors="replace")
            return _parse(lines)
    with open(path, encoding="utf-8", errors="replace") as fh:
        return _parse(fh)


def _parse(lines):
    V, F = [], []
    for line in lines:
        if line.startswith("v "):
            V.append(line.split()[1:4])
        elif line.startswith("f "):
            idx = [int(x.split("/")[0]) - 1 for x in line.split()[1:]]
            if len(idx) == 3:
                idx.append(idx[2])
            F.append(idx[:4])
    return np.array(V, dtype=np.float64), np.array(F, dtype=np.int64)


def surface_point(V, x, y, how):
    m = np.abs(V[:, 1] - y) < 1.2
    if how in ("front", "back"):
        for r in (1.2, 2.5, 4, 6):
            mm = m & (np.abs(V[:, 0] - x) < r)
            if mm.any():
                break
        else:
            raise ValueError((x, y, how))
        idx = np.nonzero(mm)[0]
        return V[idx[np.argmax(V[idx, 2]) if how == "front" else np.argmin(V[idx, 2])]]
    idx = np.nonzero(m & (np.abs(V[:, 0] - x) < 4))[0]
    if not len(idx):
        raise ValueError((x, y, how))
    zc = np.median(V[idx, 2])
    idx = idx[np.abs(V[idx, 2] - zc) < 3]
    return V[idx[np.argmax(V[idx, 0]) if how == "out" else np.argmin(V[idx, 0])]]


def segment(V, F):
    pts, lab = [], []
    for k, lst in SEEDS.items():
        for x, y, how in lst:
            for sx in ((1, -1) if x else (1,)):
                h = how if sx > 0 or how not in ("out", "in") else ("in" if how == "out" else "out")
                pts.append(surface_point(V, x * sx, y, h))
                lab.append(KEYS.index(k))
    pts, lab = np.array(pts), np.array(lab)
    C = V[F].mean(1)
    L = np.empty(len(C), np.int64)
    for a in range(0, len(C), 20000):
        d = ((C[a:a + 20000, None, :] - pts[None]) ** 2).sum(-1)
        L[a:a + 20000] = lab[d.argmin(1)]
    for _ in range(6):                    # sınırları yumuşat
        Hh = np.zeros((len(V), len(KEYS)), np.float32)
        for k in range(4):
            np.add.at(Hh, (F[:, k], L), 1.0)
        L = (Hh[F[:, 0]] + Hh[F[:, 1]] + Hh[F[:, 2]] + Hh[F[:, 3]]).argmax(1)
    return L


def samples(V, F, G=3):
    fn = np.cross(V[F[:, 2]] - V[F[:, 0]], V[F[:, 3]] - V[F[:, 1]])
    VN = np.zeros_like(V)
    for k in range(4):
        np.add.at(VN, F[:, k], fn)
    VN /= np.linalg.norm(VN, axis=1, keepdims=True) + 1e-12
    uu, vv = np.meshgrid((np.arange(G) + 0.5) / G, (np.arange(G) + 0.5) / G)
    uu, vv = uu.ravel(), vv.ravel()
    Wt = np.stack([(1 - uu) * (1 - vv), uu * (1 - vv), uu * vv, (1 - uu) * vv], 1)
    P = np.einsum("sk,fkd->fsd", Wt, V[F]).reshape(-1, 3)
    N = np.einsum("sk,fkd->fsd", Wt, VN[F]).reshape(-1, 3)
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
    return P, N, np.repeat(np.arange(len(F)), G * G)


BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 - 0.5


def frame(P, N, FACE, L, yaw):
    a, b = math.radians(yaw), math.radians(PITCH)
    ca, sa, cb, sb = math.cos(a), math.sin(a), math.cos(b), math.sin(b)
    x, y, z = P[:, 0], P[:, 1] - 91, P[:, 2]
    x1 = x * ca + z * sa
    z1 = -x * sa + z * ca
    y2 = y * cb - z1 * sb
    z2 = y * sb + z1 * cb
    nx, ny, nz = N[:, 0], N[:, 1], N[:, 2]
    nx1 = nx * ca + nz * sa
    nz1 = -nx * sa + nz * ca
    ny2 = ny * cb - nz1 * sb
    nz2 = ny * sb + nz1 * cb
    s = (H - 20) / 186.0
    px = np.round(W / 2 + x1 * s).astype(np.int64)
    py = np.round(H / 2 - y2 * s).astype(np.int64)
    ok = (px >= 0) & (px < W) & (py >= 0) & (py < H)
    pix, dep = (py * W + px)[ok], z2[ok]
    order = np.lexsort((-dep, pix))
    pix_s = pix[order]
    first = np.r_[True, pix_s[1:] != pix_s[:-1]]
    sel = np.nonzero(ok)[0][order[first]]
    pp = pix_s[first]
    Lk = np.array([-0.45, 0.55, 0.70])
    Lk /= np.linalg.norm(Lk)
    n = np.stack([nx1[sel], ny2[sel], nz2[sel]], 1)
    key = np.clip(n @ Lk, 0, 1)
    fill = np.clip(n[:, 2], 0, 1)
    hv = Lk + np.array([0, 0, 1.0])
    hv /= np.linalg.norm(hv)
    spec = np.clip(n @ hv, 0, 1) ** 24
    sh = np.clip(0.08 + 0.62 * key + 0.30 * fill + 0.25 * spec, 0, 1)
    yy, xx = np.divmod(pp, W)
    q = np.clip(np.floor(sh * (NS - 1) + 0.5 + BAYER[yy % 4, xx % 4]), 0, NS - 1).astype(np.int64)
    idx = np.zeros(W * H, np.uint8)
    idx[pp] = (1 + L[FACE[sel]] * NS + q).astype(np.uint8)
    img = idx.reshape(H, W)
    for need in (6, 5):                   # modeldeki küçük delikleri komşu renkle kapat
        nb = np.stack([np.roll(np.roll(img, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx])
        fix = (img == 0) & ((nb > 0).sum(0) >= need)
        if fix.any():
            img[fix] = nb.max(0)[fix]
    return img


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else SRC
    t0 = time.time()
    V, F = load(src)
    print("model", V.shape, F.shape, round(time.time() - t0, 1), "s")
    L = segment(V, F)
    print("muscles", dict(zip(KEYS, np.bincount(L, minlength=len(KEYS)).tolist())))
    P, N, FACE = samples(V, F)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    total = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("meta.json", json.dumps({"keys": KEYS, "shades": NS, "frames": N_FR, "w": W, "h": H,
                                             "step": 360 / N_FR, "source": os.path.basename(src)}))
        for i in range(N_FR):
            im = Image.fromarray(frame(P, N, FACE, L, i * 360.0 / N_FR), "P")
            im.putpalette([0, 0, 0] + [v for k in range(255) for v in (k, k, k)])
            b = io.BytesIO()
            im.save(b, "PNG", optimize=True, transparency=0)
            zf.writestr("f%02d.png" % i, b.getvalue())
            total += len(b.getvalue())
    print("written", OUT, total // 1024, "KB", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
