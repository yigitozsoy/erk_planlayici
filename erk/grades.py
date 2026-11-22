"""Not ortalaması: dönem ortalaması (ANO) ve genel ortalama (AGNO). Kullanıcının Excel hesaplayıcısının
(lectures_for_erk.xlsx: "lectures", "5.1", "5.2" sayfaları) birebir karşılığı:

* Harf → 4'lük not: AA 4 · BA 3.5 · BB 3 · CB 2.5 · CC 2 · DC 1.5 · DD 1 · FD 0.5 · FF 0 · D 0 · NA 0.
  Sayı yazılmışsa olduğu gibi. "XX" ya da boş = not yok → AKTS'ye de girmez.
* Dönem: AKTS = notu olan derslerin AKTS'si, ortalama = Σ(AKTS × not) / AKTS.
* AGNO (transkript): Σ dönem(AKTS × ortalama) / Σ AKTS = Σ(AKTS × not) / Σ AKTS (notu olan dersler).
* Bu dönem (Excel 5.1 T8): (transkript puanı − tekrar alınan derslerin eski puanı + Σ yeni AKTS × not)
                            / (transkript AKTS − eski AKTS + Σ notu olan yeni AKTS).
  Eski ders yalnızca hem eski hem yeni not sayıysa düşülür (Excel AJ sütunu). Eşleşme: Excel "*ad*" araması
  yapıyordu (Fizik I ↔ Fizik II karışabilirdi); burada önce tam ad, sonra ders kodu, sonra adı içeren en kısa
  transkript satırı. Ders formunda "Tekrar" ile elle seçilebilir / kapatılabilir.
* Üç senaryo (Excel'deki üç blok): "letter" gerçek harf, "guess" ihtimal, "target" hedef. Gerçek harf girilmişse
  ihtimal ve hedefte de o kullanılır (kesinleşen not tahmin edilmez).
* Excel 5.2: 5.1'in sonuçları transkripte işlenip sonraki dönem ondan hesaplanıyordu. Burada "Dönemi bitir" bu
  dönemin harflerini transkripte yazar (tekrar alınan dersin satırı güncellenir), dersler sonraki döneme hazır kalır.

transcript koleksiyonu: term ("3.2" = 3. sınıf 2. dönem), code, name, lang, credits (AKTS), letter, target, order.
courses alanları: credits (AKTS), letter (gerçek), guess (ihtimal), target (hedef), retake ("" otomatik,
"none" yok, ya da transkript id'si).
"""
import re
import zipfile
from xml.etree import ElementTree as ET

from .config import prefs

POINTS = {"AA": 4.0, "BA": 3.5, "BB": 3.0, "CB": 2.5, "CC": 2.0, "DC": 1.5, "DD": 1.0, "FD": 0.5, "FF": 0.0,
          "D": 0.0, "NA": 0.0}
LETTERS = ("AA", "BA", "BB", "CB", "CC", "DC", "DD", "FD", "FF")
EXTRA_LETTERS = ("D", "NA")      # devamsız / girmedi: 0 sayılır


def points():
    """Harf → puan tablosu. Varsayılan YÖK 4'lük sistemi; okulun tablosu farklıysa Seçenekler'den değişir
    (prefs grade_points yalnızca varsayılandan farklı harfleri tutar)."""
    out = dict(POINTS)
    for k, v in (prefs.get("grade_points") or {}).items():
        if k in out:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                pass
    return out


# Sınav türleri: (anahtar, Türkçe ad, İngilizce ad, eşanlamlılar). Kayıtta Türkçe ad tutulur, ekranda dile göre
# gösterilir. Sıra = ders içinde sınavların sırası (vizeler başta, final / bütünleme sonda).
EXAM_KINDS = (
    ("vize1", "Vize 1", "Midterm 1", ("vize 1", "1. vize", "vize1", "midterm 1", "midterm1", "mt1", "ara sınav 1")),
    ("vize2", "Vize 2", "Midterm 2", ("vize 2", "2. vize", "vize2", "midterm 2", "midterm2", "mt2", "ara sınav 2")),
    ("vize", "Vize", "Midterm", ("vize", "midterm", "ara sınav", "arasınav")),
    ("quiz", "Quiz", "Quiz", ("quiz", "kısa sınav", "quizler", "quizzes")),
    ("lab", "Laboratuvar", "Lab", ("laboratuvar", "lab", "laboratory")),
    ("odev", "Ödev", "Homework", ("ödev", "odev", "ödevler", "homework", "hw", "assignment")),
    ("proje", "Proje", "Project", ("proje", "project")),
    ("rapor", "Rapor teslimi", "Report", ("rapor teslimi", "rapor", "report")),
    ("sunum", "Sunum", "Presentation", ("sunum", "presentation")),
    ("seminer", "Seminer", "Seminar", ("seminer", "seminar")),
    ("final", "Final", "Final", ("final", "final sınavı", "dönem sonu")),
    ("but", "Bütünleme", "Makeup", ("bütünleme", "büt", "makeup", "resit")),
)
_KIND = {k: (tr, en) for k, tr, en, _a in EXAM_KINDS}
_ALIAS = {a: k for k, _tr, _en, al in EXAM_KINDS for a in al}
_ORDER = {k: i for i, (k, *_r) in enumerate(EXAM_KINDS)}


