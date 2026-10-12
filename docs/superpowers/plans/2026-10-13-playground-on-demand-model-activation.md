# Playground On-Demand Model Download & Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users on the model detail page to trigger download and loading of any inactive model on-demand when attempting to test it in the playground, featuring a confirmation modal, real-time SSE progress bar, and automatic post-activation inference execution.

**Architecture:** Public API router for models (`POST /api/models/activate` and `GET /api/models/stream`) delegating to `ModelSetupManager`. Frontend `model_detail.html` intercepts `runInference()` when the model is inactive, displays a confirmation modal, listens to SSE progress events, and automatically runs the queued inference request once the model is active.

**Tech Stack:** FastAPI, SSE (Server-Sent Events), Pydantic, Jinja2, TailwindCSS, Vanilla JS, Pytest.

## Global Constraints
- All descriptions, modal copy, button labels, and system status messages MUST be written in English.
- Public model activation does NOT require admin authentication cookies or bearer tokens.
- Interception occurs when the user clicks "Run Inference" (or uses `Ctrl+Enter`) while the model is in `Non Active` state.
- The modal displays real-time download and load progress via `GET /api/models/stream`.
- Upon successful activation: the status badge dynamically updates to `Active`, the modal closes, and `runInference()` executes automatically.
- Unit and integration tests must run without downloading actual multi-GB weights from Hugging Face.

---

### Task 1: Public Models Activation & Stream API Router

**Files:**
- Create: `app/api/models_route.py`
- Modify: `app/api/__init__.py`
- Test: `tests/test_public_models_activate.py`

**Interfaces:**
- Produces:
  `POST /api/models/activate`
  `GET /api/models/stream`

- [ ] **Step 1: Write the failing test for public model activation & stream**

Create `tests/test_public_models_activate.py`:
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.core.server import create_application


@pytest.fixture
def client_public():
    app = create_application()
    return TestClient(app)


def test_activate_model_validation(client_public):
    # Missing or empty model name
    resp = client_public.post("/api/models/activate", json={"model": ""})
    assert resp.status_code == 400

    # Unknown model name
    resp_unknown = client_public.post("/api/models/activate", json={"model": "completely-unknown-model-xyz"})
    assert resp_unknown.status_code == 400


def test_activate_model_success(client_public):
    from app.services.setup_manager import default_setup_manager

    with patch.object(default_setup_manager, "start_setup", new_callable=AsyncMock) as mock_start:
        resp = client_public.post("/api/models/activate", json={"model": "d3-lite"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"
        assert data["model"] == "d3-lite"


def test_public_models_stream(client_public):
    async def _finite_stream():
        yield "data: {\"phase\": \"connected\", \"progress\": 0, \"message\": \"Stream connected\"}\n\n"

    with patch("app.services.setup_manager.default_setup_manager.event_generator", _finite_stream):
        resp = client_public.get("/api/models/stream")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_public_models_activate.py -v`
Expected: FAIL (404 on `/api/models/activate`)

- [ ] **Step 3: Implement `app/api/models_route.py` and register in `app/api/__init__.py`**

Create `app/api/models_route.py`:
```python
import asyncio
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.models.registry import default_registry, normalize_model_name
from app.services.setup_manager import default_setup_manager

router = APIRouter()


class ModelActivateRequest(BaseModel):
    model: str


@router.post("/activate")
async def activate_model(body: ModelActivateRequest, request: Request) -> dict:
    raw_name = body.model.strip()
    if not raw_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model name is required",
        )

    model_name = normalize_model_name(raw_name)
    adapter = default_registry.get_adapter(model_name)
    if adapter is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{raw_name}' is not supported. Supported models: laya, d3-lite, kev",
        )

    loaded_models = getattr(request.app.state, "models", {})
    if model_name in loaded_models:
        return {"status": "already_active", "model": model_name}

    if default_setup_manager._is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another model setup or activation is currently in progress",
        )

    asyncio.create_task(default_setup_manager.start_setup(request.app.state, [model_name]))
    return {"status": "started", "model": model_name}


@router.get("/stream")
def stream_model_events() -> StreamingResponse:
    return StreamingResponse(
        default_setup_manager.event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
```

In `app/api/__init__.py`:
Mount `models_route.router` under prefix `/api/models`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_public_models_activate.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/api/models_route.py app/api/__init__.py tests/test_public_models_activate.py
git commit -m "feat(api): add public models activation and SSE stream router"
```

---

### Task 2: On-Demand Activation Confirmation & Progress Modal in `model_detail.html`

**Files:**
- Modify: `app/templates/model_detail.html`
- Modify: `tests/test_model_routes.py`

**Interfaces:**
- Consumes: `POST /api/models/activate`, `GET /api/models/stream`
- Intercepts: `runInference()` when `!isModelActive`

- [ ] **Step 1: Write test verifying activation modal presence and English copy in `model_detail.html`**

Add to `tests/test_model_routes.py`:
```python
def test_model_detail_activation_modal_present(client_no_auth):
    resp = client_no_auth.get("/vllm-sr/d3-lite")
    assert resp.status_code == 200
    html = resp.text
    assert 'id="model-activate-modal"' in html
    assert "MODEL NOT LOADED YET" in html
    assert "Download & Activate Model" in html
    assert "Cancel" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_model_routes.py::test_model_detail_activation_modal_present -v`
Expected: FAIL

- [ ] **Step 3: Update `app/templates/model_detail.html`**

1. Add `#model-activate-modal` HTML markup:
   - Fixed locked overlay (`bg-black/85 backdrop-blur-sm hidden`).
   - Brutalist card (`bg-[#141417] border border-[#3f3f46] p-6 max-w-lg`).
   - Phase 1 (Prompt):
     - Title: `⚡ MODEL NOT LOADED YET`
     - Description: `Model {{ model.display_name }} is currently inactive and not loaded into system memory. Would you like to download its weights and load it into memory now to run inference in this playground?`
     - Action buttons: `[ Cancel ]` and `[ Download & Activate Model ]`.
   - Phase 2 (Progress):
     - Hidden initially, shown upon clicking Download.
     - Progress bar with real-time percentage (0% to 100%).
     - Status message (e.g., `Downloading model weights to disk...` -> `Loading model into memory...`).
     - Mini live log terminal box.
   - Phase 3 (Success):
     - Green success banner: `✅ Model successfully loaded into memory and ready for inference!`
     - Automatically dismisses after 1.2s or upon clicking `Continue to Playground`.

2. Update JavaScript in `model_detail.html`:
   - Initialize `let isModelActive = {{ 'true' if is_active else 'false' }};`.
   - In `runInference()`:
     - Check `if (!isModelActive) { openActivateModal(); return; }`.
   - In `openActivateModal()`:
     - Shows modal with Phase 1.
   - When user clicks `[ Download & Activate Model ]`:
     - Calls `POST /api/models/activate` with `{"model": "{{ model.id }}"}`.
     - Connects `new EventSource('/api/models/stream')`.
     - Updates progress bar and status text dynamically.
     - On event `phase === "completed"`:
       - Sets `isModelActive = true`.
       - Updates header badge to `Active`.
       - Closes modal.
       - Automatically calls `runInference()` so user's query executes immediately!

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_model_routes.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add app/templates/model_detail.html tests/test_model_routes.py
git commit -m "feat(ui): add playground on-demand model activation modal with SSE progress"
```

---
