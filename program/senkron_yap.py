# -*- coding: utf-8 -*-
"""
Ingilizce seslendirmeyi videonun SRT zaman cizelgesine gore yeniden dizer.

Klasorde bulunmasi gerekenler:
    <video>.mp4  (veya sadece <video>.srt)
    <video>_EN.srt        -> altyazi_uret.bat ile uretilir
    englishVoice.mp3      -> senin seslendirmen

Cikti: <video>_EN_senkron.mp3   (sure = videonun suresi)

Gereken paketler: faster-whisper, numpy  (yoksa bat dosyasi kurar)
"""
import os, sys, glob, math
import numpy as np
import av

SR = 32000
TARGET_TEMPO_MAX = 1.3
GAP = 0.08
# Bosluklara eklenen, duyulmamasi gereken cok hafif ortam tonu.
# Gurultu duyuyorsan kucult ya da 0.0 yap (tamamen kapatir).
ORTAM_TONU = 0.0012

# ---------- ses okuma / yazma ----------
def decode(path, sr=SR):
    with av.open(path) as c:
        st = c.streams.audio[0]
        rs = av.AudioResampler(format="flt", layout="mono", rate=sr)
        chunks = []
        for frame in c.decode(st):
            for f in rs.resample(frame):
                chunks.append(f.to_ndarray().reshape(-1))
        for f in rs.resample(None) or []:
            chunks.append(f.to_ndarray().reshape(-1))
    return np.concatenate(chunks).astype(np.float32) if chunks else np.zeros(0, np.float32)

def encode_mp3(x, path, sr=SR, bitrate=192000):
    x = np.clip(x, -1.0, 1.0)
    with av.open(path, "w") as c:
        st = c.add_stream("mp3", rate=sr)
        st.bit_rate = bitrate
        try: st.layout = "mono"
        except Exception: pass
        block = 1152 * 20
        for i in range(0, len(x), block):
            seg = x[i:i + block]
            frame = av.AudioFrame.from_ndarray(seg.reshape(1, -1).copy(), format="flt", layout="mono")
            frame.sample_rate = sr
            frame.pts = None
            for p in st.encode(frame): c.mux(p)
        for p in st.encode(None): c.mux(p)

# ---------- zaman-esnetme (WSOLA, perde korur) ----------
def time_stretch(x, rate, sr=SR):
    if rate <= 1.001 or len(x) < sr // 10: return x
    frame = int(0.040 * sr); hop_out = frame // 2
    hop_in = int(round(hop_out * rate)); search = int(0.010 * sr)
    win = np.hanning(frame).astype(np.float32)
    out = np.zeros(int(len(x) / rate) + frame * 2, np.float32)
    norm = np.zeros_like(out)
    pos_in = 0; pos_out = 0; prev_tail = None
    while pos_in + frame + search < len(x) and pos_out + frame < len(out):
        if prev_tail is None:
            best = pos_in
        else:
            lo = max(0, pos_in - search); hi = min(len(x) - frame, pos_in + search)
            cand = np.arange(lo, hi + 1, 16)
            scores = [float(np.dot(x[c:c + hop_out], prev_tail)) for c in cand]
            best = int(cand[int(np.argmax(scores))]) if len(cand) else pos_in
        seg = x[best:best + frame] * win
        out[pos_out:pos_out + frame] += seg
        norm[pos_out:pos_out + frame] += win
        prev_tail = x[best + hop_out:best + hop_out + hop_out]
        pos_in = best + hop_in; pos_out += hop_out
    norm[norm < 1e-3] = 1.0
    return (out[:pos_out + frame] / norm[:pos_out + frame]).astype(np.float32)

# ---------- sessizlik bulma ----------
def silences(x, sr=SR, thresh_db=-33.0, min_dur=0.25):
    fr = int(0.020 * sr)
    n = len(x) // fr
    rms = np.sqrt(np.maximum(np.mean(x[:n * fr].reshape(n, fr) ** 2, axis=1), 1e-12))
    quiet = 20 * np.log10(rms) < thresh_db
    res = []; i = 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]: j += 1
            if (j - i) * 0.020 >= min_dur: res.append((i * 0.020, j * 0.020))
            i = j
        else: i += 1
    return res