def exam_kind(name):
    """Sınav adının türü ("Midterm 2" → "vize2"); tanınmazsa None."""
    return _ALIAS.get(" ".join((name or "").casefold().split()))


def exam_canon(name):
    """Kayıtta tutulacak ad: tanınan türün Türkçe adı, değilse yazıldığı gibi."""
    k = exam_kind(name)
    return _KIND[k][0] if k else (name or "").strip()


def exam_label(name, tr=True):
    """Ekranda gösterilecek ad: tanınan tür dile göre, değilse yazıldığı gibi."""
    k = exam_kind(name)
    return _KIND[k][0 if tr else 1] if k else (name or "")


def exam_names(tr=True):
    return tuple(v[0 if tr else 1] for v in _KIND.values())


def exam_order(name):
    k = exam_kind(name)
    if k is None:    # "Quiz 2", "Ödev 1": numarasız türün yerinde dursun (ad kayıtta olduğu gibi kalır)
        k = exam_kind(re.sub(r"\s*\d+\s*$", "", name or ""))
    return _ORDER[k] if k else _ORDER["final"] - 0.5      # bilinmeyenler finalden önce


def find_exam_kind(text):
    """Serbest metinde geçen en uzun tür adı (görev başlığından tahmin): Türkçe adı ya da None."""
    low = " ".join((text or "").casefold().split())
    for a in sorted(_ALIAS, key=len, reverse=True):
        if len(a) > 2 and re.search(r"(?<!\w)" + re.escape(a) + r"(?!\w)", low):
            return _KIND[_ALIAS[a]][0]
    return None


def letter_kind(letter):
    """Rozet rengi: BB ve üstü yeşil, DC / DD turuncu (koşullu geçer), FD / FF / D / NA kırmızı."""
    p = points().get((letter or "").upper())
    if p is None:
        return None
    return "good" if p >= 3 else "warn" if p >= 1 else "bad"
SCENARIOS = ("letter", "guess", "target")


