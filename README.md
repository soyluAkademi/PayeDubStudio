# Paye Games Dub Studio

Türkçe çekilmiş eğitim videolarını İngilizce seslendirmeyle buluşturan, uçtan uca çalışan bir masaüstü aracı.
Videodan Türkçe altyazı çıkarır, metni İngilizceye çevirir, Udemy'ye yüklenecek altyazıları üretir ve
İngilizce seslendirmeyi videonun kendi zaman çizelgesine birebir oturtur.

Her şey bilgisayarında çalışır. Dosyalar hiçbir sunucuya gitmez; internet yalnızca ilk çalıştırmada
modeller indirilirken gerekir.

---

## Hangi problemi çözüyor?

Türkçe bir eğitim videosunu İngilizce seslendirdiğinde ortaya şu sorun çıkar: seslendirme kesintisiz
okunduğu için videodan **kısa** kalır. Videoda fare hareketleri, menü açılışları, kurulum beklemeleri
gibi sessiz anlar vardır; okunan metinde bunlar yoktur. 200 saniyelik videoya 170 saniyelik ses düşer,
görüntüyle ses birbirinden kopar.

Sesi yavaşlatmak (time stretching) işe yaramaz — konuşma bozulur ve uyum yine tutmaz.

Bu araç farklı bir yol izler: **sesi cümlelere böler ve her cümleyi altyazıdaki kendi anına yerleştirir.**
Aradaki boşluklar sessizlikle doldurulur. Sonuçta ses süresi = video süresi olur ve her cümle, videoda
karşılığı olan görüntünün üzerine denk gelir.

---

## Nasıl çalışır

```
video.mp4
   │
   ├─[1]─> video.srt              Türkçe altyazı          (faster-whisper)
   │
   ├─[2]─> video_EN_metin.txt     İngilizce düz metin     (sözlük düzeltmeleri + Argos Translate)
   │           │
   │           └── seslendirilir ──> englishVoice.mp3
   │
   ├─[3]─> video_EN.srt           İngilizce altyazı       (TR zamanlamaları + EN satırlar)
   │       video_TR.vtt           Udemy altyazısı
   │       video_EN.vtt           Udemy altyazısı
   │
   └─[4]─> video_EN_senkron.mp3   Video süresine oturtulmuş İngilizce ses
```

### 4. adımın ayrıntısı (işin can alıcı kısmı)

1. **Hizalama** — İngilizce sesteki her kelimenin zamanı çıkarılır (faster-whisper, word timestamps),
   kelimeler altyazı cümlelerine sırayla dağıtılır. Böylece her cümlenin ses içindeki başlangıç/bitişi bulunur.
2. **Duraklamaya oturtma** — Cümle sınırları, sesteki gerçek sessizliklere kaydırılır (RMS tabanlı sessizlik
   tespiti). Klip bir sessizliğin başında biter, sonraki klip o sessizliğin bitişinde başlar.
   *Bu adım atlanırsa sonraki cümlenin ilk kelimesi taşıp tekrarlanır.*
3. **Yerleştirme** — Her klip, SRT'deki kendi başlangıç anına konur. Klip slotuna sığmıyorsa perde bozmayan
   WSOLA ile en çok 1.3× hızlandırılır; hâlâ sığmıyorsa **kesilmez**, sonraki cümle biraz ötelenir.
   Biriken kayma ilk boşlukta kapanır.
4. **Yumuşatma** — Her klibe 40 ms fade-in / 120 ms fade-out, boşluklara ise duyulmayan seviyede
   (~-60 dBFS) pembe gürültü ortam tonu eklenir. Ölü dijital sessizlik hissi kalkar.
5. **Çıktı** — Kaynağın örnekleme hızı ve kanal sayısı korunur, 192 kbps mp3 yazılır, süre video süresinde kesilir.

---

## Kurulum

