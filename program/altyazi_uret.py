# -*- coding: utf-8 -*-
"""
Bulundugu klasordeki altyazi dosyalarini uretir:
  <video>.srt            (TR, temizlenmis)         -> <video>_TR.vtt
  <video>_EN_metin.txt   (EN duz metin, satir=cumle) -> <video>_EN.srt (TR zamanlamalariyla)
  <video>_EN.srt                                    -> <video>_EN.vtt
Kullanim: altyazi_uret.bat (cift tikla)
"""
import os, sys, glob

def read(p):
    return open(p, encoding="utf-8-sig").read().replace("\r\n", "\n").strip()

def blocks(srt):
    return [b for b in read(srt).split("\n\n") if b.strip()]

def srt2vtt(src, dst):
    out = ["WEBVTT", ""]
    for b in blocks(src):
        p = b.strip().split("\n")
        if len(p) < 3:
            continue
        out.append(p[1].replace(",", "."))
        out.extend(p[2:])
        out.append("")
    open(dst, "w", encoding="utf-8", newline="\n").write("\n".join(out))
    print("  [OK]", os.path.basename(dst))

def build_en_srt(tr_srt, en_txt, dst):
    bs = blocks(tr_srt)
    lines = [l.strip() for l in open(en_txt, encoding="utf-8-sig") if l.strip()]
    if len(bs) != len(lines):
        print("  [HATA] Satir sayisi uyusmuyor: %s icinde %d blok, %s icinde %d satir."
              % (os.path.basename(tr_srt), len(bs), os.path.basename(en_txt), len(lines)))
        print("         EN metin satir sayisi SRT blok sayisiyla ayni olmali. _EN.srt uretilmedi.")
        return False
    out = []
    for i, (b, t) in enumerate(zip(bs, lines), 1):
        out.append("%d\n%s\n%s\n" % (i, b.split("\n")[1], t))
    open(dst, "w", encoding="utf-8", newline="\n").write("\n".join(out))
    print("  [OK]", os.path.basename(dst))
    return True

def main(folder=None):
    os.chdir(folder or os.path.dirname(os.path.abspath(sys.argv[0])) or ".")
    srts = [s for s in glob.glob("*.srt") if not s.endswith("_EN.srt")]
    if not srts:
        print("Bu klasorde TR .srt bulunamadi.")
        return
    for tr in srts:
        base = os.path.splitext(tr)[0]
        print("== %s" % base)
        en_txt = base + "_EN_metin.txt"
        en_srt = base + "_EN.srt"
        if os.path.isfile(en_txt):
            build_en_srt(tr, en_txt, en_srt)
        elif not os.path.isfile(en_srt):
            print("  [ATLANDI] %s yok, EN altyazi uretilemedi." % os.path.basename(en_txt))
        print("##P 0.6")
        srt2vtt(tr, base + "_TR.vtt")
        if os.path.isfile(en_srt):
            srt2vtt(en_srt, base + "_EN.vtt")
        print("##P 1.0")

if __name__ == "__main__":
    import sys as _s, os as _o
    main(_s.argv[1] if len(_s.argv) > 1 and _o.path.isdir(_s.argv[1]) else None)
