# Specification: Laya API Compatible with TypeSafe Jev

## 1. Overview
API service berbasis FastAPI untuk model non-autoregressive decision **Laya** (`convaiinnovations/laya`), menyediakan endpoint yang kompatibel langsung dengan spesifikasi API **TypeSafe Jev** (`POST /v1/systemone`). Service menerima `state` dan map `questions` (`noul`, `choice`, `score`), mengeksekusi inferensi melalui `laya.Router`, dan mengembalikan jawaban terstruktur beserta probabilitas dan keyakinan kalibrasi.

## 2. Architecture & Runtime Lifespan
- **Framework**: FastAPI + Uvicorn.
- **Model Engine**: `laya.Router(preload=True, device=device)`.
  - Inisialisasi saat aplikasi startup via FastAPI `lifespan context manager`.
  - Checkpoint disimpan di memori (`app.state.router`) agar inferensi per request instan (~30-40 ms) tanpa reload.
  - Saat shutdown, VRAM/RAM dibersihkan via `router.unload()`.
- **Concurrency**: Eksekusi inferensi model dilakukan secara synchronous thread-safe atau via `run_in_threadpool` agar tidak memblok event loop asyncio FastAPI.

## 3. Endpoints

### 3.1 `GET /healthz`
Pemeriksaan status server dan kesiapan model.
- **Response**: `200 OK`
```json
{
  "status": "ready",
  "model": "laya",
  "preloaded": true
}
```

### 3.2 `POST /v1/systemone`
Endpoint utama evaluasi keputusan System 1, identik dengan TypeSafe API.

#### Headers
- `Authorization`: `Bearer <API_KEY>` (jika `LAYA_API_KEY` diatur di environment).
- `Content-Type`: `application/json`

#### Request Body
```json
{
  "state": "Help! My payouts have been failing for 3 days.",
  "model": "laya",
  "questions": {
    "is_urgent": {
      "type": "noul",
      "instructions": "Does this convey urgency?",
      "criteria": {
        "true": "Explicitly time-sensitive",
        "false": "No urgency expressed"
      }
    },
    "department": {
      "type": "choice",
      "instructions": "Which team should handle this?",
      "criteria": {
        "billing": "Payments, invoicing, refunds",
        "technical": "Bugs, outages, integrations",
        "sales": "Pricing, upgrades, new accounts"
      }
    },
    "frustration": {
      "type": "score",
      "instructions": "How frustrated is the customer?",
      "criteria": ["Calm", "Frustrated", "Very angry"]
    }
  }
}
```

#### Request Fields
- `state` (`str | dict | list`, required): Data yang dievaluasi.
- `model` (`str`, optional): Default `"laya"`. Nilai alias seperti `"jev-latest"`, `"english"`, `"multilingual"`, atau `"typed-decisions"` diteruskan/di-resolve oleh Router Laya.
- `questions` (`dict[str, Question]`, required): Map ID pertanyaan ke definisi pertanyaan:
  - `noul`: `{ "type": "noul", "instructions": ..., "criteria": { "true": ..., "false": ... } }`
  - `choice`: `{ "type": "choice", "instructions": ..., "criteria": { "<option>": "<desc>", ... } }`
  - `score`: `{ "type": "score", "instructions": ..., "criteria": ["<level 0>", "<level 1>", ...] }`

#### Response Body
```json
{
  "model": "laya",
  "answers": {
    "is_urgent": {
      "type": "noul",
      "noul": 0.95
    },
    "department": {
      "type": "choice",
      "choice": "billing",
      "probabilities": {
        "billing": 0.88,
        "technical": 0.12,
        "sales": 0.0
      },
      "confidence": 0.81
    },
    "frustration": {
      "type": "score",
      "score": 1.05,
      "legend": {
        "0": "Calm",
        "1": "Frustrated",
        "2": "Very angry"
      },
      "probabilities": {
        "0": 0.0,
        "1": 0.95,
        "2": 0.05
      },
      "confidence": 0.92
    }
  },
  "usage": {
    "input_tokens": 128,
    "output_tokens": 12
  }
}
```

## 4. Adapter & Normalization Logic
Laya `router.predict(state, questions)` menghasilkan kamus jawaban. Normalisasi respons ke format Jev meliputi:
1. **Noul Answer**:
   - Tipe: `"noul"`.
   - Laya mengembalikan float probabilitas atau dict. Diubah menjadi format `{ "type": "noul", "noul": float(val) }`.
2. **Choice Answer**:
   - Tipe: `"choice"`.
   - Properti: `choice` (string label pemenang), `probabilities` (map label ke float [0..1]), `confidence` (float [0..1]).
3. **Score Answer**:
   - Tipe: `"score"`.
   - Properti: `score` (float nilai tertimbang), `legend` (map index `"0"`, `"1"` ke deskripsi kriteria), `probabilities` (map index ke float), `confidence` (float).
4. **Usage**:
   - Mengestimasi jumlah token input berdasarkan panjang karakter state & criteria, dan output token berdasarkan jumlah pertanyaan (output System 1 bersifat non-generatif).

## 5. Authentication & Environment Configuration
- `LAYA_API_KEY` (string, optional): Token API untuk header `Authorization: Bearer <API_KEY>`. Jika tidak disetel, auth di-bypass.
- `LAYA_DEVICE` (string, default `"auto"`): Target device PyTorch (`"cuda"`, `"cpu"`, `"mps"`, atau `"auto"`).
- `LAYA_PRELOAD` (bool, default `true`): Memuat model ke memori saat server booting.
- `PORT` (int, default `8000`): Port server.
- `HOST` (string, default `"0.0.0.0"`): Host binding.

## 6. Error Handling
Mengikuti HTTP status codes standar TypeSafe Jev:
- `401 Unauthorized`: Header `Authorization` tidak ada atau tidak valid saat `LAYA_API_KEY` aktif.
- `422 Unprocessable Entity`: Request body tidak sesuai skema (misal `type` tidak dikenali, `criteria` score < 2 level).
- `500 Internal Server Error`: Terjadi kegagalan komputasi pada model Laya.

## 7. Testing Strategy
File pengujian `tests/test_api.py` menggunakan `pytest` dan `fastapi.testclient.TestClient`:
1. **Test Auth**: Request tanpa header / token salah -> status `401`.
2. **Test Validation**: Request malformed (misal `type: unknown`) -> status `422`.
3. **Test System One Inference**: Mocking / real call ke adapter Laya memverifikasi output format `noul`, `choice`, dan `score` sesuai kontrak TypeSafe.
4. **Test Healthz**: Memastikan `GET /healthz` mengembalikan status `200`.

## 8. Constraints & Edge Cases
- **Batas Label Choice**: Checkpoint Laya optimal pada <= 20 opsi per pertanyaan. Pertanyaan dengan >20 opsi akan tetap diproses namun dialokasikan token terbatas sesuai budget `head_max_len`.
- **Non-Latin Scripts**: Secara otomatis dialihkan oleh Laya Router ke checkpoint multilingual (`convaiinnovations/laya-multilingual`).
