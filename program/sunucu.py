# -*- coding: utf-8 -*-
"""
Paye Games Dub Studio - yerel web sunucusu.
Tarayıcıda arayüzü açar, adımları bu makinede çalıştırır.
Dışarıya hiçbir bağlantı açmaz; yalnızca 127.0.0.1 dinler.
"""
import os, sys, json, time, threading, queue, webbrowser, traceback, glob, socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)
KOK = os.path.dirname(BURASI)
SURUM = "v2.0"

ADIMLAR = [
    dict(no=1, modul="transkript_yap", baslik="Türkçe transkript",
         aciklama="Klasördeki mp4 → &lt;video&gt;.srt  (konuşmayı yazıya döker)",
         urun=lambda b: b + ".srt"),
    dict(no=2, modul="ceviri_yap", baslik="Düzeltme + İngilizce metin",
         aciklama="Sözlük düzeltmeleri + çeviri → &lt;video&gt;_EN_metin.txt",
         urun=lambda b: b + "_EN_metin.txt"),
    dict(no=3, modul="altyazi_uret", baslik="Altyazılar",
         aciklama="→ &lt;video&gt;_EN.srt, &lt;video&gt;_TR.vtt, &lt;video&gt;_EN.vtt",
         urun=lambda b: b + "_EN.vtt"),
    dict(no=4, modul="senkron_yap", baslik="Sesi senkronla",
         aciklama="englishVoice.mp3 → &lt;video&gt;_EN_senkron.mp3 (video süresinde)",
         urun=lambda b: b + "_EN_senkron.mp3"),
]

AYAR_YOLU = os.path.join(BURASI, "ayarlar.json")


def ayar_oku():
    try:
        with open(AYAR_YOLU, encoding="utf-8") as f: return json.load(f)
    except Exception:
        return {}

