# -*- coding: utf-8 -*-
"""Klasordeki mp4 dosyalarindan Turkce .srt uretir (faster-whisper)."""
import os, sys, glob

MODEL = "medium"

def ts(sec):
    if sec < 0: sec = 0
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)

def sure_bul(src):
    try:
        import av
        with av.open(src) as c:
            return float(c.duration) / av.time_base
    except Exception:
        return 0.0

def transcribe(src, model):
    print("Transkripsiyon: %s" % os.path.basename(src))
    toplam = sure_bul(src)
    segments, info = model.transcribe(src, language="tr", beam_size=5, vad_filter=True,
                                      vad_parameters=dict(min_silence_duration_ms=500),
                                      condition_on_previous_text=False)
    out = os.path.splitext(src)[0] + ".srt"
    n = 0
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for seg in segments:
            text = seg.text.strip()
            if not text: continue
            n += 1
            f.write("%d\n%s --> %s\n%s\n\n" % (n, ts(seg.start), ts(seg.end), text))
            print("  [%s] %s" % (ts(seg.start), text[:70]))
            if toplam > 0:
                print("##P %.4f" % min(0.99, float(seg.end) / toplam))
    print("  [OK] %s (%d satir)" % (os.path.basename(out), n))

def main(folder=None):
    os.chdir(folder or os.path.dirname(os.path.abspath(sys.argv[0])) or ".")
    videos = sorted(glob.glob("*.mp4"))
    if not videos:
        print("HATA: Klasorde .mp4 bulunamadi."); return
    todo = [v for v in videos if not os.path.isfile(os.path.splitext(v)[0] + ".srt")]
    for v in videos:
        if v not in todo: print("[ATLANDI] %s.srt zaten var" % os.path.splitext(v)[0])
    if not todo:
        return
    print("Model yukleniyor (%s)... ilk seferde indirir." % MODEL)
    from faster_whisper import WhisperModel
    model = WhisperModel(MODEL, device="cpu", compute_type="int8")
    for v in todo: transcribe(v, model)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]) else None)
