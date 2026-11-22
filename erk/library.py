"""İçerik kütüphanesi: kitap, film, dizi, belgesel, oyun, podcast, makale. Bilgi çekme (arka planda) + yardımcılar.

Kaynaklar (kullanıcının seçtiği; Goodreads / Letterboxd'un açık API'si yok, sayfaları kazınmaz, yalnızca bağlantı):
  kitap     Open Library (search.json + covers) → bulunamazsa Google Books. Anahtar gerekmez.
  film/dizi/belgesel  TMDB (prefs tmdb_key; ücretsiz). Türkçe başlık/tür (language=tr-TR), afiş, yönetmen,
            süre, sezon / bölüm sayısı. Belgesel = TMDB tür 99.
  oyun      Steam mağaza araması (storesearch + appdetails, anahtarsız); kapak dikey library_600x900.
            Steam'de olmayan (konsol) oyunlar elle eklenir. İlerleme = oynanan saat.
  podcast   Apple Podcasts araması (itunes.apple.com/search). Anahtar gerekmez.
  makale    bağlantının sayfası: og:title / og:image / og:site_name, kelime sayısından okuma süresi.
Arama isteğine yalnızca yazılan başlık gider; kişisel veri gitmez. Kapaklar DATA_DIR\\images'a indirilir.

media koleksiyonu: type, title, creator, year, cover (images içindeki dosya), genres[], status (want | doing |
done | dropped), rating (0-5, yarım), progress, total, started, finished, link, links{goodreads, letterboxd, tmdb},
source ("tmdb:movie:123" ...), note, seasons. Telefon sayfasına (web.py) GİTMEZ.
"""
import html
import json
import os
import re
import threading
import urllib.parse
import urllib.request
import uuid
from datetime import date

from PyQt6.QtCore import QObject, pyqtSignal

from .config import prefs, IMAGES_DIR

TYPES = ("book", "film", "series", "doc", "game", "podcast", "article")
STATUSES = ("doing", "want", "done", "dropped")
TYPE_ICON = {"book": "menu_book", "film": "movie", "series": "tv", "doc": "movie", "podcast": "podcast",
             "article": "notes", "game": "sports_esports"}
# "+" düğmesinin adımı ve birim
STEP = {"book": 10, "series": 1, "podcast": 1, "doc": 1, "film": 1, "article": 1, "game": 1}
UA = "erk/3 (personal library)"
TIMEOUT = 12


def _get(url, headers=None, raw=False):
    req = urllib.request.Request(url, headers=dict({"User-Agent": UA, "Accept-Language": "tr,en;q=0.8"},
                                                   **(headers or {})))
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = r.read(4_000_000)
        if raw:
            return data, r.headers.get_content_type()
        return json.loads(data.decode("utf-8", "replace"))


def q(s):
    return urllib.parse.quote(s or "")


# ============================================================ arama sonuçları: dict(title, creator, year, cover_url,
#                                                              genres, total, link, links, source, extra)
def search_books(text):
    out = []
    try:
        d = _get(f"https://openlibrary.org/search.json?q={q(text)}&limit=8"
                 "&fields=key,title,author_name,first_publish_year,number_of_pages_median,subject,cover_i,isbn")
        for x in d.get("docs", []):
            isbn = (x.get("isbn") or [None])[0]
            out.append({"title": x.get("title") or "", "creator": ", ".join((x.get("author_name") or [])[:2]),
                        "year": x.get("first_publish_year"), "total": x.get("number_of_pages_median"),
                        "genres": [s for s in (x.get("subject") or []) if len(s) < 24][:3],
                        "cover_url": f"https://covers.openlibrary.org/b/id/{x['cover_i']}-L.jpg"
                        if x.get("cover_i") else None,
                        "link": "https://openlibrary.org" + x.get("key", ""),
                        "links": {"goodreads": f"https://www.goodreads.com/search?q={q(isbn or x.get('title'))}"},
                        "source": "openlibrary:" + x.get("key", "")})
    except Exception:
        pass
    if len(out) < 3:
        try:
            d = _get(f"https://www.googleapis.com/books/v1/volumes?q={q(text)}&maxResults=8")
            for it in d.get("items", []):
                v = it.get("volumeInfo", {})
                img = (v.get("imageLinks") or {}).get("thumbnail")
                out.append({"title": v.get("title") or "", "creator": ", ".join((v.get("authors") or [])[:2]),
                            "year": (v.get("publishedDate") or "")[:4] or None, "total": v.get("pageCount"),
                            "genres": (v.get("categories") or [])[:3],
                            "cover_url": img.replace("http://", "https://") if img else None,
                            "link": v.get("infoLink"),
                            "links": {"goodreads": f"https://www.goodreads.com/search?q={q(v.get('title'))}"},
                            "source": "gbooks:" + it.get("id", "")})
        except Exception:
            pass
    return out


_genres = {}