def ayar_yaz(d):
    try:
        with open(AYAR_YOLU, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


class Durum:
    def __init__(self):
        self.kilit = threading.Lock()
        self.calisiyor = False
        self.adim = 0
        self.oran = 0.0
        self.basla = 0.0
        self.kalan = ""
        self.sira = []
        self.aboneler = []          # SSE kuyruklari

    def yayinla(self, tur, veri):
        paket = json.dumps({"tur": tur, "veri": veri}, ensure_ascii=False)
        with self.kilit:
            for q in list(self.aboneler):
                q.put(paket)

    def abone(self):
        q = queue.Queue()
        with self.kilit: self.aboneler.append(q)
        return q

    def cik(self, q):
        with self.kilit:
            if q in self.aboneler: self.aboneler.remove(q)

D = Durum()


class Yazici:
    """print() ciktisini SSE'ye aktarir, ##P satirlarini ilerlemeye cevirir."""
    def __init__(self): self.tampon = ""
    def write(self, s):
        if not s: return
        self.tampon += s
        while "\n" in self.tampon:
            satir, self.tampon = self.tampon.split("\n", 1)
            self._satir(satir)
    def _satir(self, satir):
        t = satir.strip()
        if t.startswith("##P "):
            try:
                o = float(t[4:]); D.oran = max(0.0, min(1.0, o))
                gecen = time.time() - D.basla
                kalan = ""
                if D.oran > 0.02:
                    k = gecen * (1 - D.oran) / D.oran
                    kalan = "%d saniye" % int(k) if k < 60 else "%d dakika" % max(int(k // 60), 1)
                D.kalan = kalan
                D.yayinla("ilerleme", {"oran": D.oran, "kalan": kalan})
            except ValueError:
                pass
            return
        if not satir.strip(): return
        seviye = "bilgi"
        if "===" in satir: seviye = "baslik"
        elif "[OK]" in satir or satir.startswith("Bitti"): seviye = "ok"
        elif "HATA" in satir or "EKSIK" in satir: seviye = "hata"
        elif "UYARI" in satir or "ATLANDI" in satir: seviye = "uyari"
        D.yayinla("gunluk", {"metin": satir, "seviye": seviye, "saat": time.strftime("%H:%M:%S")})
    def flush(self): pass


def klasor_tara(klasor):
    sonuc = {"videolar": [], "adimlar": []}
    if not klasor or not os.path.isdir(klasor):
        sonuc["adimlar"] = [{"durum": "yok", "dosya": "Klasör bulunamadı"} for _ in ADIMLAR]
        return sonuc
    videolar = sorted(glob.glob(os.path.join(klasor, "*.mp4")))
    sonuc["videolar"] = [os.path.basename(v) for v in videolar]
    base = os.path.splitext(videolar[0])[0] if videolar else None
    ses_var = any(os.path.isfile(os.path.join(klasor, x)) for x in ("englishVoice.mp3",)) or \
              any("senkron" not in os.path.basename(m).lower() for m in glob.glob(os.path.join(klasor, "*.mp3")))
    for a in ADIMLAR:
        if not base:
            sonuc["adimlar"].append({"durum": "yok", "dosya": "Klasörde mp4 yok"}); continue
        u = a["urun"](base)
        if os.path.isfile(u):
            sonuc["adimlar"].append({"durum": "hazir", "dosya": os.path.basename(u)})
        elif a["no"] == 4 and not ses_var:
            sonuc["adimlar"].append({"durum": "bekliyor", "dosya": "englishVoice.mp3 gerekli"})
        else:
            sonuc["adimlar"].append({"durum": "bekliyor", "dosya": "Henüz çalıştırılmadı"})
    return sonuc


def adim_calistir(no, klasor, sira=None):
    a = ADIMLAR[no - 1]
    eski = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = Yazici()
    ok = False
    try:
        D.calisiyor = True; D.adim = no; D.oran = 0.0; D.basla = time.time()
        D.yayinla("adim", {"no": no, "durum": "calisiyor"})
        print("===  %d. adım — %s  ===" % (no, a["baslik"]))
        __import__(a["modul"]).main(klasor)
        ok = True
    except ModuleNotFoundError as e:
        print("EKSIK PAKET: %s" % e.name)
        print("Komut istemine yaz:  pip install %s" % e.name)
    except Exception:
        print("HATA:\n" + traceback.format_exc())
    finally:
        sys.stdout, sys.stderr = eski
        D.calisiyor = False
        D.oran = 1.0 if ok else D.oran
        D.yayinla("adim", {"no": no, "durum": "bitti" if ok else "hata"})
        D.yayinla("tara", klasor_tara(klasor))
        if ok and sira:
            sonraki = sira[0]
            threading.Timer(0.6, adim_calistir, (sonraki, klasor, sira[1:])).start()


def klasor_sec_diyalog(baslangic):
    """Windows klasor secme penceresi (tkinter varsa)."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        r = tk.Tk(); r.withdraw(); r.attributes("-topmost", True)
        d = filedialog.askdirectory(initialdir=baslangic or KOK)
        r.destroy()
        return d or ""
    except Exception:
        return ""


HTML_YOLU = os.path.join(BURASI, "arayuz.html")


class Sunucu(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _gonder(self, kod, tur, govde, ek=None):
        self.send_response(kod)
        self.send_header("Content-Type", tur)
        self.send_header("Cache-Control", "no-store")
        for k, v in (ek or {}).items(): self.send_header(k, v)
        self.end_headers()
        if isinstance(govde, str): govde = govde.encode("utf-8")
        if govde: self.wfile.write(govde)

    def _json(self, d): self._gonder(200, "application/json; charset=utf-8", json.dumps(d, ensure_ascii=False))

    def do_GET(self):
        u = urlparse(self.path); p = u.path; q = parse_qs(u.query)
        if p in ("/", "/index.html"):
            try:
                with open(HTML_YOLU, encoding="utf-8") as f: html = f.read()
            except Exception as e:
                self._gonder(500, "text/plain; charset=utf-8", "arayuz.html okunamadi: %s" % e); return
            ayar = ayar_oku()
            html = html.replace("__KLASOR__", (ayar.get("klasor") or KOK).replace("\\", "\\\\"))
            html = html.replace("__SURUM__", SURUM)
            self._gonder(200, "text/html; charset=utf-8", html); return

        if p == "/api/tara":
            k = (q.get("klasor") or [""])[0]
            if k: ayar_yaz({"klasor": k})
            self._json(klasor_tara(k)); return

        if p == "/api/sec":
            d = klasor_sec_diyalog((q.get("klasor") or [""])[0])
            if d: ayar_yaz({"klasor": os.path.normpath(d)})
            self._json({"klasor": os.path.normpath(d) if d else ""}); return

        if p == "/api/ac":
            ne = (q.get("ne") or ["klasor"])[0]
            yol = (q.get("klasor") or [""])[0] if ne == "klasor" else os.path.join(BURASI, "sozluk.txt")
            if ne == "sozluk" and not os.path.isfile(yol):
                open(yol, "w", encoding="utf-8").write("# yanlis=dogru\n")
            try: os.startfile(yol)
            except Exception as e: self._json({"hata": str(e)}); return
            self._json({"ok": True}); return

        if p == "/api/durum":
            self._json({"calisiyor": D.calisiyor, "adim": D.adim, "oran": D.oran, "kalan": D.kalan}); return

        if p == "/api/akis":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            q2 = D.abone()
            try:
                self.wfile.write(b": baglandi\n\n"); self.wfile.flush()
                while True:
                    try:
                        paket = q2.get(timeout=15)
                        self.wfile.write(("data: %s\n\n" % paket).encode("utf-8"))
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except Exception:
                pass
            finally:
                D.cik(q2)
            return

        self._gonder(404, "text/plain; charset=utf-8", "yok")

    def do_POST(self):
        u = urlparse(self.path); p = u.path; q = parse_qs(u.query)
        if p == "/api/calistir":
            if D.calisiyor:
                self._json({"hata": "Zaten bir adım çalışıyor."}); return
            no = int((q.get("adim") or ["1"])[0])
            klasor = (q.get("klasor") or [""])[0]
            hepsi = (q.get("hepsi") or ["0"])[0] == "1"
            if not os.path.isdir(klasor):
                self._json({"hata": "Klasör bulunamadı."}); return
            ayar_yaz({"klasor": klasor})
            sira = [2, 3, 4] if hepsi else None
            threading.Thread(target=adim_calistir, args=(no, klasor, sira), daemon=True).start()
            self._json({"ok": True}); return

        if p == "/api/kapat":
            self._json({"ok": True})
            threading.Timer(0.4, lambda: os._exit(0)).start(); return

        self._gonder(404, "text/plain; charset=utf-8", "yok")


def bos_port(bas=8765):
    for port in range(bas, bas + 40):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", port)); s.close(); return port
        except OSError:
            s.close()
    return bas


def main():
    port = bos_port()
    srv = ThreadingHTTPServer(("127.0.0.1", port), Sunucu)
    adres = "http://127.0.0.1:%d/" % port
    threading.Timer(0.6, lambda: webbrowser.open(adres)).start()
    print("Paye Games Dub Studio %s  —  %s" % (SURUM, adres))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
