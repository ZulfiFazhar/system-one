# Specification: TypeSafe AI-Styled Landing Page & Developer Playground

## 1. Overview
Web landing page responsif di endpoint `GET /` dengan estetika brutalist-editorial khas TypeSafe AI (`https://typesafe.ai/` dan `DESIGN.md`). Halaman ini berfungsi ganda sebagai pengenal nilai produk System 1 Laya (non-autoregressive decision inference) sekaligus developer hub interaktif (Live Tester console) untuk mengeksekusi inferensi terhadap `POST /v1/systemone` langsung dari peramban.

## 2. Visual Architecture & Design Tokens
Sistem desain mematuhi aturan ketat **Anti-Slop (Mode DURING)** dan token pada `DESIGN.md`:
- **Dials Liveliness**: `ENERGY 2 / RHYTHM 2 / MOTION 1`.
- **Palette**:
  - Background: `#fefefe` (kertas terang bersih, bukan dark mode generik).
  - Teks & Border: `#1E1E1E` (kontras rasio 14:1+, lolos WCAG AA).
  - Secondary Text: `#555555` (kontras 5.2:1+, lolos WCAG AA).
  - Card & Container Border: `1px solid #1E1E1E`.
  - Aksent: Hijau `#03aa5c` (status ready badge), Pink `#f386a1` (accent pill), Soft Gray `#dedede` (divider).
  - Bayangan (Hard Shadow): `2px 2px 0px rgba(0,0,0,0.4)` pada tombol, input field, dan kartu. Dilarang menggunakan soft diffuse blur atau ambient glow.
- **Tipografi**:
  - Font: `Inter` untuk body/heading, `JetBrains Mono` untuk kode, metrik, angka, dan JSON.
  - Tracking: `-0.02em` pada judul, tight hierarchy.
- **Anti-Slop Constraints**:
  - Dilarang memakai karakter em dash (—) pada seluruh teks antarmuka.
  - Dilarang memakai AI marketing buzzwords ("revolutionary", "seamless", "next generation", "cutting edge").
  - Dilarang menggunakan testimonial atau metrik palsu. Data teknis didasarkan pada spesifikasi model aktual (322M parameter mmBERT-base, ~33ms batch latency, 100+ bahasa).

## 3. Page Structure & Components

### 3.1 Header / Navigation
- Brand mark: `System One` teks dengan badge status model di sampingnya.
- Status Badge: Polling awal ke `GET /healthz`. Jika `status: "ready"`, indikator hijau ("Model Ready: laya-multilingual"). Jika gagal, indikator merah ("Model Offline").
- Navigasi: Tautan ke Swagger API (`/docs`), Health check (`/healthz`), dan tombol scroll ke Playground.

### 3.2 Hero & Research Thesis
- H1 Headline: "We took the opposite research direction."
- Editorial Narrative: Mengapa System 1 bukan LLM generatif: non-autoregressive decision model menghasilkan probabilitas terkalibrasi dan keputusan terstruktur langsung dalam satu forward pass tanpa token decoding, tanpa delay autoregresi, dan tanpa halusinasi.
- Core Metrics Grid:
  - `~33ms`: Single-pass inference latency.
  - `322M`: mmBERT-base backbone parameters.
  - `100+`: Bahasa didukung secara native.
  - `0`: Generative hallucinations or parsing errors.

### 3.3 Interactive Live Tester (Playground)
Area kerja interaktif bagi developer untuk menguji endpoint inferensi `POST /v1/systemone`:
1. **Preset Selectors**: Tombol cepat untuk mengisi contoh kasus nyata:
   - *Customer Support*: Deteksi komplain penagihan ganda dan permintaan refund.
   - *Security Triage*: Klasifikasi konten berbahaya atau pelanggaran TOS.
   - *Incident Urgency*: Evaluasi keparahan gangguan teknis produksi.
2. **State Input**: Textarea multiline untuk memasukkan teks/state yang akan dievaluasi.
3. **Question Configurator**:
   - Pilihan pertanyaan `noul` (probabilitas biner Ya/Tidak).
   - Pilihan pertanyaan `choice` (pemilihan kategori diskrit).
   - Pilihan pertanyaan `score` (skala ordinal bertingkat).
