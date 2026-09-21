# system-one

FastAPI service yang membungkus model **Laya** (`convaiinnovations/laya`) dengan API kompatibel **TypeSafe Jev** (`POST /v1/systemone`). Kirim `state` dan `questions`, terima keputusan terstruktur dengan probabilitas yang dikalibrasi — tanpa teks generatif, tanpa parsing.

## Quickstart

```bash
# Install dependencies
uv sync

# Jalankan development server (auto-reload)
fastapi dev
# atau via uv:
uv run fastapi dev

# Jalankan production server
fastapi run
# atau dengan custom port:
uv run fastapi run --port 8000
```

> **Catatan Auto-Download Model:**
> Jika repositori baru di-clone dan folder `models/laya-multilingual/` belum memiliki file weights, server akan otomatis mendownload model `convaiinnovations/laya-multilingual` dari Hugging Face ke folder `models/` saat startup pertama kali. Setelah itu, server mengunci mode offline (`HF_HUB_OFFLINE=1`) sehingga setiap request tidak akan pernah menghubungi Hugging Face lagi.

### PM2

```bash
pm2 start "uv run fastapi run --port 20129" --name system-one
```

## API

### `GET /healthz`

```bash
curl http://localhost:8000/healthz
```

```json
{ "status": "ready", "model": "laya", "preloaded": true }
```

### `POST /v1/systemone`

Drop-in replacement untuk TypeSafe Jev SDK — cukup ubah `base_url`.

```bash
curl -X POST http://localhost:8000/v1/systemone \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "state": "Tagihan saya dikenakan dua kali untuk bulan Maret. Tolong kembalikan uangnya atau saya batalkan langganan.",
    "model": "laya",
    "questions": {
      "department": {
        "type": "choice",
        "instructions": "Departemen mana yang harus menangani ini?",
        "criteria": {
          "billing": "Tagihan, pembayaran, refund",
          "technical": "Bug, gangguan, integrasi",
          "sales": "Harga, upgrade, akun baru"
        }
      },
      "urgency": {
        "type": "score",
        "instructions": "Seberapa mendesak permintaan ini?",
        "criteria": ["Tidak mendesak", "Segera", "Kritis"]
      },
      "churn_risk": {
        "type": "noul",
        "instructions": "Apakah pengguna mengancam untuk membatalkan atau pergi?"
      }
    }
  }'
```

**Response:**

```json
{
  "model": "laya",
  "answers": {
    "department": {
      "type": "choice",
      "choice": "billing",
      "probabilities": { "billing": 0.91, "technical": 0.06, "sales": 0.03 },
      "confidence": 0.88
    },
    "urgency": {
      "type": "score",
      "score": 1.72,
      "legend": { "0": "Tidak mendesak", "1": "Segera", "2": "Kritis" },
      "probabilities": { "0": 0.05, "1": 0.23, "2": 0.72 },
      "confidence": 0.81
    },
    "churn_risk": {
      "type": "noul",
      "noul": 0.94
    }
  },
  "usage": { "input_tokens": 128, "output_tokens": 12 }
}
```

## Tipe Pertanyaan

| Tipe | Tujuan | Mengembalikan |
|------|--------|---------------|
| `noul` | Ya/tidak — probabilitas pernyataan benar | `noul` (0–1) |
| `choice` | Pilih satu dari opsi yang didefinisikan | `choice`, `probabilities`, `confidence` |
| `score` | Nilai konten terhadap rubrik bertingkat | `score`, `legend`, `probabilities`, `confidence` |

Semua pertanyaan dalam satu request dieksekusi **paralel** dalam satu forward pass (~33ms).

## Environment Variables

| Variabel | Default | Keterangan |
|---|---|---|
| `LAYA_API_KEY` | — | Bearer token auth untuk bypass rate limit. |
| `LAYA_MODEL_ID` | `convaiinnovations/laya-multilingual` | HF repo ID untuk auto-download saat startup pertama. |
| `LAYA_MODEL_PATH` | `models/laya-multilingual` | Path lokal folder model Laya (offline). |
| `LAYA_DEVICE` | `auto` | Device PyTorch: `cuda`, `cpu`, `mps`, atau `auto`. |
| `LAYA_PRELOAD` | `true` | Preload model saat server start. |
| `RATE_LIMIT_ENABLED` | `true` | Aktifkan rate limiting IP untuk request publik tanpa API key. |
| `RATE_LIMIT_REQUESTS` | `10` | Maksimum request publik per IP dalam window. |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Durasi window rate limiting dalam detik. |
| `PORT` | `8000` | Port server. |
| `HOST` | `0.0.0.0` | Host binding. |

## Struktur File

```
models/
└── laya-multilingual/          # Weights model lokal (offline)

app/
├── __init__.py
├── main.py                    # Entrypoint aplikasi FastAPI
├── api/
│   ├── __init__.py            # Router aggregator
│   ├── health_route.py        # Endpoint GET /healthz dan GET /health
│   └── systemone_route.py     # Endpoint POST /v1/systemone
├── core/
│   ├── __init__.py
│   ├── config.py              # Pydantic Settings & environment
│   ├── schema.py              # BaseResponse & standard envelopes
│   ├── security.py            # API key auth & constant-time check
│   └── server.py              # Lifespan, middlewares, server setup
├── dto/
│   ├── __init__.py            # DTO exports
│   └── systemone_dto.py       # Pydantic v2 schemas (Jev questions/answers)
└── services/
    ├── __init__.py
    ├── health.py              # Health check status
    └── laya_service.py        # Token estimation & JEV adapter

tests/
├── conftest.py                # Pytest fixtures
├── test_adapter.py            # Normalisasi & usage unit tests
├── test_api.py                # End-to-end endpoint tests
└── test_schemas.py            # DTO validation unit tests
```

## Testing

```bash
uv run pytest -v
```

## Model Checkpoints

| Checkpoint | Backbone | Params | Terbaik untuk |
|---|---|---|---|
| `convaiinnovations/laya` | ModernBERT-large | 421M | Teks Inggris, guardrails, email triage |
| `convaiinnovations/laya-multilingual` | mmBERT-base | 322M | 100+ bahasa, ~2.2x lebih cepat |
| `convaiinnovations/laya-typed-decisions` | ModernBERT-large | 421M | Typed-decisions workflows (akurasi 0.766) |

Router otomatis mendeteksi skrip/bahasa dan memilih checkpoint optimal.

## Credits & Attribution

- **Public Web UI & API Wrapper**: Dibuat dan dikembangkan oleh [Zulfi Fazhar](https://github.com/ZulfiFazhar/system-one).
- **Model Laya & Checkpoint Multilingual**: Diteliti dan dirilis oleh [Convai Innovations](https://huggingface.co/convaiinnovations) dan [Nandha Kishor](https://github.com/NandhaKishorM/laya).

## Lisensi

Apache 2.0
