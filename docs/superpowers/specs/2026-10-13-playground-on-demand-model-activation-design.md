# Playground On-Demand Model Download & Activation Design

## Overview
Ketika seorang pengguna berada di halaman detail model (`/{creator}/{model_name}`) dan model tersebut berstatus "Non Active" (belum dimuat ke memori / belum diunduh), pengguna tetap dapat mencoba playground. Saat pengguna menekan tombol "Run Inference" (atau shortcut `Ctrl+Enter`), sistem akan mencegat eksekusi inferensi dan menampilkan Modal Konfirmasi Aktivasi. Modal ini memberi tahu bahwa model belum aktif dan menyediakan tombol konfirmasi untuk mengunduh bobotnya (jika belum ada di disk lokal) dengan progress bar Server-Sent Events (SSE) real-time serta indikator pemuatan memori. Setelah model aktif, modal menutup dan inferensi yang tertunda langsung dijalankan otomatis.

---

## 1. Backend API: Public Model Activation & SSE Stream

### 1.1 Endpoint `POST /api/models/activate` (`app/api/models_route.py`)
- **Tujuan:** Mengizinkan aktivasi/unduhan on-demand model tertentu langsung dari halaman publik model playground tanpa memerlukan autentikasi session admin.
- **Payload:**
  ```json
  { "model": "d3-lite" }
  ```
- **Alur Kerja:**
  1. Melakukan normalisasi nama/alias model via `normalize_model_name(req.model)`.
  2. Memeriksa validitas model pada registry. Jika tidak dikenal -> return `400 Bad Request`.
  3. Memeriksa apakah model sudah aktif di `request.app.state.models`. Jika sudah aktif -> return `{"status": "already_active", "model": model_name}`.
  4. Memeriksa apakah ada proses setup lain yang sedang berjalan (`default_setup_manager._is_running`). Jika ya -> return `409 Conflict`.
  5. Menjalankan background task `default_setup_manager.start_setup(request.app.state, [model_name])`.
  6. Return `200 OK`: `{"status": "started", "model": model_name}`.

### 1.2 Endpoint `GET /api/models/stream` (`app/api/models_route.py`)
- **Tujuan:** Menyediakan stream Server-Sent Events (`text/event-stream`) publik untuk mendengarkan progress download & load model.
- **Response Headers:** `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`.
- **Payload Events:**
  - `phase: "downloading"`, `progress: <int>`, `message: "..."`
  - `phase: "loading"`, `progress: <int>`, `message: "..."`
  - `phase: "completed"`, `progress: 100`, `message: "All models loaded successfully!"`
  - `phase: "error"`, `progress: 0`, `message: "..."`

---

## 2. Frontend Playground Interception & Modal UI (`app/templates/model_detail.html`)

### 2.1 State Tracking
- Halaman memantau status keaktifan model saat ini melalui variable `isModelActive` (diinisialisasi dari Jinja context `is_active` dan diperbarui berkala via polling `/health`).

### 2.2 Modal Aktivasi (`#model-activate-modal`)
- Terdiri dari 3 fase visual:
  1. **Fase Konfirmasi:**
     - Judul: `⚡ MODEL NOT LOADED YET`
     - Deskripsi: `Model {{ model.display_name }} saat ini berstatus Non Active dan belum dimuat ke memori. Apakah Anda ingin mengunduh bobot dan memuat model ini sekarang?`
     - Tombol: `[ Batal ]` dan `[ Download & Aktifkan Model ]`.
  2. **Fase Progress (SSE):**
     - Membuka koneksi `new EventSource('/api/models/stream')`.
     - Progress bar animasi (0% - 100%).
     - Teks status dinamis (`Mengunduh bobot...` -> `Memuat ke memori...`).
     - Log mini terminal menampilkan pesan event.
  3. **Fase Sukses:**
     - Pesan sukses: `✅ Model berhasil dimuat dan siap melayani inferensi!`
     - Memperbarui badge model di header halaman menjadi `Active`.
     - Menutup modal aktivasi.
     - Melanjutkan pemanggilan `runInference()` yang tadi tertunda secara otomatis.

---

## 3. Testing & Verification

1. **API Integration Test (`tests/test_public_models_activate.py`):**
   - Menguji `POST /api/models/activate` dengan model valid mengembalikan 200 `started`.
   - Menguji `POST /api/models/activate` dengan model invalid mengembalikan 400.
   - Menguji `GET /api/models/stream` mengembalikan header `text/event-stream`.
2. **Playground UI Verification (`tests/test_model_routes.py`):**
   - Memastikan `#model-activate-modal` ter-render di template `model_detail.html`.
   - Memastikan tombol aktivasi dan logika `isModelActive` terintegrasi dengan handler `runInference`.
