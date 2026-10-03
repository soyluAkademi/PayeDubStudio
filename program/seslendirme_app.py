# -*- coding: utf-8 -*-
"""Seslendirme Stüdyosu — dört adımlık iş akışı arayüzü."""
import os, sys, time, threading, queue, glob, traceback
import tkinter as tk
from tkinter import filedialog

BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)
KOK = os.path.dirname(BURASI)
SURUM = "v1.1"

# ---- palet ----
BG       = "#0a0f18"
PANEL    = "#111a27"
KART     = "#141e2d"
CIZGI    = "#1e2b3d"
YAZI     = "#e8eef6"
SOLUK    = "#8ba0b8"
MAVI     = "#2f7ff0"
YESIL    = "#22c55e"
SARI     = "#eab308"
KIRMIZI  = "#ef4444"

ADIMLAR = [
    dict(no="1", renk="#2f7ff0", ikon="📝", modul="transkript_yap",
         baslik="Türkçe transkript",
         aciklama="Klasördeki mp4 → <video>.srt   (konuşmayı yazıya döker)",
         urun=lambda b: b + ".srt"),
    dict(no="2", renk="#8b5cf6", ikon="🌐", modul="ceviri_yap",
         baslik="Düzeltme + İngilizce metin",
         aciklama="Sözlük düzeltmeleri + çeviri → <video>_EN_metin.txt",
         urun=lambda b: b + "_EN_metin.txt"),
    dict(no="3", renk="#22c55e", ikon="📑", modul="altyazi_uret",
         baslik="Altyazılar",
         aciklama="→ <video>_EN.srt, <video>_TR.vtt, <video>_EN.vtt",
         urun=lambda b: b + "_EN.vtt"),
    dict(no="4", renk="#f97316", ikon="🎚", modul="senkron_yap",
         baslik="Sesi senkronla",
         aciklama="englishVoice.mp3 → <video>_EN_senkron.mp3 (video süresinde)",
         urun=lambda b: b + "_EN_senkron.mp3"),
]

YARDIM = """SESLENDİRME STÜDYOSU — NASIL ÇALIŞIR

Amaç: Türkçe çektiğin eğitim videosunu İngilizce seslendirmeyle,
videonun kendi zamanlamasına birebir oturmuş hale getirmek ve
Udemy'ye yüklenecek altyazıları üretmek.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HAZIRLIK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Her video için ayrı bir klasör aç, içine o videonun mp4'ünü koy.
Programı aç, üstten o klasörü seç. Program tek yerde durur; klasör
seçerek bütün videoları aynı programdan işlersin.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1 — TÜRKÇE TRANSKRİPT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Videonun sesini Türkçe altyazıya çevirir (Whisper "medium").
Çıktı: <video>.srt

• İlk çalıştırmada model bir kez iner (~1.5 GB), sonra hep hazır.
• 3-4 dakikalık video birkaç dakika sürer.
• .srt zaten varsa o videoyu atlar.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2 — DÜZELTME + İNGİLİZCE METİN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Önce sozluk.txt kurallarını uygular (Whisper'ın yanlış duyduğu
kelimeler), Türkçe .srt'yi temizler; sonra satır satır çevirir.
Çıktı: <video>_EN_metin.txt (zaman damgası yok, her satır bir cümle)

>>> BU DOSYAYI MUTLAKA OKU. Makine çevirisidir; ekran terimlerinde
    tuhaflık olabilir. Düzelt ama SATIR SAYISINI DEĞİŞTİRME —
    satır sayısı .srt'deki blok sayısıyla birebir olmalı.

sozluk.txt: "yanlis=dogru" satırları. Örn: webbullet=WebGL
Alt bardaki "Sözlüğü aç" düğmesiyle doğrudan açabilirsin.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3 — ALTYAZILAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
İngilizce metni Türkçe .srt'nin zamanlamalarıyla eşler.
Çıktılar: <video>_EN.srt , <video>_TR.vtt , <video>_EN.vtt
Udemy'ye yüklenecek olanlar iki .vtt dosyası.

"Satır sayısı uyuşmuyor" derse _EN_metin.txt'de satır eksilmiş
veya artmıştır; düzelt ve tekrar çalıştır.

>>> Bu adımdan sonra _EN_metin.txt'yi seslendir, dosyayı klasöre
    englishVoice.mp3 adıyla koy. Her satırı ayrı ayrı, aralarında
    kısa duraklarla okut — kesintisiz okunan ses hizalanamaz.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4 — SESİ SENKRONLA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
İngilizce sesi cümlelere böler, her cümleyi .srt'deki kendi anına
yerleştirir. Ses süresi = video süresi olur.
Çıktı: <video>_EN_senkron.mp3 (varsa üzerine yazmaz, _v2 kaydeder)

Yaptıkları:
• Cümle sınırlarını gerçek duraklamalara oturtur (kelime taşmaz)
• Sığmayan cümleyi hafifçe hızlandırır (en çok 1.3×); yine sığmazsa
  kesmez, sonraki cümleyi biraz öteler
• Cümle başı/sonuna yumuşatma, boşluklara duyulmayan ortam tonu

Ortam tonu rahatsız ederse program klasöründeki senkron_yap.py
içinde ORTAM_TONU değerini küçült ya da 0.0 yap.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAMTASIA'DA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Senkron sesin başını videonun 0:00'ına hizala
• Türkçe sesi kıs
• TIME SCALING YAPMA — ses zaten video zaman çizelgesine kurulu

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UDEMY'YE YÜKLERKEN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Video + <video>_EN.vtt + <video>_TR.vtt
Kurs İngilizce yayınlansa da Türkçe altyazı Türk öğrenciler için
işe yarar; ikisini de ekle.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SIK KARŞILAŞILANLAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"EKSIK PAKET: xxx"        → Komut istemine:  pip install xxx
Model indirme yavaş       → Bir kereliktir
Ses gürültülü             → ORTAM_TONU değerini düşür
Altyazı ile ses uyuşmuyor → 2. adımda satır sayısı bozulmuş olabilir
"""


