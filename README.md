<div align="center" style="text-align: center;">
  <h1>Zulvis System One</h1>
  <p><strong>We took the opposite research direction.</strong></p>
  <p>
    Deterministic parallel decisions with calibrated probabilities. Drop-in TypeSafe Jev API.<br />
    Single forward pass (~33ms) &bull; 0% hallucination &bull; Zero generative text
  </p>
  <p align="center" style="text-align: center;">
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-2ea44f" alt="License: Apache-2.0"></a>
    <a href="https://github.com/ZulfiFazhar/system-one"><img src="https://img.shields.io/badge/python-3.12-blue?logo=python" alt="Python 3.12"></a>
    <a href="https://github.com/ZulfiFazhar/system-one"><img src="https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi" alt="FastAPI"></a>
    <a href="https://github.com/ZulfiFazhar/system-one"><img src="https://img.shields.io/badge/docker-ready-2496ed?logo=docker" alt="Docker"></a>
  </p>
</div>

---

> **We took the opposite research direction.** Generative models predict text sequentially token by token, accumulating latency, cost, and hallucination. **Zulvis System One** uses a bidirectional encoder with direct decision heads to produce calibrated probabilities and structured choices in a single forward pass (~33ms) — **0% hallucination**, zero generative text, and zero prompt-and-parse friction.

> **What is System One?** Introduced by [TypeSafe AI](https://typesafe.ai/) and inspired by Daniel Kahneman's _Thinking, Fast and Slow_, System One models execute fast, intuitive, and deterministic machine judgments. This project is a production-ready, self-hosted implementation compatible with the TypeSafe Jev API contract.

---

## What it does

- **Drop-in TypeSafe Jev Compatibility**: Implements `POST /v1/systemone` matching the TypeSafe SDK specification — redirect your existing client by simply changing `base_url`.
- **Parallel Decisions in ~33ms**: Evaluates multiple heterogeneous questions (`noul`, `choice`, `score`) simultaneously in a single forward pass over input state.
- **Calibrated Probabilities & Zero Hallucination**: Outputs mathematical confidence scores and categorical distributions instead of uncontrolled tokens.
- **Offline & Air-Gapped Operation**: Auto-downloads weights once on first boot if missing, then locks into strict offline mode (`HF_HUB_OFFLINE=1`). No runtime external telemetry or cloud dependencies.
- **Built-in Interactive Web UI**: Includes a high-contrast brutalist dashboard and live inspector served right at `/`.
- **Production Guardrails**: In-memory token-bucket rate limiting, constant-time API key security, non-root Docker container, and full Pytest test suite.

---

## See the difference

Generative LLMs force classification through autoregressive text completion. System One models execute typed decisions directly on state embeddings.

| Metric / Aspect        | Generative LLMs (System 2)                   | Zulvis System One (System 1)                             |
| :--------------------- | :------------------------------------------- | :------------------------------------------------------- |
| **Execution Model**    | Sequential autoregressive token generation   | Bidirectional encoder with parallel decision heads       |
| **Inference Latency**  | 800ms – 5,000ms+ per decision                | **~33ms** single forward pass                            |
| **Hallucination Rate** | Inevitable token drift & schema violations   | **0% hallucination** (strictly bounded discrete choices) |
| **Output Format**      | Unstructured markdown / fragile JSON strings | Strongly typed typed values (`float`, `choice`, `score`) |
| **Confidence Metric**  | Heuristic or absent                          | Mathematically calibrated softmax probabilities          |
| **Hardware Footprint** | Heavy VRAM requirements or pricey cloud APIs | Runs efficiently on modest CPU or single low-cost GPU    |

---

## Install & Run

Choose the deployment method that fits your environment:

### 1. Local with `uv` (Recommended)

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/):

```bash
# Clone the repository
git clone https://github.com/ZulfiFazhar/system-one.git
cd system-one

# Install dependencies into virtual environment
uv sync

# Run development server with live reload
uv run fastapi dev

# Or run production server
uv run fastapi run --port 8000
```