**Gerekenler:** Windows, Python 3.9+ (PATH'e ekli).

```bash
pip install faster-whisper argostranslate numpy av
```

Depoyu indir, klasörü istediğin yere koy, `PayeDubStudio.vbs` dosyasına çift tıkla.
Yerel sunucu başlar ve tarayıcıda arayüz açılır (`http://127.0.0.1:8765`).

İlk çalıştırmada modeller bir kez iner: Whisper "medium" (~1.5 GB) ve Argos tr→en (~100 MB).
Kullanıcı profiline kurulurlar; sonraki videolarda tekrar inmez, internet gerekmez.

Sorun çıkarsa `program\Tanila.bat` — Python, paketler ve sunucu durumunu konsolda gösterir.

---

## Kullanım

1. Her video için ayrı bir klasör aç, `.mp4` dosyasını içine koy.
2. Programı aç, üstten o klasörü seç.
3. **1. adım** → Türkçe `.srt` oluşur.
4. **2. adım** → `_EN_metin.txt` oluşur. **Bu dosyayı oku ve gerekirse düzelt** — makine çevirisidir.
   *Satır sayısını değiştirme;* satır sayısı `.srt` blok sayısıyla birebir olmak zorunda.
5. **3. adım** → `_EN.srt`, `_TR.vtt`, `_EN.vtt` oluşur.
6. Metni seslendir (ben SorceressGames kullanıyorum), dosyayı klasöre **`englishVoice.mp3`** adıyla koy.
   Her satırı ayrı ayrı, aralarında kısa duraklarla okut — kesintisiz okunan ses hizalanamaz.
7. **4. adım** → `_EN_senkron.mp3` oluşur.
8. Camtasia'da senkron sesi videonun `0:00`'ına hizala, Türkçe sesi kıs. **Time scaling yapma** —
   ses zaten video zaman çizelgesine kurulu.

Udemy'ye yüklenecekler: video + `_EN.vtt` + `_TR.vtt`.

### sozluk.txt

Whisper teknik terimleri sık yanlış duyar. `program\sozluk.txt` içine `yanlis=dogru` satırları yazarsın,
2. adım çeviriden önce bunları uygular:

```
unitihab=Unity Hub
webbullet=WebGL
cloud=Claude
sportut=Supported
```

Yeni bir hata yakaladığında ekle; bir daha elle düzeltmezsin. Arayüzdeki "Sözlüğü aç" düğmesi doğrudan açar.

---

## Dosya yapısı

```
PayeDubStudio.vbs          başlatıcı (konsol açmadan sunucuyu çalıştırır)
program/
  sunucu.py                yerel HTTP sunucusu, adımları çalıştırır, SSE ile canlı günlük
  arayuz.html              arayüz (tek dosya, bağımlılık yok)
  transkript_yap.py        1. adım — faster-whisper ile Türkçe transkript
  ceviri_yap.py            2. adım — sözlük düzeltmeleri + Argos Translate
  altyazi_uret.py          3. adım — EN .srt ve .vtt üretimi
  senkron_yap.py           4. adım — hizalama, snap, yerleştirme, WSOLA, mixdown
  sozluk.txt               düzeltme kuralları
  Tanila.bat               tanılama
  OKU.txt                  kısa kullanım notu
  eski_arayuz/
    seslendirme_app.py     önceki tkinter arayüzü (yedek)
```

İş mantığı dört modülde; arayüz yalnızca kabuk. Modülleri komut satırından da çalıştırabilirsin:

```bash
python program/senkron_yap.py "C:\videolar\ders01"
```

---

## Ayarlar

| Ne | Nerede |
|---|---|
| Ortam tonu seviyesi (gürültü duyarsan düşür ya da `0.0` yap) | `senkron_yap.py` → `ORTAM_TONU` |
| En fazla hızlandırma oranı | `senkron_yap.py` → `TARGET_TEMPO_MAX` |
| Whisper model boyutu (`small` / `medium` / `large-v3`) | `transkript_yap.py` → `MODEL` |
| Son kullanılan klasör | `program/ayarlar.json` (otomatik) |

---

## Bilinen sınırlar

- Yalnızca Windows'ta denendi. Modüller platform bağımsız; `os.startfile` ve `.vbs` başlatıcı Windows'a özgü.
- Çeviri makine çevirisidir. Ekran terimlerinde ("Install Editor", "Build Settings") tuhaflık yapabilir —
  2. adımın çıktısı yayına gitmeden okunmalı.
- Seslendirme cümle cümle, aralarda duraklarla okunmalı. Tek nefeste okunan kayıtta hizalama zorlanır.
- Transkripsiyon CPU'da çalışır; 3-4 dakikalık video birkaç dakika sürer.

---

## English summary

**Paye Games Dub Studio** turns Turkish screencast tutorials into English-dubbed videos whose audio lines
up with the original footage. It transcribes the Turkish audio, translates it, generates subtitle files for
Udemy, and — the core trick — re-times your English voice-over so each sentence lands at its own moment in
the video instead of running short.

It splits the voice-over into sentences using forced alignment, snaps every boundary to a real pause,
places each clip at its subtitle's start time, gently time-stretches (pitch-preserving WSOLA, ≤1.3×) only
what doesn't fit, and fills the gaps with inaudible room tone. Output duration equals video duration.

Everything runs locally: a small Python HTTP server plus a single-page UI in your browser.
No data leaves your machine; the internet is only used once, to download the models.

---

## Lisans

MIT

## Teşekkür

Araç [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [Argos Translate](https://github.com/argosopentech/argos-translate),
[PyAV](https://github.com/PyAV-Org/PyAV) ve NumPy üzerine kuruludur.

Paye Games tarafından, Udemy Unity eğitim serisinin İngilizce sürümünü üretmek için yazıldı.
