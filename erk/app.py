"""Uygulama girişi: tek örnek, tema, Türkçe Qt çevirisi."""
import ctypes
import os
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication

from .config import prefs, asset, DATA_DIR

# tek örnek kilidi veri klasörüne bağlı: testler (geçici LOCALAPPDATA) açık olan gerçek erk'e dokunmaz
SERVER_NAME = "erk-%08x" % (__import__("zlib").crc32(os.path.normcase(DATA_DIR).encode("utf-8")))


def _send_to_running(cmd: str) -> bool:
    sock = QLocalSocket()
    sock.connectToServer(SERVER_NAME)
    if not sock.waitForConnected(300):
        return False
    try:
        ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
    except Exception:
        pass
    sock.write(cmd.encode("utf-8"))
    sock.flush()
    sock.waitForBytesWritten(1000)
    sock.disconnectFromServer()
    return True


def _install_excepthook():
    """PyQt, bir slot içindeki yakalanmamış hatada süreci kapatır. Bunun yerine hatayı kaydet, devam et."""
    import traceback
    from .config import APP_DIR

    def hook(tp, val, tb):
        text = "".join(traceback.format_exception(tp, val, tb))
        sys.stderr.write(text)
        try:
            from datetime import datetime
            with open(os.path.join(APP_DIR, "error.log"), "a", encoding="utf-8") as f:
                f.write(f"\n--- {datetime.now():%Y-%m-%d %H:%M:%S}\n{text}")
        except OSError:
            pass
    sys.excepthook = hook


def main():
    _install_excepthook()
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("tamga.erk")
    except Exception:
        pass
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("erk")
    app.setOrganizationName("tamga")
    f = QFont("Segoe UI Variable Text")
    f.setPointSizeF(9.5)
    app.setFont(f)
    ico = asset("logo.ico") if os.path.exists(asset("logo.ico")) else asset("logo.png")
    app.setWindowIcon(QIcon(ico))

    from .i18n import apply_locale
    apply_locale()
    if prefs.get("language", "tr") == "tr":
        try:
            from PyQt6.QtCore import QTranslator, QLibraryInfo
            tr = QTranslator(app)
            if tr.load("qtbase_tr", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
                app.installTranslator(tr)
        except Exception:
            pass

    app.setQuitOnLastWindowClosed(False)   # widget açıkken ana pencere kapansa da uygulama yaşar
    if _send_to_running("show"):
        return 0
    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    server.listen(SERVER_NAME)

    from .theme import theme
    theme.apply()
    from .config import migrate_old_data
    migrate_old_data()                     # veri klasörü boşsa eski kopyadan bir kez (config.py)
    from .store import Store
    from .window import MainWindow
    store = Store()
    win = MainWindow(store)
    only_widget = "--widget" in sys.argv and prefs.get("desk_widget", False)
    if prefs.get("desk_widget", False):
        win.set_desk(True)
    if not only_widget:
        win.show()
    if prefs.get("autostart", False):   # eski kayıtlı komutu güncel tut
        from .dialogs import set_autostart
        set_autostart(True)

    def on_conn():
        s = server.nextPendingConnection()
        if s is None:
            return

        buf = bytearray()

        def read():
            buf.extend(bytes(s.readAll()))
            if not buf.startswith(b"{"):          # ikinci kez açıldı: pencereyi öne getir
                buf.clear()
                QTimer.singleShot(0, win.bring_front)
                return
            if buf.endswith(b"\n"):               # komut satırı (cli.py): bu depoda çalıştır, yanıtı yaz
                from .cli import handle_request
                s.write(handle_request(store, bytes(buf)))
                s.flush()
                buf.clear()
        s.readyRead.connect(read)
        s.disconnected.connect(s.deleteLater)
    server.newConnection.connect(on_conn)
    app.aboutToQuit.connect(store.flush)
    app._erk = (store, win, server)
    return app.exec()
