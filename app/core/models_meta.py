"""Model metadata catalog for System One models."""

from typing import Any

MODELS_CATALOG: dict[str, dict[str, Any]] = {
    "convaiinnovations/laya-multilingual": {
        "id": "convaiinnovations/laya-multilingual",
        "creator": "convaiinnovations",
        "name": "laya-multilingual",
        "display_name": "Laya Multilingual",
        "params": "322M",
        "context_window": "512 tokens",
        "modality": "Text",
        "license": "Apache-2.0",
        "summary": "Ultra-fast low-latency multilingual model supporting 100+ languages for instant classification and scoring.",
        "description": (
            "Laya is a 322M parameter multilingual encoder based on the mmBERT architecture. "
            "Designed for real-time edge and server deployments, it evaluates natural language state "
            "against structured questions across 100+ languages with sub-5ms latency."
        ),
        "architecture": "mmBERT-base",
        "huggingface_url": "https://huggingface.co/convaiinnovations/laya-multilingual",
        "benchmarks": [
            {"metric": "Latency (p50)", "value": "2.8ms", "note": "Single CPU inference"},
            {"metric": "Languages", "value": "100+", "note": "High-accuracy multilingual coverage"},
            {"metric": "Throughput", "value": "350 req/s", "note": "Standard 4-core worker"},
        ],
        "code_curl": (
            'curl -X POST http://localhost:8000/v1/systemone \\\n'
            '  -H "Content-Type: application/json" \\\n'
            '  -H "Authorization: Bearer dev-key" \\\n'
            '  -d \'{\n'
            '    "model": "laya-multilingual",\n'
            '    "state": "User requested refund for damaged goods after 2 days",\n'
            '    "questions": {\n'
            '      "refund_eligible": {"type": "noul"},\n'
            '      "sentiment": {"type": "choice", "criteria": {"positive": "Happy", "negative": "Unhappy"}}\n'
            '    }\n'
            '  }\''
        ),
        "code_python": (
            "import httpx\n\n"
            "response = httpx.post(\n"
            '    "http://localhost:8000/v1/systemone",\n'
            '    headers={"Authorization": "Bearer dev-key"},\n'
            "    json={\n"
            '        "model": "laya-multilingual",\n'
            '        "state": "User requested refund for damaged goods after 2 days",\n'
            '        "questions": {\n'
            '            "refund_eligible": {"type": "noul"},\n'
            '            "sentiment": {\n'
            '                "type": "choice",\n'
            '                "criteria": {"positive": "Happy", "negative": "Unhappy"},\n'
            "            },\n"
            "        },\n"
            "    },\n"
            ")\n"
            "print(response.json())\n"
        ),
    },
    "vllm-sr/d3-lite": {
        "id": "vllm-sr/d3-lite",
        "creator": "vllm-sr",
        "name": "d3-lite",
        "display_name": "D3-Lite",
        "params": "450M",
        "context_window": "2048 tokens",
        "modality": "Multimodal (Text + Vision)",
        "license": "Apache-2.0",
        "summary": "Compact multimodal decision model for concurrent text and visual state evaluation.",
        "description": (
            "D3-Lite delivers high-throughput multimodal judgment capabilities. "
            "Built for low-overhead vision-language pipelines, it processes visual embeddings "
            "alongside conversational context to return calibrated classification decisions."
        ),
        "architecture": "D3 Transformer",
        "huggingface_url": "https://huggingface.co/vllm-sr/d3-lite",
        "benchmarks": [
            {"metric": "Latency (p50)", "value": "6.4ms", "note": "Quantized GPU inference"},
            {"metric": "Modality", "value": "Text + Vision", "note": "Concurrent dual-stream"},
            {"metric": "Throughput", "value": "180 req/s", "note": "Batch evaluation"},
        ],
        "code_curl": (
            'curl -X POST http://localhost:8000/v1/systemone \\\n'
            '  -H "Content-Type: application/json" \\\n'
            '  -H "Authorization: Bearer dev-key" \\\n'
            '  -d \'{\n'
            '    "model": "d3-lite",\n'
            '    "state": "Package delivered to front porch step, undamaged packaging",\n'
            '    "questions": {\n'
            '      "delivery_successful": {"type": "noul"},\n'
            '      "risk_score": {"type": "score", "criteria": ["Safe", "Moderate", "High"]}\n'
            '    }\n'
            '  }\''
        ),
        "code_python": (
            "import httpx\n\n"
            "response = httpx.post(\n"
            '    "http://localhost:8000/v1/systemone",\n'
            '    headers={"Authorization": "Bearer dev-key"},\n'
            "    json={\n"
            '        "model": "d3-lite",\n'
            '        "state": "Package delivered to front porch step, undamaged packaging",\n'
            '        "questions": {\n'
            '            "delivery_successful": {"type": "noul"},\n'
            '            "risk_score": {\n'
            '                "type": "score",\n'
            '                "criteria": ["Safe", "Moderate", "High"],\n'
            "            },\n"
            "        },\n"
            "    },\n"
            ")\n"
            "print(response.json())\n"
        ),
    },
    "jaredpalmer/kev-0.8b": {
        "id": "jaredpalmer/kev-0.8b",
        "creator": "jaredpalmer",
        "name": "kev-0.8b",
        "display_name": "Kev 0.8B",
        "params": "800M",
        "context_window": "4096 tokens",
        "modality": "Text",
        "license": "Apache-2.0",
        "summary": "Lightweight autoregressive System One judgment model calibrated for zero-shot decision primitives.",
        "description": (
            "Kev-0.8b specializes in programmable common sense and probability routing. "
            "Designed by Jared Palmer, it converts complex application state into rapid typed choices "
            "and probability distributions."
        ),
        "architecture": "Decoder-only Transformer",
        "huggingface_url": "https://huggingface.co/jaredpalmer/kev-0.8b",
        "benchmarks": [
            {"metric": "Latency (p50)", "value": "4.2ms", "note": "ONNX / torch runtime"},
            {"metric": "Calibration ECE", "value": "<0.04", "note": "High confidence alignment"},
            {"metric": "Throughput", "value": "240 req/s", "note": "Single-node worker"},
        ],
        "code_curl": (
            'curl -X POST http://localhost:8000/v1/systemone \\\n'
            '  -H "Content-Type: application/json" \\\n'
            '  -H "Authorization: Bearer dev-key" \\\n'
            '  -d \'{\n'
            '    "model": "kev-0.8b",\n'
            '    "state": "Customer asking for pricing upgrade options on enterprise plan",\n'
            '    "questions": {\n'
            '      "intent": {"type": "choice", "criteria": {"upgrade": "Upgrade account", "cancel": "Cancel account", "other": "Other"}}\n'
            '    }\n'
            '  }\''
        ),
        "code_python": (
            "import httpx\n\n"
            "response = httpx.post(\n"
            '    "http://localhost:8000/v1/systemone",\n'
            '    headers={"Authorization": "Bearer dev-key"},\n'
            "    json={\n"
            '        "model": "kev-0.8b",\n'
            '        "state": "Customer asking for pricing upgrade options on enterprise plan",\n'
            '        "questions": {\n'
            '            "intent": {\n'
            '                "type": "choice",\n'
            '                "criteria": {\n'
            '                    "upgrade": "Upgrade account",\n'
            '                    "cancel": "Cancel account",\n'
            '                    "other": "Other",\n'
            "                },\n"
            "            },\n"
            "        },\n"
            "    },\n"
            ")\n"
            "print(response.json())\n"
        ),
    },
}


def get_all_models() -> list[dict[str, Any]]:
    """Return metadata for all registered models."""
    return list(MODELS_CATALOG.values())


def get_model_by_slug(creator: str, name: str) -> dict[str, Any] | None:
    """Retrieve model metadata by creator and model name slugs."""
    for model in MODELS_CATALOG.values():
        if model["creator"] == creator and model["name"] == name:
            return model
    return None
