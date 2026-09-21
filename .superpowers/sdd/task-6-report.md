# Task 6 Report: Refactor Tests to Target app/

## Overview
Refactored the test suite under `tests/` to target the `app` package instead of legacy top-level or `src.*` modules, completing Task 6 of the project structure refactoring.

## Changes Made
1. **Created `tests/conftest.py`:**
   - Added `client_no_auth` fixture: configures settings with no API key and mock router enabled; initializes `TestClient(create_application(mock_router=True))`.
   - Added `client_with_auth` fixture: configures settings with secret API key and mock router enabled; initializes `TestClient(create_application(mock_router=True))`.
2. **Updated `tests/test_api.py`:**
   - Switched imports to `app.core.server.create_application`, `app.core.config.settings`, and `app.core.security.verify_api_key`.
   - Leveraged shared `client_no_auth` and `client_with_auth` fixtures from `conftest.py`.
   - Verified healthcheck, authentication error handling, authorized mock responses, schema validation errors, token mismatches, multi-question payload processing, lifespan router attachment, and constant-time secret comparison.
3. **Updated `tests/test_schemas.py`:**
   - Switched imports from legacy `schemas` to `app.dto`.
   - Verified validation of request and response schemas, including question validation rules (e.g. score question requiring >= 2 criteria).
4. **Updated `tests/test_adapter.py`:**
   - Switched imports to `app.dto` and `app.services.laya_service` (`estimate_usage`, `format_jev_response`).
   - Verified mapping logic, usage estimation, defaults handling, and explicit None handling.

## Verification
- Executed: `uv run pytest`
- Output:
  ```
  collected 15 items
  tests\test_adapter.py ....                                               [ 26%]
  tests\test_api.py ........                                               [ 80%]
  tests\test_schemas.py ...                                                [100%]
  ======================== 15 passed, 3 warnings in 1.83s ========================
  ```
- All 15 tests passed cleanly with 0 failures.

## Commit
- Commit: `df0496e`
- Message: `test: update test suite to import from app package`
