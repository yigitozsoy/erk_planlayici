"""Hatırlatma sesleri: dışarıdan dosya yok, WAV'lar burada sentezlenir (APP_DIR\\sounds) ve winsound ile çalınır.
Testte / offscreen'de (QT_QPA_PLATFORM=offscreen) ya da ERK_MUTE=1 iken çalınmaz, yalnızca dosya üretilir."""
import math
import os
import struct
import wave

from .config import APP_DIR

RATE = 44100
SOUNDS = ("chime", "soft", "alarm", "system", "none")
SOUND_DIR = os.path.join(APP_DIR, "sounds")


def _bell(freq, dur, amp, decay):
    """Zil benzeri ton: temel + iki üst ton, üstel sönüm, kısa yumuşak giriş."""
    n = int(RATE * dur)
    out = []
    for i in range(n):
        tt = i / RATE
        env = math.exp(-decay * tt) * min(1.0, tt / 0.004)
        v = (math.sin(2 * math.pi * freq * tt) + 0.45 * math.sin(2 * math.pi * freq * 2.0 * tt) * math.exp(-3 * tt)
             + 0.2 * math.sin(2 * math.pi * freq * 3.01 * tt) * math.exp(-6 * tt))
        out.append(amp * env * v / 1.65)
    return out


def _mix(parts, total):
    buf = [0.0] * int(RATE * total)
    for start, samples in parts:
        o = int(RATE * start)
        for i, v in enumerate(samples):
            if o + i < len(buf):
                buf[o + i] += v
    return buf


def synth(name, volume=0.7):
    """Örnek listesi (-1..1)."""
    a = max(0.0, min(1.0, volume)) * 0.9
    if name == "chime":       # iki notalı yumuşak zil (La5 → Mi6)
        return _mix([(0.0, _bell(880.0, 0.9, a, 5.0)), (0.16, _bell(1318.5, 1.1, a, 4.2))], 1.3)
    if name == "soft":        # tek, sıcak ve kısa ton
        return _mix([(0.0, _bell(659.3, 1.0, a * 0.9, 4.0)), (0.0, _bell(987.8, 0.8, a * 0.35, 6.0))], 1.0)
    if name == "alarm":       # üç kısa, belirgin bip (önemli işler için iyi)
        parts = [(k * 0.22, _bell(1046.5, 0.18, a, 14.0)) for k in range(3)]
        return _mix(parts, 0.75)
    return []


def path_for(name, volume):
    v = int(round(max(0.0, min(1.0, volume)) * 100))
    return os.path.join(SOUND_DIR, f"{name}-{v}.wav")


def ensure(name, volume=0.7):
    """Sesi diske yazar (yoksa) ve yolunu döndürür; system / none için None."""
    if name not in ("chime", "soft", "alarm"):
        return None
    p = path_for(name, volume)
    if os.path.exists(p):
        return p
    os.makedirs(SOUND_DIR, exist_ok=True)
    samples = synth(name, volume)
    tmp = p + ".tmp"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767)) for s in samples))
    os.replace(tmp, p)
    return p


def muted():
    return os.environ.get("ERK_MUTE") == "1" or os.environ.get("QT_QPA_PLATFORM") == "offscreen"


def play(name, volume=0.7):
    """Çalar (arka planda). Çalınacak bir şey yoksa ya da sessizse False."""
    if name == "none":
        return False
    p = ensure(name, volume)
    if muted():
        return False
    try:
        import winsound
        if name == "system" or p is None:
            winsound.PlaySound("SystemNotification", winsound.SND_ALIAS | winsound.SND_ASYNC)
        else:
            winsound.PlaySound(p, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        return True
    except (ImportError, RuntimeError, OSError):
        return False