class Yazici:
    def __init__(self, q): self.q = q
    def write(self, s):
        if s: self.q.put(s)
    def flush(self): pass


class App:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.calisiyor = False
        self.basla_t = 0.0
        self.oran = 0.0
        root.title("Seslendirme Stüdyosu")
        root.geometry("1040x780"); root.minsize(900, 660)
        root.configure(bg=BG)

        self._baslik()
        self._klasor()
        self._kartlar()
        self._altbar()
        self._ilerleme()
        self._gunluk()
        self._altbilgi()

        self.durum_tara()
        self.root.after(80, self.kuyruk)

    # ---------------- ust baslik ----------------
    def _baslik(self):
        c = tk.Frame(self.root, bg=BG, padx=20, pady=16); c.pack(fill="x")
        sol = tk.Frame(c, bg=BG); sol.pack(side="left")
        logo = tk.Canvas(sol, width=54, height=54, bg=BG, highlightthickness=0)
        logo.pack(side="left", padx=(0, 14))
        logo.create_oval(6, 6, 48, 48, outline=MAVI, width=2)
        logo.create_rectangle(21, 14, 33, 32, fill=MAVI, outline="")
        logo.create_arc(15, 20, 39, 40, start=200, extent=140, style="arc", outline=MAVI, width=2)
        logo.create_line(27, 40, 27, 46, fill=MAVI, width=2)
        yazi = tk.Frame(sol, bg=BG); yazi.pack(side="left")
        tk.Label(yazi, text="Seslendirme Stüdyosu", bg=BG, fg=YAZI,
                 font=("Segoe UI", 19, "bold")).pack(anchor="w")
        tk.Label(yazi, text="Videolarını çok dilli seslendirmelerle buluştur", bg=BG, fg=SOLUK,
                 font=("Segoe UI", 9)).pack(anchor="w")
        y = tk.Frame(c, bg=PANEL, cursor="hand2"); y.pack(side="right")
        tk.Label(y, text="?", bg=MAVI, fg="white", font=("Segoe UI", 12, "bold"),
                 width=3, height=2).pack(side="left")
        iy = tk.Frame(y, bg=PANEL); iy.pack(side="left", padx=12, pady=8)
        tk.Label(iy, text="Yardım", bg=PANEL, fg=YAZI, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(iy, text="Kullanım kılavuzunu görüntüle", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).pack(anchor="w")
        for w in (y, iy) + tuple(iy.winfo_children()):
            w.bind("<Button-1>", lambda e: self.yardim())

    # ---------------- klasor ----------------
    def _klasor(self):
        p = tk.Frame(self.root, bg=PANEL, padx=16, pady=14)
        p.pack(fill="x", padx=20, pady=(0, 10))
        tk.Label(p, text="📁", bg=PANEL, fg=SARI, font=("Segoe UI", 16)).pack(side="left", padx=(0, 10))
        s = tk.Frame(p, bg=PANEL); s.pack(side="left")
        tk.Label(s, text="Video klasörü", bg=PANEL, fg=YAZI,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(s, text="İşlenecek video dosyalarının bulunduğu klasörü seç.", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).pack(anchor="w")
        self.klasor = tk.StringVar(value=KOK)
        tk.Button(p, text="  Klasörü aç  ", command=self.klasoru_ac, bg=MAVI, fg="white",
                  relief="flat", font=("Segoe UI", 9, "bold"), cursor="hand2",
                  activebackground=MAVI, activeforeground="white").pack(side="right", ipady=6)
        tk.Button(p, text="  Seç...  ", command=self.klasor_sec, bg=CIZGI, fg=YAZI,
                  relief="flat", font=("Segoe UI", 9), cursor="hand2",
                  activebackground=CIZGI, activeforeground=YAZI).pack(side="right", padx=8, ipady=6)
        tk.Entry(p, textvariable=self.klasor, bg=KART, fg=YAZI, relief="flat",
                 insertbackground=YAZI, font=("Segoe UI", 9)).pack(
                 side="right", fill="x", expand=True, padx=14, ipady=6)

    # ---------------- adim kartlari ----------------
    def _kartlar(self):
        self.durum_et = []; self.durum_alt = []; self.butonlar = []
        c = tk.Frame(self.root, bg=BG); c.pack(fill="x", padx=20)
        for a in ADIMLAR:
            k = tk.Frame(c, bg=KART); k.pack(fill="x", pady=4)
            tk.Frame(k, bg=a["renk"], width=4).pack(side="left", fill="y")
            tk.Label(k, text=a["no"], bg=a["renk"], fg="white",
                     font=("Segoe UI", 16, "bold"), width=3).pack(side="left", fill="y", padx=(10, 0), pady=10)
            tk.Label(k, text=a["ikon"], bg=KART, fg=a["renk"],
                     font=("Segoe UI", 16)).pack(side="left", padx=14)
            m = tk.Frame(k, bg=KART); m.pack(side="left", fill="both", expand=True, pady=12)
            tk.Label(m, text=a["baslik"], bg=KART, fg=YAZI,
                     font=("Segoe UI", 12, "bold")).pack(anchor="w")
            tk.Label(m, text=a["aciklama"], bg=KART, fg=SOLUK,
                     font=("Segoe UI", 9)).pack(anchor="w")
            sag = tk.Frame(k, bg=KART); sag.pack(side="right", padx=14)
            d = tk.Frame(sag, bg=KART); d.pack(side="right", padx=(14, 0))
            et = tk.Label(d, text="bekliyor", bg=KART, fg=SOLUK, font=("Segoe UI", 10, "bold"), anchor="w", width=12)
            et.pack(anchor="w")
            alt = tk.Label(d, text="Henüz çalıştırılmadı", bg=KART, fg="#5c728c",
                           font=("Segoe UI", 8), anchor="w", width=18)
            alt.pack(anchor="w")
            b = tk.Button(sag, text="▶  Çalıştır", bg=a["renk"], fg="white", relief="flat",
                          font=("Segoe UI", 10, "bold"), width=12, cursor="hand2",
                          activebackground=a["renk"], activeforeground="white",
                          command=lambda x=a: self.calistir(x))
            b.pack(side="right", ipady=6)
            self.durum_et.append(et); self.durum_alt.append(alt); self.butonlar.append(b)

    # ---------------- alt bar ----------------
    def _altbar(self):
        c = tk.Frame(self.root, bg=BG, padx=20, pady=10); c.pack(fill="x")
        self.hepsi_btn = tk.Button(c, text="▶  Hepsini sırayla çalıştır", command=self.hepsi,
                                   bg="#7c3aed", fg="white", relief="flat", cursor="hand2",
                                   font=("Segoe UI", 10, "bold"), activebackground="#7c3aed",
                                   activeforeground="white")
        self.hepsi_btn.pack(side="left", ipadx=10, ipady=7)
        for metin, komut in (("⟳  Durumu yenile", self.durum_tara),
                             ("📖  Sözlüğü aç", self.sozluk_ac),
                             ("🧹  Günlüğü temizle", lambda: self.log.delete("1.0", "end"))):
            tk.Button(c, text=metin, command=komut, bg=KART, fg=YAZI, relief="flat",
                      cursor="hand2", font=("Segoe UI", 9), activebackground=CIZGI,
                      activeforeground=YAZI).pack(side="left", padx=(8, 0), ipadx=8, ipady=7)
        self.durum = tk.Label(c, text="Hazır", bg=BG, fg=YESIL, font=("Segoe UI", 10, "bold"))
        self.durum.pack(side="right")

    # ---------------- ilerleme ----------------
    def _ilerleme(self):
        p = tk.Frame(self.root, bg=PANEL, padx=16, pady=12); p.pack(fill="x", padx=20)
        tk.Label(p, text="Genel ilerleme", bg=PANEL, fg=YAZI,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        self.sure_et = tk.Label(p, text="", bg=KART, fg=SOLUK, font=("Segoe UI", 9), padx=12, pady=5)
        self.sure_et.pack(side="right")
        self.yuzde_et = tk.Label(p, text="%0", bg=PANEL, fg=YESIL, font=("Segoe UI", 12, "bold"), width=6)
        self.yuzde_et.pack(side="right", padx=12)
        self.cubuk = tk.Canvas(p, height=14, bg=KART, highlightthickness=0)
        self.cubuk.pack(side="left", fill="x", expand=True, padx=16)
        self.cubuk.bind("<Configure>", lambda e: self.cubuk_ciz())
        self.cubuk_ciz()

    def cubuk_ciz(self):
        self.cubuk.delete("all")
        w = max(self.cubuk.winfo_width(), 1); h = 14
        self.cubuk.create_rectangle(0, 0, w, h, fill=KART, outline="")
        if self.oran > 0:
            self.cubuk.create_rectangle(0, 0, int(w * min(self.oran, 1.0)), h, fill=YESIL, outline="")

    def oran_ayarla(self, o):
        self.oran = max(0.0, min(1.0, o))
        self.cubuk_ciz()
        self.yuzde_et.config(text="%%%d" % int(self.oran * 100))
        if self.calisiyor and self.oran > 0.02:
            gecen = time.time() - self.basla_t
            kalan = gecen * (1 - self.oran) / self.oran
            self.sure_et.config(text="Tahmini kalan süre   ~ %s" % self.sure_metni(kalan))
        elif not self.calisiyor:
            self.sure_et.config(text="")

    @staticmethod
    def sure_metni(sn):
        sn = int(sn)
        if sn < 60: return "%d saniye" % max(sn, 1)
        return "%d dakika" % max(sn // 60, 1)

    # ---------------- gunluk ----------------
    def _gunluk(self):
        p = tk.Frame(self.root, bg=PANEL, padx=2, pady=2); p.pack(fill="both", expand=True, padx=20, pady=10)
        ust = tk.Frame(p, bg=PANEL, padx=14, pady=10); ust.pack(fill="x")
        tk.Label(ust, text=">_", bg=KART, fg=YESIL, font=("Consolas", 11, "bold"),
                 padx=8, pady=3).pack(side="left")
        tk.Label(ust, text="İşlem günlüğü", bg=PANEL, fg=YAZI,
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
        self.canli = tk.Label(ust, text="", bg=PANEL, fg=YESIL, font=("Segoe UI", 9))
        self.canli.pack(side="left")
        self.log = tk.Text(p, bg="#070b12", fg="#b9c8da", insertbackground=YAZI,
                           font=("Consolas", 9), wrap="word", relief="flat", padx=12, pady=10)
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log.tag_config("bilgi", foreground="#6ea8fe")
        self.log.tag_config("ok", foreground=YESIL)
        self.log.tag_config("uyari", foreground=SARI)
        self.log.tag_config("hata", foreground=KIRMIZI)
        self.log.tag_config("baslik", foreground="#c9a5ff")
        self.yaz("Klasörü seç, sonra 1'den 4'e sırayla tıkla. Takılırsan sağ üstteki Yardım.\n", "bilgi")

    def _altbilgi(self):
        c = tk.Frame(self.root, bg=BG, padx=20, pady=6); c.pack(fill="x", pady=(0, 8))
        tk.Label(c, text="Seslendirme Stüdyosu   %s" % SURUM, bg=BG, fg="#4f6379",
                 font=("Segoe UI", 8)).pack(side="left")
        tk.Label(c, text="Paye Games", bg=BG, fg="#4f6379", font=("Segoe UI", 8)).pack(side="right")

    # ---------------- yardimcilar ----------------
    def yaz(self, s, tag=None):
        self.log.insert("end", s, tag or ())
        self.log.see("end")

    def klasor_sec(self):
        d = filedialog.askdirectory(initialdir=self.klasor.get() or KOK)
        if d:
            self.klasor.set(os.path.normpath(d)); self.durum_tara()

    def klasoru_ac(self):
        try: os.startfile(self.klasor.get())
        except Exception as e: self.yaz("Klasör açılamadı: %s\n" % e, "hata")

    def sozluk_ac(self):
        yol = os.path.join(BURASI, "sozluk.txt")
        if not os.path.isfile(yol):
            try:
                open(yol, "w", encoding="utf-8").write(
                    "# Whisper'in yanlis duydugu kelimeler: yanlis=dogru\n")
            except Exception as e:
                self.yaz("Sözlük açılamadı: %s\n" % e, "hata"); return
        try: os.startfile(yol)
        except Exception as e: self.yaz("Sözlük açılamadı: %s\n" % e, "hata")

    def durum_tara(self):
        kl = self.klasor.get()
        videolar = sorted(glob.glob(os.path.join(kl, "*.mp4"))) if os.path.isdir(kl) else []
        base = os.path.splitext(videolar[0])[0] if videolar else None
        for a, et, alt in zip(ADIMLAR, self.durum_et, self.durum_alt):
            if not base:
                et.config(text="—", fg=SOLUK); alt.config(text="Klasörde mp4 yok"); continue
            u = a["urun"](base)
            if os.path.isfile(u):
                et.config(text="✔ hazır", fg=YESIL)
                alt.config(text=os.path.basename(u)[:26])
            else:
                et.config(text="bekliyor", fg=SOLUK)
                alt.config(text="Henüz çalıştırılmadı")

    def kilit(self, acik):
        self.calisiyor = acik
        st = "disabled" if acik else "normal"
        for b in self.butonlar: b.config(state=st)
        self.hepsi_btn.config(state=st)
        self.canli.config(text="Çalışma devam ediyor..." if acik else "")

    def kuyruk(self):
        try:
            while True:
                s = self.q.get_nowait()
                for satir in s.splitlines(True):
                    t = satir.strip()
                    if t.startswith("##P "):
                        try: self.oran_ayarla(float(t[4:]))
                        except ValueError: pass
                        continue
                    if not satir: continue
                    tag = None
                    if "===" in satir: tag = "baslik"
                    elif "[OK]" in satir or "Bitti" in satir: tag = "ok"
                    elif "HATA" in satir or "EKSIK" in satir: tag = "hata"
                    elif "UYARI" in satir or "ATLANDI" in satir: tag = "uyari"
                    self.yaz(satir, tag)
        except queue.Empty:
            pass
        self.root.after(80, self.kuyruk)

    # ---------------- calistirma ----------------
    def calistir(self, adim, sonra=None):
        if self.calisiyor: return
        kl = self.klasor.get()
        if not os.path.isdir(kl):
            self.yaz("HATA: Klasör bulunamadı.\n", "hata"); return
        self.kilit(True)
        self.basla_t = time.time()
        self.oran_ayarla(0.0)
        self.durum.config(text="%s. adım çalışıyor..." % adim["no"], fg=SARI)
        i = ADIMLAR.index(adim)
        self.durum_et[i].config(text="çalışıyor", fg=SARI)
        self.durum_alt[i].config(text="Devam ediyor...")
        threading.Thread(target=self._is, args=(adim, kl, sonra), daemon=True).start()

    def _is(self, adim, kl, sonra):
        eski = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = Yazici(self.q)
        ok = False
        try:
            self.q.put("\n===  %s. adım — %s  ===\n" % (adim["no"], adim["baslik"]))
            __import__(adim["modul"]).main(kl)
            ok = True
        except ModuleNotFoundError as e:
            self.q.put("\nEKSIK PAKET: %s\nKomut istemine yaz:  pip install %s\n" % (e.name, e.name))
        except Exception:
            self.q.put("\nHATA:\n" + traceback.format_exc())
        finally:
            sys.stdout, sys.stderr = eski
            self.root.after(0, lambda: self.bitti(ok, sonra))

    def bitti(self, ok, sonra):
        self.kilit(False)
        self.oran_ayarla(1.0 if ok else self.oran)
        self.durum.config(text="Bitti" if ok else "Hata", fg=YESIL if ok else KIRMIZI)
        self.durum_tara()
        if ok and sonra:
            adim, kalan = sonra
            self.root.after(400, lambda: self.calistir(adim, kalan))

    def hepsi(self):
        zincir = None
        for a in reversed(ADIMLAR): zincir = (a, zincir)
        adim, kalan = zincir
        self.calistir(adim, kalan)

    # ---------------- yardim penceresi ----------------
    def yardim(self):
        p = tk.Toplevel(self.root)
        p.title("Yardım — Seslendirme Stüdyosu")
        p.geometry("820x700"); p.configure(bg=BG)
        bas = tk.Frame(p, bg=BG, padx=18, pady=14); bas.pack(fill="x")
        tk.Label(bas, text="Kullanım kılavuzu", bg=BG, fg=YAZI,
                 font=("Segoe UI", 15, "bold")).pack(side="left")
        tk.Button(bas, text="Kapat", command=p.destroy, bg=KART, fg=YAZI, relief="flat",
                  font=("Segoe UI", 9), cursor="hand2").pack(side="right", ipadx=14, ipady=5)
        c = tk.Frame(p, bg=BG, padx=18); c.pack(fill="both", expand=True, pady=(0, 16))
        sb = tk.Scrollbar(c); sb.pack(side="right", fill="y")
        t = tk.Text(c, bg="#070b12", fg=YAZI, wrap="word", relief="flat",
                    font=("Consolas", 10), padx=14, pady=12, yscrollcommand=sb.set)
        t.pack(fill="both", expand=True); sb.config(command=t.yview)
        t.insert("1.0", YARDIM)
        t.config(state="disabled")


def main():
    root = tk.Tk()  # noqa
    try: root.call("tk", "scaling", 1.2)
    except Exception: pass
    App(root)
    root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        iz = traceback.format_exc()
        try:
            yol = os.path.join(BURASI, "hata_log.txt")
            with open(yol, "a", encoding="utf-8") as f:
                f.write("\n===== %s =====\n%s" % (time.strftime("%Y-%m-%d %H:%M:%S"), iz))
        except Exception:
            yol = "(hata_log.txt yazilamadi)"
        try:
            import tkinter.messagebox as mb
            mb.showerror("Seslendirme Studyosu - hata", iz[-1500:] + "\n\nAyrinti: " + yol)
        except Exception:
            print(iz)
        raise
