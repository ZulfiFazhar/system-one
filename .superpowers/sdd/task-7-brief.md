# Task 7 Brief: Verification & Cleanup

**Files:**
- Delete: `D:\Zulfi\Programming\FastAPI\system-one\src` directory
- Modify: `D:\Zulfi\Programming\FastAPI\system-one\README.md`

### Requirements
1. Run `uv run pytest` before deletion to confirm all tests pass.
2. Remove legacy directory `src/` completely (including all files `app.py`, `adapter.py`, `schemas.py`, `__init__.py`, `__pycache__`).
3. Update `README.md`:
   - Quickstart commands:
     ```bash
     # Install dependencies
     uv sync

     # Jalankan server (mock router, tanpa download model)
     LAYA_MOCK_ROUTER=1 uv run fastapi run app/main.py --port 8000

     # Dengan model Laya asli (download otomatis ~800MB)
     uv run fastapi run app/main.py --port 8000
     ```
   - PM2 commands:
     ```bash
     pm2 start "uv run fastapi run app/main.py --port 20129" --name system-one
     ```
   - File Structure section to reflect `app/` layout:
     ```
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
         └── laya_service.py        # Model inference, MockRouter, JEV adapter

     tests/
     ├── conftest.py                # Pytest fixtures
     ├── test_adapter.py            # Normalisasi & usage unit tests
     ├── test_api.py                # End-to-end endpoint tests
     └── test_schemas.py            # DTO validation unit tests
     ```
4. Run `uv run pytest` after deletion to verify 100% clean test execution.
5. Commit:
`git add -A && git commit -m "chore: remove legacy src/ directory and update README documentation"`