def _tmdb(path, **params):
    key = (prefs.get("tmdb_key") or "").strip()
    params = dict({"api_key": key, "language": "tr-TR"}, **params)
    return _get(f"https://api.themoviedb.org/3/{path}?" + urllib.parse.urlencode(params))


def _tmdb_genres(kind):
    if kind not in _genres:
        try:
            _genres[kind] = {g["id"]: g["name"] for g in _tmdb(f"genre/{kind}/list").get("genres", [])}
        except Exception:
            _genres[kind] = {}
    return _genres[kind]


def search_tmdb(text, mtype):
    """mtype: film | series | doc. Anahtar yoksa NoKey."""
    if not (prefs.get("tmdb_key") or "").strip():
        raise NoKey()
    kinds = {"film": ("movie",), "series": ("tv",), "doc": ("movie", "tv")}[mtype]
    out = []
    for kind in kinds:
        g = _tmdb_genres(kind)
        for x in _tmdb(f"search/{kind}", query=text).get("results", [])[:8]:
            ids = x.get("genre_ids") or []
            title = x.get("title") or x.get("name") or ""
            day = x.get("release_date") or x.get("first_air_date") or ""
            out.append({"title": title, "creator": "", "year": day[:4] or None,
                        "genres": [g.get(i) for i in ids if g.get(i)][:3],
                        "cover_url": f"https://image.tmdb.org/t/p/w342{x['poster_path']}"
                        if x.get("poster_path") else None,
                        "link": f"https://www.themoviedb.org/{kind}/{x['id']}",
                        "links": {"letterboxd": f"https://letterboxd.com/tmdb/{x['id']}/"} if kind == "movie" else {},
                        "source": f"tmdb:{kind}:{x['id']}", "original": x.get("original_title") or
                        x.get("original_name"), "is_doc": 99 in ids})
    if mtype == "doc":
        out.sort(key=lambda r: not r.get("is_doc"))
    return out


def tmdb_details(source):
    """Seçilen sonucun ayrıntısı: yönetmen / yaratıcı, süre, sezon / bölüm sayısı."""
    _, kind, tid = source.split(":")
    d = _tmdb(f"{kind}/{tid}", append_to_response="credits")
    extra = {}
    if kind == "movie":
        crew = (d.get("credits") or {}).get("crew") or []
        extra["creator"] = ", ".join(c["name"] for c in crew if c.get("job") == "Director")[:80]
        extra["runtime"] = d.get("runtime")
        extra["total"] = 1
    else:
        extra["creator"] = ", ".join(c.get("name", "") for c in (d.get("created_by") or []))[:80]
        extra["total"] = d.get("number_of_episodes")
        extra["seasons"] = d.get("number_of_seasons")
    extra["genres"] = [g["name"] for g in d.get("genres", [])][:4]
    return extra


def search_podcasts(text):
    d = _get(f"https://itunes.apple.com/search?media=podcast&limit=8&term={q(text)}")
    return [{"title": x.get("collectionName") or "", "creator": x.get("artistName") or "",
             "year": (x.get("releaseDate") or "")[:4] or None, "genres": [g for g in (x.get("genres") or [])
                                                                          if g != "Podcasts"][:3],
             "cover_url": x.get("artworkUrl600") or x.get("artworkUrl100"), "total": x.get("trackCount"),
             "link": x.get("collectionViewUrl"), "links": {}, "source": f"itunes:{x.get('collectionId')}"}
            for x in d.get("results", [])]


_NOT_GAME = re.compile(r"soundtrack|\bost\b|artbook|art book|\bdlc\b|season pass|demo$|playtest|"
                       r"expansion pack|wallpaper|dedicated server|sdk\b", re.I)


def search_games(text):
    d = _get(f"https://store.steampowered.com/api/storesearch/?term={q(text)}&l=turkish&cc=TR")
    out = []
    for x in d.get("items") or []:
        if x.get("type") != "app" or _NOT_GAME.search(x.get("name") or ""):
            continue
        i = x["id"]
        out.append({"title": x.get("name") or "", "creator": "", "year": None, "genres": [],
                    "cover_url": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{i}/library_600x900.jpg",
                    "alt_cover": x.get("tiny_image"), "total": None,
                    "link": f"https://store.steampowered.com/app/{i}/", "links": {}, "source": f"steam:{i}"})
    return out[:8]


_GENRE = {"RYO": "Rol yapma"}


def steam_details(source):
    i = source.split(":", 1)[1]
    d = (_get(f"https://store.steampowered.com/api/appdetails?appids={i}&l=turkish").get(i) or {}).get("data") or {}
    y = re.search(r"\d{4}", (d.get("release_date") or {}).get("date") or "")
    return {"title": d.get("name"), "creator": ", ".join(d.get("developers") or [])[:80],
            "year": y.group(0) if y else None,
            "genres": [_GENRE.get(g["description"], g["description"]) for g in d.get("genres") or []
                       if g.get("description")][:4],
            "alt_cover": d.get("header_image")}