# ---------- srt ----------
def parse_srt(path):
    txt = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n").strip()
    items = []
    for b in txt.split("\n\n"):
        p = [l for l in b.strip().split("\n") if l.strip()]
        if len(p) < 3: continue
        a, c = p[1].split(" --> ")
        items.append((to_sec(a), to_sec(c), " ".join(p[2:]).strip()))
    return items

def to_sec(t):
    t = t.strip().replace(".", ",")
    h, m, rest = t.split(":"); s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

def norm_word(w):
    return "".join(ch for ch in w.lower() if ch.isalnum())

def dur_tahmin(path):
    try:
        with av.open(path) as c:
            return float(c.duration) / av.time_base
    except Exception:
        return 0.0

# ---------- ana akis ----------
def main(folder=None):
    os.chdir(folder or os.path.dirname(os.path.abspath(sys.argv[0])) or ".")
    en_srts = glob.glob("*_EN.srt")
    if not en_srts:
        print("HATA: *_EN.srt bulunamadi. Once altyazi_uret.bat calistir."); return
    en_srt = en_srts[0]
    base = en_srt[:-7]
    voice_path = "englishVoice.mp3"
    if not os.path.isfile(voice_path):
        cand = [f for f in glob.glob("*.mp3") if "senkron" not in f.lower()]
        if not cand:
            print("HATA: englishVoice.mp3 bulunamadi."); return
        voice_path = cand[0]
    print("Ses      :", voice_path)
    print("Altyazi  :", en_srt)

    cues = parse_srt(en_srt)
    n = len(cues)
    total = cues[-1][1]
    video = base + ".mp4"
    if os.path.isfile(video):
        try:
            with av.open(video) as c: total = max(total, float(c.duration) / av.time_base)
        except Exception: pass
    print("Cumle    : %d   hedef sure: %.2f sn" % (n, total))

    print("\nKelime zamanlamalari cikariliyor (faster-whisper)...")
    from faster_whisper import WhisperModel
    model = WhisperModel("medium", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(voice_path, language="en", word_timestamps=True,
                               vad_filter=False, condition_on_previous_text=False)
    words = []
    _sure = dur_tahmin(voice_path)
    for s in segs:
        if _sure > 0:
            try: print("##P %.4f" % min(0.55, 0.55 * float(s.end) / _sure))
            except Exception: pass
        for w in (s.words or []):
            t = norm_word(w.word)
            if t: words.append((t, float(w.start), float(w.end)))
    print("  %d kelime bulundu" % len(words))
    if not words:
        print("HATA: seste kelime bulunamadi."); return

    # cumleleri kelime akisina sirayla dagit
    bounds = []; k = 0
    for idx, (_, _, text) in enumerate(cues):
        toks = [norm_word(t) for t in text.split()]
        toks = [t for t in toks if t]
        want = len(toks)
        start_k = k
        take = min(want, len(words) - k)
        if take <= 0:
            bounds.append(None); continue
        # whisper kelimeleri farkli bolebilir: sonraki cumlenin ilk kelimesine gore +-3 duzelt
        nxt = None
        if idx + 1 < len(cues):
            nt = [norm_word(t) for t in cues[idx + 1][2].split()]
            nt = [t for t in nt if t]
            nxt = nt[0] if nt else None
        if nxt:
            best = take; bestscore = -1
            for d in (0, 1, -1, 2, -2, 3, -3):
                c = take + d
                if c < 1 or start_k + c >= len(words): continue
                score = 1 if words[start_k + c][0] == nxt else 0
                if score > bestscore: bestscore = score; best = c
                if score == 1: break
            take = best
        k = start_k + take
        bounds.append((words[start_k][1], words[k - 1][2]))
    bounds = [b for b in bounds]
    if any(b is None for b in bounds):
        print("UYARI: bazi cumleler seste bulunamadi; metin ile seslendirme birebir ayni mi?")

    x = decode(voice_path)
    dur = len(x) / SR
    sil = silences(x)
    begins = [b[0] if b else 0.0 for b in bounds]
    ends = [b[1] if b else 0.0 for b in bounds]

    snapped = 0
    for i in range(n - 1):
        b = ends[i]; best = None; bd = 1e9
        for s, e in sil:
            d = min(abs(s - b), abs(e - b), abs((s + e) / 2 - b))
            if d < bd: bd = d; best = (s, e)
        if best and bd <= 1.2:
            ends[i] = best[0]; begins[i + 1] = best[1]; snapped += 1
        else:
            begins[i + 1] = max(ends[i], begins[i + 1])
    ends[-1] = min(dur, max(ends[-1], begins[-1] + 0.2))
    print("  %d/%d cumle siniri gercek duraklamaya oturdu" % (snapped, n - 1))

    canvas = np.zeros(int(total * SR) + SR, np.float32)
    prev_end = 0.0; stretched = 0; pushed = 0; drift = 0.0
    for i in range(n):
        a = int(max(0.0, begins[i]) * SR); b = int(min(ends[i], dur) * SR)
        seg = x[a:b].copy()
        if len(seg) < 10: continue
        pos = max(cues[i][0], prev_end + GAP)
        drift = max(drift, pos - cues[i][0])
        slot = (cues[i + 1][0] - pos) if i < n - 1 else (total - pos - 0.05)
        L = len(seg) / SR
        if L > slot and slot > 0.3:
            r = min(TARGET_TEMPO_MAX, L / slot)
            seg = time_stretch(seg, r); stretched += 1
            if len(seg) / SR > slot: pushed += 1
        f_i = int(0.040 * SR); f_o = int(0.120 * SR)
        if len(seg) > f_i + f_o:
            seg[:f_i] *= np.linspace(0, 1, f_i); seg[-f_o:] *= np.linspace(1, 0, f_o)
        print("##P %.4f" % (0.55 + 0.40 * (i + 1) / float(n)))
        off = int(pos * SR); end = off + len(seg)
        if end > len(canvas): canvas = np.concatenate([canvas, np.zeros(end - len(canvas), np.float32)])
        canvas[off:end] += seg
        prev_end = end / SR
    print("  %d cumle hafif hizlandirildi, %d cumle sonrakini oteledi, en fazla kayma %.2f sn" % (stretched, pushed, drift))

    # cok hafif ortam tonu (pink noise) - olu dijital sessizligi kaldirir
    if ORTAM_TONU > 0:
        n = len(canvas)
        rng = np.random.default_rng(7)
        w = rng.standard_normal(n).astype(np.float32)
        spec = np.fft.rfft(w)
        f = np.arange(len(spec)); f[0] = 1
        spec /= np.sqrt(f)
        pink = np.fft.irfft(spec, n).astype(np.float32)
        pink *= ORTAM_TONU / (float(np.std(pink)) + 1e-9)
        mix = canvas + pink
    else:
        mix = canvas
    peak = float(np.max(np.abs(mix)))
    if peak > 0.99: mix *= 0.99 / peak
    mix = mix[:int(total * SR)]

    out = base + "_EN_senkron.mp3"
    if os.path.isfile(out):
        i = 2
        while os.path.isfile("%s_EN_senkron_v%d.mp3" % (base, i)): i += 1
        out = "%s_EN_senkron_v%d.mp3" % (base, i)
    encode_mp3(mix, out)
    print("\nBitti: %s   (%.2f sn)" % (out, len(mix) / SR))
    print("Camtasia'da sesin basini videonun 0:00'ina hizala, time scaling yapma.")

if __name__ == "__main__":
    import sys as _s, os as _o
    main(_s.argv[1] if len(_s.argv) > 1 and _o.path.isdir(_s.argv[1]) else None)
