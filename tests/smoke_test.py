"""Uçtan uca duman testi: geçici veri klasörü + örnek veri, tüm sayfalar ve formlar, ekran görüntüleri.

python tests/smoke_test.py                 # test
python tests/smoke_test.py --shots DIR     # ayrıca her sayfanın PNG'sini DIR'e kaydet (açık + koyu tema)
Adımlar tests/steps/ altında konu konu; ortak kurulum tests/smoke_base.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smoke_base import STEPS, seed, _tmp  # noqa: E402  (önce: geçici klasörler, gerçek veriye dokunmaz)
from steps import MODULES  # noqa: E402  (adımları sırayla kaydeder)
from datetime import date  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    assert MODULES and STEPS, "adım yok"
    shots = None
    if "--shots" in sys.argv:
        shots = sys.argv[sys.argv.index("--shots") + 1]
        os.makedirs(shots, exist_ok=True)
    app = QApplication(sys.argv)
    # PyQt slot içindeki yakalanmamış hatada süreci kapatır; burada toplayıp test hatası say
    slot_errors = []

    def hook(tp, val, tb):
        import traceback
        slot_errors.append("".join(traceback.format_exception(tp, val, tb)))
    sys.excepthook = hook
    from erk.config import prefs, DATA_DIR, APP_DIR, PREFS_FILE
    assert DATA_DIR.startswith(_tmp) and APP_DIR.startswith(_tmp) and PREFS_FILE.startswith(_tmp), DATA_DIR
    prefs.set("name", "Test")
    prefs.set("day_end_hour", 0)   # örnek veri takvim gününe göre; gece 00-04 arası da aynı sonuç
    prefs.set("last_plan", date.today().isoformat())   # plan ekranı kendi adımında test edilir
    from erk.i18n import apply_locale
    apply_locale()
    from erk.theme import theme
    theme.apply("amoled")
    from erk.store import Store
    from erk.window import MainWindow
    store = Store()
    seed(store)
    win = MainWindow(store)
    win.resize(1400, 900)
    win.show()
    app.processEvents()
    ctx = {"app": app, "store": store, "win": win, "shots": shots}
    failed = 0
    for i, (name, fn) in enumerate(STEPS, 1):
        try:
            fn(ctx)
            print(f"[{i:2}/{len(STEPS)}] ok   {name}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            import traceback
            traceback.print_exc()
            print(f"[{i:2}/{len(STEPS)}] FAIL {name}: {e}")
    win.close()
    if slot_errors:
        failed += 1
        print("\nArka planda yakalanan hatalar:")
        for e in slot_errors[:5]:
            print(e)
    print("\n" + ("HEPSİ GEÇTİ" if not failed else f"{failed} ADIM BAŞARISIZ"))
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        code = main()
    except BaseException:          # kurulumda (adımlardan önce) çıkan hata da görünsün: excepthook onu yutar
        import traceback
        traceback.print_exc()
        print("KURULUM BAŞARISIZ")
        code = 1
    sys.exit(code)
