"""Kütüphane > Harita için alphaapp/assets/geo.json.gz üretir (Natural Earth, kamu malı).

Kullanım: python packaging/make_geo.py <natural-earth geojson klasörü>
Gerekenler (github.com/nvkelso/natural-earth-vector/geojson):
  ne_110m_admin_0_countries.geojson, ne_10m_admin_1_states_provinces.geojson, ne_10m_populated_places_simple.geojson
Çıktı: {"world": [{iso, name, rings}], "tr": [{plate, name, rings, c}], "cities": [[ad, iso3, ülke, lon, lat, nüfus]]}
Halkalar Douglas-Peucker ile sadeleşir (dünya 0.08°, Türkiye illeri 0.01°).
"""
import gzip
import json
import os
import sys
import unicodedata

PROVINCES = ("Adana Adıyaman Afyonkarahisar Ağrı Amasya Ankara Antalya Artvin Aydın Balıkesir Bilecik Bingöl Bitlis "
             "Bolu Burdur Bursa Çanakkale Çankırı Çorum Denizli Diyarbakır Edirne Elazığ Erzincan Erzurum Eskişehir "
             "Gaziantep Giresun Gümüşhane Hakkari Hatay Isparta Mersin İstanbul İzmir Kars Kastamonu Kayseri Kırklareli "
             "Kırşehir Kocaeli Konya Kütahya Malatya Manisa Kahramanmaraş Mardin Muğla Muş Nevşehir Niğde Ordu Rize "
             "Sakarya Samsun Siirt Sinop Sivas Tekirdağ Tokat Trabzon Tunceli Şanlıurfa Uşak Van Yozgat Zonguldak "
             "Aksaray Bayburt Karaman Kırıkkale Batman Şırnak Bartın Ardahan Iğdır Yalova Karabük Kilis Osmaniye "
             "Düzce").split()
ALIAS = {"zinguldak": "zonguldak", "kinkkale": "kirikkale", "k. maras": "kahramanmaras", "icel": "mersin"}
TR_COUNTRY = {"TUR": "Türkiye", "DEU": "Almanya", "GBR": "Birleşik Krallık", "FRA": "Fransa", "ITA": "İtalya",
              "ESP": "İspanya", "NLD": "Hollanda", "BEL": "Belçika", "CHE": "İsviçre", "AUT": "Avusturya",
              "GRC": "Yunanistan", "BGR": "Bulgaristan", "GEO": "Gürcistan", "RUS": "Rusya", "USA": "ABD",
              "JPN": "Japonya", "CHN": "Çin", "KOR": "Güney Kore", "CZE": "Çekya", "HUN": "Macaristan",
              "POL": "Polonya", "PRT": "Portekiz", "SWE": "İsveç", "NOR": "Norveç", "DNK": "Danimarka",
              "FIN": "Finlandiya", "ISL": "İzlanda", "IRL": "İrlanda", "EGY": "Mısır", "MAR": "Fas",
              "ARE": "BAE", "SAU": "Suudi Arabistan", "QAT": "Katar", "AZE": "Azerbaycan", "CYP": "Kıbrıs",
              "UKR": "Ukrayna", "ROU": "Romanya", "SRB": "Sırbistan", "HRV": "Hırvatistan", "BIH": "Bosna-Hersek",
              "MNE": "Karadağ", "ALB": "Arnavutluk", "MKD": "Kuzey Makedonya", "CAN": "Kanada", "MEX": "Meksika",
              "BRA": "Brezilya", "ARG": "Arjantin", "AUS": "Avustralya", "NZL": "Yeni Zelanda", "IND": "Hindistan",
              "THA": "Tayland", "IDN": "Endonezya", "SGP": "Singapur", "IRN": "İran", "IRQ": "Irak", "SYR": "Suriye"}


def fold(s):
    s = (s or "").lower().replace("ı", "i")
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).strip()


def simplify(pts, tol):
    """Douglas-Peucker (yinelemesiz)."""
    if len(pts) < 4:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        n2 = dx * dx + dy * dy or 1e-12
        best, idx = -1.0, None
        for i in range(a + 1, b):
            px, py = pts[i]
            k = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / n2))
            d = (px - ax - k * dx) ** 2 + (py - ay - k * dy) ** 2
            if d > best:
                best, idx = d, i
        if idx is not None and best > tol * tol:
            keep[idx] = True
            stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(pts, keep) if k]


def rings_of(geom, tol, nd, min_pts=4):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    out = []
    for poly in polys:
        ring = simplify([tuple(p[:2]) for p in poly[0]], tol)       # yalnızca dış halka
        if len(ring) >= min_pts:
            out.append([[round(x, nd), round(y, nd)] for x, y in ring])
    return out


def main(src):
    load = lambda n: json.load(open(os.path.join(src, n), encoding="utf-8"))  # noqa: E731
    world = []
    for f in load("ne_110m_admin_0_countries.geojson")["features"]:
        p = f["properties"]
        iso = p.get("ADM0_A3") or p.get("ISO_A3")
        name = TR_COUNTRY.get(iso) or p.get("NAME_TR") or p.get("NAME")
        world.append({"iso": iso, "name": name, "rings": rings_of(f["geometry"], 0.08, 2)})
    by_fold = {fold(n): (i + 1, n) for i, n in enumerate(PROVINCES)}
    tr = []
    for f in load("ne_10m_admin_1_states_provinces.geojson")["features"]:
        p = f["properties"]
        if p.get("adm0_a3") != "TUR":
            continue
        k = fold(p.get("name"))
        k = ALIAS.get(k, k)
        if k not in by_fold:
            raise SystemExit("il eşleşmedi: %r" % p.get("name"))
        plate, name = by_fold[k]
        rings = rings_of(f["geometry"], 0.01, 3)
        big = max(rings, key=len)
        cx, cy = (float(p["longitude"]), float(p["latitude"])) if p.get("longitude") else \
            (sum(x for x, _ in big) / len(big), sum(y for _, y in big) / len(big))
        tr.append({"plate": plate, "name": name, "rings": rings, "c": [round(cx, 3), round(cy, 3)]})
    assert len(tr) == 81, len(tr)
    cities = []
    names = {w["iso"]: w["name"] for w in world}
    for f in load("ne_10m_populated_places_simple.geojson")["features"]:
        p = f["properties"]
        iso, pop = p.get("adm0_a3"), int(p.get("pop_max") or 0)
        if iso == "TUR" or pop >= 250000 or p.get("adm0cap"):
            nm = p["name"]
            if iso == "TUR":                     # "Icel", "Corum" → il adının doğru yazımı
                k = ALIAS.get(fold(nm), fold(nm))
                nm = by_fold[k][1] if k in by_fold else nm
            cities.append([nm, iso, names.get(iso) or p.get("adm0name"), round(float(p["longitude"]), 3),
                           round(float(p["latitude"]), 3), pop])
    cities.sort(key=lambda c: -c[5])
    out = os.path.join(os.path.dirname(__file__), "..", "alphaapp", "assets", "geo.json.gz")
    data = json.dumps({"world": world, "tr": tr, "cities": cities}, ensure_ascii=False, separators=(",", ":"))
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        fh.write(data)
    print("ok", len(world), "ülke,", len(tr), "il,", len(cities), "şehir,", os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
