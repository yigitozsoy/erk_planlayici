"""Derleme öncesi üretilen dosyalar: exe sürüm bilgisi (version_info.txt) ve kurulum sürümü (version.iss).

Kullanım: python packaging/make_meta.py   (build.ps1 otomatik çalıştırır; sürümü yazdırır)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from alphaapp import __version__, __author__  # noqa: E402

parts = [int(p) for p in __version__.split(".")[:3]]
ver4 = tuple((parts + [0, 0, 0, 0])[:4])
ver_str = ".".join(map(str, ver4))

VERSION_INFO = f"""# UTF-8 — make_meta.py tarafından üretildi
VSVersionInfo(
  ffi=FixedFileInfo(filevers={ver4}, prodvers={ver4}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('041F04B0', [
      StringStruct('CompanyName', '{__author__}'),
      StringStruct('FileDescription', 'alpha'),
      StringStruct('FileVersion', '{ver_str}'),
      StringStruct('InternalName', 'alpha'),
      StringStruct('LegalCopyright', '© {__author__} — GPL-3.0'),
      StringStruct('OriginalFilename', 'alpha.exe'),
      StringStruct('ProductName', 'alpha'),
      StringStruct('ProductVersion', '{__version__}')])]),
    VarFileInfo([VarStruct('Translation', [1055, 1200])])
  ]
)
"""

if __name__ == "__main__":
    with open(os.path.join(HERE, "version_info.txt"), "w", encoding="utf-8") as f:
        f.write(VERSION_INFO)
    with open(os.path.join(HERE, "version.iss"), "w", encoding="utf-8-sig") as f:
        f.write(f'#define AppVersion "{__version__}"\n')
    print(__version__)