4. **Auth Bar**: Input opsional Bearer API Key (otomatis terisi dari `sessionStorage` jika sebelumnya pernah dimasukkan).
5. **Action Bar**: Tombol "Run Evaluation" dengan efek hard shadow dan hover offset.
6. **Result View**:
   - Status badge HTTP dan roundtrip latency (ms).
   - Visualisasi probabilitas calibrated (bar progress proporsional).
   - Token usage indicator (input tokens dan output tokens).
   - Tab switch: Tampilan Visual vs Raw JSON output.

### 3.4 Model Card & Author Attribution (Convai Innovations)
Bagian khusus untuk mengatribusikan karya dan menampilkan informasi teknis model Laya:
- **Author Attribution**: Dikembangkan oleh **Convai Innovations** (`convaiinnovations`) dan Nandha Kishor.
- **Model Card Highlights (`convaiinnovations/laya-multilingual`)**:
  - Backbone: mmBERT-base (bidirectional, 22 layer, hidden 768, 256k vocabulary) + decision head 2 layer terlatih khusus dari scratch.
  - Parameter: 322 Juta (322M).
  - Context Window: 1024 token per pertanyaan (256 dialokasikan untuk pertanyaan dan opsi).
  - Training Method: RLCD (Reinforcement Learning from Calibrated Decisions), 15.987 update, 4 epoch.
  - Coverage: 100+ bahasa (evaluasi pada 51 bahasa MASSIVE, peningkatan akurasi signifikan pada non-Latin scripts dibanding model bahasa Inggris).
  - Kecepatan: ~32.8 ms untuk forward pass tunggal, hingga 332 pertanyaan/detik secara ter-batch pada T4 GPU.
- **Tautan Eksternal**:
  - Hugging Face Model Card: `https://huggingface.co/convaiinnovations/laya-multilingual`
  - Laya Family Collection: `https://huggingface.co/convaiinnovations/laya`
  - Lisensi Asli: Apache 2.0.

### 3.5 Technical Architecture & FAQ
- Pertanyaan teknis konkret:
  - *Bagaimana System 1 bekerja tanpa autoregressive decoding?*
  - *Bagaimana probabilitas dikalibrasi?*
  - *Bagaimana cara integrasi ke backend yang ada?*
- Contoh curl request yang dapat disalin dengan tombol "Copy Curl".

### 3.6 Footer
- Versi service, status penyimpanan lokal (`models/laya-multilingual`), atribusi Convai Innovations, dan lisensi Apache 2.0.

## 4. Technical Implementation & Delivery Plan
- **Backend**:
  - Tambahkan file `app/api/home_route.py` dengan endpoint `GET /` mengembalikan `HTMLResponse`.
  - Daftarkan `home_route` ke `app/api/__init__.py`.
- **Frontend Stack**:
  - Single-file template di `app/templates/index.html` (atau disajikan langsung via `HTMLResponse`).
  - Tailwind CSS via Play CDN dengan konfigurasi kustom token TypeSafe di `<script>`.
  - Vanilla JS tanpa external framework untuk manipulasi DOM, AJAX fetch ke `/healthz` dan `/v1/systemone`, serta visualisasi state.
- **Resilience & Accessibility**:
  - Loading spinner saat inferensi berjalan.
  - Penanganan error 401 (API key tidak valid) dan 503 (model belum siap) dengan notifikasi jelas.
  - Mobile responsive: breakpoint grid `grid-cols-1 md:grid-cols-2`, target sentuh >= 44px, zero horizontal overflow.
  - Navigasi keyboard penuh (`tabindex`, `focus-visible` ring kontras).

## 5. Testing & Verification
- Unit test di `tests/test_api.py` memverifikasi `GET /` mengembalikan HTTP status 200 dengan header `Content-Type: text/html`.
- Verifikasi interaksi API playground bekerja langsung terhadap endpoint `POST /v1/systemone`.
- Seluruh 15 test yang ada tetap lulus tanpa regresi.
