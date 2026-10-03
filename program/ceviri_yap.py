# -*- coding: utf-8 -*-
"""
<video>.srt (Turkce) -> duzeltilmis <video>.srt + <video>_EN_metin.txt (Ingilizce duz metin)

- sozluk.txt icindeki "yanlis=dogru" satirlarini once uygular (whisper hatalari, terimler)
- Ceviriyi bilgisayarda, internetsiz calisan Argos Translate ile yapar
  (ilk calistirmada tr->en modeli bir kez iner, ~100 MB)
- Satir sayisi SRT blok sayisiyla BIREBIR ayni kalir
"""
import os, sys, glob, re

def sozluk_yolu():
    """Once video klasoru, sonra program klasoru, sonra bir ust klasor."""
    kod = os.path.dirname(os.path.abspath(__file__))
    for p in ("sozluk.txt",
              os.path.join(kod, "sozluk.txt"),
              os.path.join(os.path.dirname(kod), "sozluk.txt")):
        if os.path.isfile(p): return p
    return "sozluk.txt"

def load_sozluk(path=None):
    path = path or sozluk_yolu()
    rules = []
    if os.path.isfile(path):
        for line in open(path, encoding="utf-8-sig"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line: continue
            a, b = line.split("=", 1)
            if a.strip(): rules.append((a.strip(), b.strip()))
    return rules

def apply_sozluk(text, rules):
    for a, b in rules:
        text = re.sub(re.escape(a), b, text, flags=re.IGNORECASE)
    return text

def tidy(text):
    t = " ".join(text.split())
    if not t: return t
    t = t[0].upper() + t[1:]
    if t[-1] not in ".!?:": t += "."
    return t

def parse_srt(path):
    raw = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n").strip()
    items = []
    for b in raw.split("\n\n"):
        p = [l for l in b.strip().split("\n") if l.strip()]
        if len(p) < 3: continue
        items.append((p[1], " ".join(p[2:]).strip()))
    return items

def get_translator():
    import argostranslate.package as pkg, argostranslate.translate as tr
    langs = tr.get_installed_languages()
    def find():
        src = next((l for l in tr.get_installed_languages() if l.code == "tr"), None)
        dst = next((l for l in tr.get_installed_languages() if l.code == "en"), None)
        return (src.get_translation(dst) if src and dst else None)
    t = find()
    if t: return t
    print("  tr->en ceviri modeli indiriliyor (bir kez, ~100 MB)...")
    pkg.update_package_index()
    avail = pkg.get_available_packages()
    want = next((p for p in avail if p.from_code == "tr" and p.to_code == "en"), None)
    if want is None:
        print("  HATA: tr->en paketi bulunamadi (internet?)."); return None
    pkg.install_from_path(want.download())
    return find()

def main(folder=None):
    os.chdir(folder or os.path.dirname(os.path.abspath(sys.argv[0])) or ".")
    srts = [s for s in glob.glob("*.srt") if not s.endswith("_EN.srt")]
    if not srts:
        print("HATA: Turkce .srt bulunamadi. Once 1_transkript.bat calistir."); return
    src = srts[0]; base = os.path.splitext(src)[0]
    rules = load_sozluk()
    print("Kaynak : %s  (%d sozluk kurali)" % (src, len(rules)))

    items = parse_srt(src)
    tr_lines = [tidy(apply_sozluk(t, rules)) for _, t in items]

    # duzeltilmis TR srt'yi yaz
    out_tr = "\n".join("%d\n%s\n%s\n" % (i, items[i-1][0], tr_lines[i-1]) for i in range(1, len(items)+1))
    open(src, "w", encoding="utf-8", newline="\n").write(out_tr)
    print("  [OK] %s (duzeltilmis Turkce)" % src)

    t = get_translator()
    if t is None: return
    print("  %d cumle cevriliyor..." % len(tr_lines))
    en = []
    for i, line in enumerate(tr_lines, 1):
        try:
            e = t.translate(line).strip()
        except Exception as ex:
            print("   [uyari] %d. satir cevrilemedi (%s)" % (i, ex)); e = line
        en.append(" ".join(e.split()))
        print("##P %.4f" % (i / float(len(tr_lines))))
        if i % 10 == 0: print("   %d/%d" % (i, len(tr_lines)))
    dst = base + "_EN_metin.txt"
    open(dst, "w", encoding="utf-8", newline="\n").write("\n".join(en) + "\n")
    print("  [OK] %s (%d satir)" % (dst, len(en)))
    print("\nMetni okuyup gerekirse elle duzelt, sonra 3. adimi calistir.")

if __name__ == "__main__":
    import sys as _s, os as _o
    main(_s.argv[1] if len(_s.argv) > 1 and _o.path.isdir(_s.argv[1]) else None)