def fetch_article(url):
    data, ctype = _get(url, raw=True)
    s = data.decode("utf-8", "replace")

    def meta(prop):
        m = re.search(r'<meta[^>]+(?:property|name)=["\']%s["\'][^>]*content=["\']([^"\']+)' % re.escape(prop), s, re.I) \
            or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']%s["\'];?' %
                         re.escape(prop), s, re.I)
        return html.unescape(m.group(1)).strip() if m else None
    title = meta("og:title") or (html.unescape(re.search(r"<title[^>]*>(.*?)</title>", s, re.I | re.S).group(1)).strip()
                                 if re.search(r"<title[^>]*>(.*?)</title>", s, re.I | re.S) else url)
    body = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", s, flags=re.S | re.I)
    words = len(re.findall(r"\w+", body))
    img = meta("og:image")
    if img and img.startswith("//"):
        img = "https:" + img
    return [{"title": title, "creator": meta("og:site_name") or meta("author") or urllib.parse.urlparse(url).netloc,
             "year": (meta("article:published_time") or "")[:4] or None, "genres": [],
             "cover_url": img if img and img.startswith("http") else None,
             "total": max(1, round(words / 230)) if words > 200 else None,   # dakika
             "link": url, "links": {}, "source": "url:" + url}]


class NoKey(Exception):
    pass


def search(mtype, text):
    text = (text or "").strip()
    if not text:
        return []
    if mtype == "book":
        return search_books(text)
    if mtype in ("film", "series", "doc"):
        return search_tmdb(text, mtype)
    if mtype == "podcast":
        return search_podcasts(text)
    if mtype == "game":
        return search_games(text)
    if mtype == "article":
        url = text if re.match(r"^https?://", text) else "https://" + text
        return fetch_article(url)
    return []


def download_cover(url):
    """Kapağı IMAGES_DIR'e indirir, dosya adını döndürür (hata → None)."""
    if not url:
        return None
    try:
        data, ctype = _get(url, raw=True)
        if len(data) < 500 or not ctype.startswith("image/"):
            return None
        ext = {"image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(ctype, ".jpg")
        os.makedirs(IMAGES_DIR, exist_ok=True)
        name = "media_" + uuid.uuid4().hex[:12] + ext
        with open(os.path.join(IMAGES_DIR, name), "wb") as f:
            f.write(data)
        return name
    except Exception:
        return None


class Job(QObject):
    """fn'i arka planda çalıştırır; sonuç ana iş parçacığında done(sonuç) ya da failed(hata adı) ile gelir.
    Sonucu bekleyen pencere kapandıysa sinyal boşa gider (ebeveyn silinince Job da silinir)."""
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn, *args, parent=None):
        super().__init__(parent)
        self._fn, self._args = fn, args

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()
        return self

    def _run(self):
        try:
            res = self._fn(*self._args)
        except NoKey:
            self._emit(self.failed, "nokey")
            return
        except Exception as e:     # ağ / ayrıştırma hatası: kullanıcıya kısa mesaj
            self._emit(self.failed, type(e).__name__)
            return
        self._emit(self.done, res)

    def _emit(self, sig, val):
        try:
            sig.emit(val)
        except RuntimeError:       # nesne silinmiş
            pass


# ============================================================ sorgular
def year_count(store, mtype, year=None):
    year = year or date.today().year
    return sum(1 for m in store.all("media") if m.get("type") == mtype and m.get("status") == "done"
               and str(m.get("finished") or "")[:4] == str(year))


def current(store):
    """Şu an okunan / izlenen / dinlenenler (son güncellenen önce)."""
    items = [m for m in store.all("media") if m.get("status") == "doing"]
    return sorted(items, key=lambda m: m.get("updated") or m.get("created") or "", reverse=True)


def progress_text(m, t):
    p, tot = m.get("progress"), m.get("total")
    unit = {"book": "u_page", "series": "u_ep", "podcast": "u_ep", "article": "u_min", "doc": "u_ep",
            "game": "u_hour"}.get(
        m.get("type"))
    if unit is None or not (p or tot):
        return ""
    p = int(p or 0)
    return t(unit, n=f"{p}/{int(tot)}" if tot else str(p))


def bump(store, m, sign=1):
    """İlerlemeyi bir adım artırır (kitap 10 sayfa, dizi 1 bölüm); sona gelince bitti sayılır."""
    from datetime import datetime
    step = STEP.get(m.get("type"), 1) * sign
    tot = m.get("total")
    p = max(0, int(m.get("progress") or 0) + step)
    if tot:
        p = min(p, int(tot))
    fields = {"progress": p, "updated": datetime.now().isoformat(timespec="seconds")}
    if tot and p >= int(tot):
        fields.update(status="done", finished=date.today().isoformat())
    store.update("media", m["id"], **fields)
    return fields.get("status") == "done"
