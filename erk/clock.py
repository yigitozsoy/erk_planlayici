"""Uygulama genelinde tek sayaç: kronometre (ileri sayar) ya da zamanlayıcı (geri sayar).

Ders çalışma (kind "study", ref = ders id) ve meditasyon (kind "meditation") için kullanılır. Durum prefs "clock"ta
duvar saatiyle tutulur: sayfalar yenilense ya da uygulama kapanıp açılsa da sayaç kaldığı yerden sürer.
Durdurunca (ya da zamanlayıcı bitince) "sessions" koleksiyonuna kayıt düşer; ders çalışmasıysa o gün dersin
çalışma karesi (courses.study_days) de işaretlenir. Bir dakikadan kısa oturumlar kaydedilmez.

    sessions   date, kind (study | meditation), minutes, course, start ("HH:MM"), mode (stopwatch | timer)
"""
import time
from datetime import datetime

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .config import prefs, day_of
from .store import day_set

MIN_SAVE_S = 60


def fmt_clock(sec):
    sec = max(0, int(round(sec)))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


class Clock(QObject):
    changed = pyqtSignal()          # başla / dur / bitti / sıfırla
    ticked = pyqtSignal()           # çalışırken saniyede bir
    finished = pyqtSignal(object)   # kaydedilen oturum (ya da None)

    def __init__(self, store, parent=None, now=time.time):
        super().__init__(parent)
        self.store = store
        self.now = now
        self.state = dict(prefs.get("clock") or {}) or None
        self._t = QTimer(self)
        self._t.setInterval(500)
        self._t.timeout.connect(self._tick)
        if self.state:
            self._t.start()

    # ---------------------------------------------------------------- durum
    def active(self):
        return self.state is not None

    def running(self):
        return bool(self.state and self.state.get("since"))

    def is_for(self, kind, ref=None):
        return bool(self.state and self.state.get("kind") == kind and (ref is None or self.state.get("ref") == ref))

    def elapsed(self):
        if not self.state:
            return 0.0
        e = float(self.state.get("acc", 0.0))
        if self.state.get("since"):
            e += self.now() - float(self.state["since"])
        return max(0.0, e)

    def remaining(self):
        if not self.state or self.state.get("mode") != "timer":
            return None
        return max(0.0, float(self.state.get("target", 0)) - self.elapsed())

    def display(self):
        r = self.remaining()
        return fmt_clock(self.elapsed() if r is None else r)

    def _save_state(self):
        prefs.set("clock", dict(self.state) if self.state else None)

    # ---------------------------------------------------------------- komutlar
    def start(self, kind, ref=None, mode="stopwatch", minutes=None, label=""):
        """Yeni sayaç başlatır; başka bir sayaç açıksa önce onu kaydedip kapatır."""
        if self.state:
            self.stop()
        self.state = {"kind": kind, "ref": ref, "mode": mode, "label": label, "acc": 0.0, "since": self.now(),
                      "started": datetime.now().strftime("%H:%M"), "date": day_of(datetime.now()).isoformat()}
        if mode == "timer":
            self.state["target"] = max(60, int(round((minutes or 25) * 60)))
        self._save_state()
        self._t.start()
        self.changed.emit()

    def pause(self):
        if self.running():
            self.state["acc"] = self.elapsed()
            self.state["since"] = None
            self._save_state()
            self.changed.emit()

    def resume(self):
        if self.state and not self.running():
            self.state["since"] = self.now()
            self._save_state()
            self._t.start()
            self.changed.emit()

    def toggle(self):
        self.pause() if self.running() else self.resume()

    def stop(self, save=True):
        """Sayacı kapatır; save ise (ve en az bir dakikaysa) oturumu kaydeder. Kaydı döndürür."""
        if not self.state:
            return None
        st, sec = self.state, self.elapsed()
        if st.get("mode") == "timer":
            sec = min(sec, float(st.get("target", sec)))
        self.state = None
        self._save_state()
        self._t.stop()
        rec = self._record(st, sec) if save and sec >= MIN_SAVE_S else None
        self.changed.emit()
        self.finished.emit(rec)
        return rec

    def cancel(self):
        return self.stop(save=False)

    def _record(self, st, sec):
        rec = {"date": st.get("date") or day_of(datetime.now()).isoformat(), "kind": st.get("kind"),
               "minutes": round(sec / 60.0, 1), "start": st.get("started", ""), "mode": st.get("mode")}
        if st.get("ref"):
            rec["course"] = st["ref"]
        item = self.store.add("sessions", rec)
        if st.get("kind") == "study" and st.get("ref"):
            c = self.store.get("courses", st["ref"])
            if c is not None:
                days = sorted({d.isoformat() for d in day_set(c.get("study_days"))} | {rec["date"]})
                self.store.update("courses", c["id"], study_days=days)
        return item

    def _tick(self):
        if not self.state:
            self._t.stop()
            return
        r = self.remaining()
        if r is not None and r <= 0 and self.running():
            from . import sounds
            sounds.play(prefs.get("reminder_sound", "chime"), int(prefs.get("reminder_volume", 70)) / 100)
            self.stop()
            return
        if self.running():
            self.ticked.emit()