> **Auto-Download Notice:**
> If `models/laya-multilingual/` does not yet exist locally, the server automatically downloads model weights from Hugging Face (`convaiinnovations/laya-multilingual`) on initial startup, then locks into permanent offline mode.

### 2. Docker & Docker Compose

Run fully isolated with pre-configured volume mounts for local weights:

```bash
docker compose up -d
```

`docker-compose.yml`:

```yaml
services:
  system-one:
    image: ghcr.io/zulfifazhar/system-one:latest
    container_name: system-one-api
    ports:
      - "8000:8000"
    environment:
      - LAYA_DEVICE=cpu
      - LAYA_MODEL_PATH=models/laya-multilingual
    volumes:
      - ./models:/app/models
    restart: unless-stopped
```

### 3. Production Process Manager (PM2)

```bash
pm2 start "uv run fastapi run --port 8000" --name system-one
```

---

## API Reference

### `GET /health`

Returns engine readiness and preloading status.

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ready",
  "model": "laya",
  "preloaded": true
}
```

---

### `POST /v1/systemone`

Send an input state and an arbitrary set of questions. The engine answers all of them in parallel.

```bash
curl -X POST http://localhost:8000/v1/systemone \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "state": "My card was charged twice for the March subscription. Please refund the duplicate transaction immediately or cancel my account.",
    "model": "laya",
    "questions": {
      "department": {
        "type": "choice",
        "instructions": "Which department should handle this request?",
        "criteria": {
          "billing": "Invoices, transactions, chargebacks, refunds",
          "technical": "Software bugs, outages, system integration",
          "sales": "Enterprise quotes, upgrades, plan changes"
        }
      },
      "urgency": {
        "type": "score",
        "instructions": "How urgent is this customer issue?",
        "criteria": ["Low priority", "Medium priority", "Critical emergency"]
      },
      "churn_risk": {
        "type": "noul",
        "instructions": "Is the user explicitly threatening to cancel or churn?"
      }
    }
  }'