def point(letter):
    """Harf (ya da sayı) → 4'lük not; not yoksa None."""
    if letter is None:
        return None
    if isinstance(letter, (int, float)):
        return float(letter)
    s = str(letter).strip().upper()
    if not s or s == "XX":
        return None
    pts = points()
    if s in pts:
        return pts[s]
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def _f(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def term_label(term, tr=True):
    m = re.match(r"^(\d+)\.(\d+)$", str(term or ""))
    if not m:
        return str(term or "—")
    return (f"{m.group(1)}. sınıf {m.group(2)}. dönem" if tr else f"Year {m.group(1)}, term {m.group(2)}")


def term_key(term):
    m = re.match(r"^(\d+)\.(\d+)$", str(term or ""))
    return (int(m.group(1)), int(m.group(2))) if m else (99, 99)


# ============================================================ transkript
def letter_of(entry, scenario="letter"):
    """Transkript satırında senaryonun harfi: hedefte hedef harf varsa o, yoksa gerçek."""
    if scenario == "target" and point(entry.get("target")) is not None:
        return entry.get("target")
    return entry.get("letter")


def totals(entries, scenario="letter"):
    """(puan, AKTS): notu olan satırların Σ AKTS × not ve Σ AKTS."""
    pts = akts = 0.0
    for e in entries:
        p = point(letter_of(e, scenario))
        if p is None:
            continue
        c = _f(e.get("credits"))
        pts += c * p
        akts += c
    return pts, akts


def gpa(pts, akts):
    return pts / akts if akts else None


def by_term(entries):
    """[(term, [satırlar])] dönem sırasıyla."""
    groups = {}
    for e in entries:
        groups.setdefault(e.get("term") or "", []).append(e)
    out = []
    for term in sorted(groups, key=term_key):
        out.append((term, sorted(groups[term], key=lambda e: (_f(e.get("order")), e.get("code") or ""))))
    return out


# ============================================================ bu dönem
def _norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().casefold()


def match_retake(course, transcript):
    """Bu dönemki dersin transkriptteki eski satırı (tekrar alınıyorsa) ya da None."""
    r = course.get("retake") or ""
    if r == "none":
        return None
    if r:
        for e in transcript:
            if e.get("id") == r:
                return e
        return None
    name, code = _norm(course.get("name")), _norm(course.get("code"))
    if name:
        for e in transcript:
            if _norm(e.get("name")) == name:
                return e
    if code:
        for e in transcript:
            if _norm(e.get("code")) == code:
                return e
    if len(name) >= 4:
        hits = [e for e in transcript if name in _norm(e.get("name"))]
        if hits:
            return min(hits, key=lambda e: len(_norm(e.get("name"))))
    return None


def course_letter(course, scenario):
    """Senaryodaki harf: gerçek harf girilmişse hep o."""
    if point(course.get("letter")) is not None or scenario == "letter":
        return course.get("letter")
    return course.get(scenario)


def semester(courses, transcript, scenario="letter"):
    """Bu dönemin sonucu: dict(ano, agno, akts, pts, n, n_all, retakes=[(ders, eski satır)]).
    Excel 5.1: T5 (ANO) ve T8 / T18 / T28 (AGNO)."""
    base_pts, base_akts = totals(transcript, scenario)
    s_pts = s_akts = old_pts = old_akts = 0.0
    n = 0
    retakes = []
    for c in courses:
        p = point(course_letter(c, scenario))
        old = match_retake(c, transcript)
        if old is not None:
            retakes.append((c, old))
        if p is None:
            continue
        cr = _f(c.get("credits"))
        s_pts += cr * p
        s_akts += cr
        n += 1
        op = point(letter_of(old, scenario)) if old is not None else None
        if op is not None:            # eski not düşülür, yenisi sayılır
            old_pts += op * _f(old.get("credits"))
            old_akts += _f(old.get("credits"))
    pts, akts = base_pts - old_pts + s_pts, base_akts - old_akts + s_akts
    return {"ano": gpa(s_pts, s_akts), "agno": gpa(pts, akts), "akts": akts, "pts": pts, "sem_akts": s_akts,
            "n": n, "n_all": len(courses), "retakes": retakes, "base": gpa(base_pts, base_akts)}


def needed_point(courses, transcript, goal, scenario="letter"):
    """Notu belli olmayan derslerden AGNO'yu goal'e çıkarmak için gereken ortalama (4'lük) ya da None."""
    known = semester([c for c in courses if point(course_letter(c, scenario)) is not None], transcript, scenario)
    rest = [c for c in courses if point(course_letter(c, scenario)) is None]
    if not rest:
        return None
    r_akts = sum(_f(c.get("credits")) for c in rest)
    old_pts = old_akts = 0.0
    for c in rest:
        old = match_retake(c, transcript)
        op = point(letter_of(old, scenario)) if old is not None else None
        if op is not None:
            old_pts += op * _f(old.get("credits"))
            old_akts += _f(old.get("credits"))
    if not r_akts:
        return None
    # (pts - old_pts + x * r_akts) / (akts - old_akts + r_akts) = goal
    return (goal * (known["akts"] - old_akts + r_akts) - (known["pts"] - old_pts)) / r_akts


def suggest_letter(score):
    """100'lük puandan yaklaşık harf (bağıl değerlendirme değil; yalnızca ipucu)."""
    if score is None:
        return None
    for lim, l in ((90, "AA"), (85, "BA"), (80, "BB"), (75, "CB"), (70, "CC"), (65, "DC"), (60, "DD"), (50, "FD")):
        if score >= lim:
            return l
    return "FF"


def finish_semester(store, term):
    """Bu dönemin gerçek harflerini transkripte yazar: tekrar alınan dersin eski satırı güncellenir (eski harf
    old_letter'da saklanır), diğerleri term dönemine eklenir. Geri almak için (eklenenler, eski hâller) döner."""
    transcript = store.all("transcript")
    added, changed = [], []
    order = max([_f(e.get("order")) for e in transcript] or [0]) + 1
    for c in store.all("courses"):
        if point(c.get("letter")) is None:
            continue
        old = match_retake(c, transcript)
        if old is not None:
            changed.append(dict(old))
            store.update("transcript", old["id"], letter=c["letter"], old_letter=old.get("letter"),
                         credits=c.get("credits") or old.get("credits"))
        else:
            added.append(store.add("transcript", {"term": term, "code": c.get("code") or "", "name": c.get("name"),
                                                  "credits": c.get("credits"), "letter": c["letter"],
                                                  "order": order}))
            order += 1
    return added, changed


# ============================================================ Excel'den al
_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
       "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def _sheets(path):
    """{sayfa adı: {(satır, sütun harfi): değer}} — openpyxl gerektirmez (xlsx = zip + XML)."""
    z = zipfile.ZipFile(path)
    names = z.namelist()
    shared = []
    if "xl/sharedStrings.xml" in names:
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", _NS):
            shared.append("".join(x.text or "" for x in si.iter("{%s}t" % _NS["m"])))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    out = {}
    for sh in wb.find("m:sheets", _NS):
        target = rels.get(sh.get("{%s}id" % _NS["r"]), "")
        p = "xl/" + target.lstrip("/").replace("xl/", "", 1)
        if p not in names:
            continue
        cells = {}
        for c in ET.fromstring(z.read(p)).iter("{%s}c" % _NS["m"]):
            m = re.match(r"([A-Z]+)(\d+)", c.get("r") or "")
            if not m:
                continue
            v = c.find("m:v", _NS)
            val = v.text if v is not None else None
            if c.get("t") == "s" and val is not None:
                val = shared[int(val)]
            elif c.get("t") == "inlineStr":
                val = "".join(x.text or "" for x in c.iter("{%s}t" % _NS["m"]))
            if val not in (None, ""):
                cells[(int(m.group(2)), m.group(1))] = val
        out[sh.get("name")] = cells
    return out


def _col_after(col, n):
    """"A" + 4 → "E" (yalnızca tek / iki harfli sütunlar)."""
    def to_i(s):
        i = 0
        for ch in s:
            i = i * 26 + ord(ch) - 64
        return i

    def to_s(i):
        s = ""
        while i:
            i, r = divmod(i - 1, 26)
            s = chr(65 + r) + s
        return s
    return to_s(to_i(col) + n)


def read_transcript_xlsx(path):
    """Transkript sayfasını okur: başlıkları KOD / DERS / AKTS / HARF olan ilk blok gerçek notlar, sağdaki
    bloklar (FALL HEDEF, SPRING HEDEF...) hedef; en sağdaki hedef harf "target" olur. Dönem başlıkları
    "1. SINIF 1. DÖNEM" satırlarından. Dönüş: [transkript satırı]."""
    sheets = _sheets(path)
    for name, cells in sheets.items():
        heads = [(r, col) for (r, col), v in cells.items() if str(v).strip().upper() == "KOD"]
        if not heads:
            continue
        hrow = min(r for r, _ in heads)
        starts = sorted((col for r, col in heads if r == hrow), key=lambda c: (len(c), c))

        def col_of(start, label):
            for k in range(0, 8):
                c = _col_after(start, k)
                if str(cells.get((hrow, c), "")).strip().upper().startswith(label):
                    return c
            return None
        blocks = [{k: col_of(s, k) for k in ("KOD", "DERS", "DİL", "AKTS", "HARF")} for s in starts]
        main = blocks[0]
        if not (main["DERS"] and main["AKTS"] and main["HARF"]):
            continue
        rows = sorted({r for r, _ in cells if r > hrow})
        term, order, out = "", 0, []
        for r in rows:
            code = str(cells.get((r, main["KOD"]), "")).strip()
            m = re.match(r"^(\d+)\.\s*SINIF\s*(\d+)\.\s*D", code.upper().replace("İ", "I"))
            if m:
                term = f"{m.group(1)}.{m.group(2)}"
                continue
            if code.upper().startswith("AGNO"):   # transkript bitti (altındaki "MEVCUT DURUM" planı alınmaz)
                break
            if not code or code.upper().startswith("TOPLAM"):
                continue
            nm = str(cells.get((r, main["DERS"]), "")).strip()
            if not nm and not code:
                continue
            target = None
            for b in blocks[1:]:
                if b["HARF"] and point(cells.get((r, b["HARF"]))) is not None:
                    target = str(cells[(r, b["HARF"])]).strip().upper()
            letter = str(cells.get((r, main["HARF"]), "")).strip().upper() or "XX"
            out.append({"term": term, "code": code, "name": nm or code,
                        "lang": str(cells.get((r, main["DİL"]), "")).strip() if main["DİL"] else "",
                        "credits": _f(cells.get((r, main["AKTS"]))), "letter": letter,
                        "target": target if target and target != letter else None, "order": order})
            order += 1
        if out:
            return out
    return []