```

#### Response

```json
{
  "model": "laya",
  "answers": {
    "department": {
      "type": "choice",
      "choice": "billing",
      "probabilities": {
        "billing": 0.92,
        "technical": 0.05,
        "sales": 0.03
      },
      "confidence": 0.89
    },
    "urgency": {
      "type": "score",
      "score": 1.74,
      "legend": {
        "0": "Low priority",
        "1": "Medium priority",
        "2": "Critical emergency"
      },
      "probabilities": {
        "0": 0.04,
        "1": 0.22,
        "2": 0.74
      },
      "confidence": 0.82
    },
    "churn_risk": {
      "type": "noul",
      "noul": 0.95
    }
  },
  "usage": {
    "input_tokens": 134,
    "output_tokens": 12
  }
}
```

---

## Question Types

| Type     | Purpose                                            | Return Attributes                                                       |
| :------- | :------------------------------------------------- | :---------------------------------------------------------------------- |
| `noul`   | Boolean proposition truth probability              | `noul` (calibrated float from `0.0` to `1.0`)                           |
| `choice` | Categorical selection across discrete options      | `choice`, `probabilities` (distribution map), `confidence`              |
| `score`  | Ordinal rating evaluated against an ordered rubric | `score` (expected value float), `legend`, `probabilities`, `confidence` |

---

## Environment Variables

| Variable                    | Default                               | Description                                                     |
| :-------------------------- | :------------------------------------ | :-------------------------------------------------------------- |
| `LAYA_MODEL_PATH`           | `models/laya-multilingual`            | Relative path to local model weights folder.                    |
| `LAYA_MODEL_ID`             | `convaiinnovations/laya-multilingual` | Hugging Face repository ID for automatic initial download.      |
| `LAYA_DEVICE`               | `auto`                                | PyTorch runtime device (`cuda`, `cpu`, `mps`, or `auto`).       |
| `LAYA_PRELOAD`              | `true`                                | Preload model weights into memory during application boot.      |
| `LAYA_LAZY_LOAD`            | `false`                               | Defer model loading until the first received inference request. |
| `LAYA_API_KEY`              | `""`                                  | Optional Bearer secret to bypass rate limiting.                 |
| `RATE_LIMIT_ENABLED`        | `true`                                | Enable client IP rate limiting for unauthenticated requests.    |
| `RATE_LIMIT_REQUESTS`       | `10`                                  | Maximum requests permitted per IP inside the time window.       |
| `RATE_LIMIT_WINDOW_SECONDS` | `60`                                  | Rolling window length in seconds.                               |
| `PORT`                      | `8000`                                | Server listening port.                                          |
| `HOST`                      | `0.0.0.0`                             | Server network bind address.                                    |

---

## Project Structure

```
system-one/
├── models/
│   └── laya-multilingual/          # Local offline model weights
├── app/
│   ├── main.py                    # Application entrypoint
│   ├── api/
│   │   ├── health_route.py        # GET /health endpoint
│   │   └── systemone_route.py     # POST /v1/systemone endpoint
│   ├── core/
│   │   ├── config.py              # Settings & environment validation
│   │   ├── schema.py              # Base response envelopes
│   │   ├── security.py            # API key & rate limiting middleware
│   │   └── server.py              # Lifespan handlers & asset mounting
│   ├── dto/
│   │   └── systemone_dto.py       # Pydantic v2 schemas for Jev contract
│   ├── services/
│   │   ├── health.py              # System health inspector
│   │   └── laya_service.py        # Token estimation & inference adapter
│   └── templates/
│       └── index.html             # Brutalist interactive web dashboard
├── public/
│   ├── cool-orb.gif               # Animated ASCII orb asset
│   ├── css/                       # Static styles
│   └── js/                        # Client-side scripts
├── tests/
│   ├── conftest.py                # Test setup & fixtures
│   ├── test_adapter.py            # Model adapter unit tests
│   ├── test_api.py                # Endpoint integration tests
│   └── test_schemas.py            # DTO validation tests
├── .github/
│   └── workflows/
│       └── docker-publish.yml     # CI build & GHCR publish pipeline
├── docker-compose.yml             # Container orchestration configuration
└── Dockerfile                     # Multi-stage container definition
```

---

## Testing

Run the test suite using `pytest`:

```bash
uv run pytest -v
```

---

## Model Checkpoints

| Checkpoint                               | Architecture     | Parameters | Recommended Use Case                        |
| :--------------------------------------- | :--------------- | :--------- | :------------------------------------------ |
| `convaiinnovations/laya`                 | ModernBERT-large | 421M       | English text, guardrails, ticket triage     |
| `convaiinnovations/laya-multilingual`    | mmBERT-base      | 322M       | 100+ languages, ultra-fast low latency      |
| `convaiinnovations/laya-typed-decisions` | ModernBERT-large | 421M       | Complex multi-step typed-decision pipelines |

---

## FAQ

### Can I use the official TypeSafe Python/TypeScript SDK?

Yes. The service implements the exact `POST /v1/systemone` request and response contract. Simply configure your TypeSafe client with:

```python
client = TypeSafe(base_url="http://localhost:8000/v1")
```

### How does the offline mode work?

On first launch, if weights are absent, they are pulled from Hugging Face into `models/laya-multilingual/`. Immediately after, the service sets `HF_HUB_OFFLINE=1`, ensuring the process never makes external network calls during inferences.

### Where are the weights stored in Docker?

Model weights live on your host machine in `./models` and are mounted into the container at `/app/models`. Because `WORKDIR` is `/app`, setting `LAYA_MODEL_PATH=models/laya-multilingual` seamlessly resolves to `/app/models/laya-multilingual`.

---

## Credits & Attribution

- **Public Web UI & API Engine**: Designed and developed by [Zulfi Fazhar](https://github.com/ZulfiFazhar/system-one).
- **Laya Model Architecture**: Developed and published by [Convai Innovations](https://huggingface.co/convaiinnovations) and [Nandha Kishor](https://github.com/NandhaKishorM/laya).
- **System One & Jev Paradigm**: Conceptualized by [TypeSafe AI](https://typesafe.ai/).

<hr>

<p align="center"><em>“Generative models predict text token by token.<br>
System One executes typed decisions in a single forward pass.”</em></p>

<hr>

## License

[Apache 2.0](LICENSE)
