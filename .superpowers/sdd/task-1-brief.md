# Task 1 Brief: Update Project Configuration & Dependencies

**Files:**
- Modify: `D:\Zulfi\Programming\FastAPI\system-one\pyproject.toml`
- Create: `D:\Zulfi\Programming\FastAPI\system-one\.env.example`
- Create: `D:\Zulfi\Programming\FastAPI\system-one\pyrightconfig.json`

### Requirements
1. Update `pyproject.toml` to:
```toml
[project]
name = "system-one"
version = "0.1.0"
description = "System One Model API for Laya compatible with TypeSafe Jev"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]>=0.141.1",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "httpx>=0.27.0",
]

[tool.uv]
package = false

[tool.fastapi]
entrypoint = "app.main:app"

[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["."]
```

2. Create `.env.example`:
```bash
# Application Settings
APP_NAME="System One (Laya) API"
ENVIRONMENT=development
VERSION=0.1.0
PORT=8000
HOST=0.0.0.0

# Security & CORS
ALLOWED_ORIGINS=["*"]
ALLOWED_HOSTS=["*"]
LAYA_API_KEY=""

# Laya Model Settings
LAYA_DEVICE="auto"
LAYA_PRELOAD=true
LAYA_MOCK_ROUTER=false

# Logging
LOG_LEVEL="INFO"
```

3. Create `pyrightconfig.json`:
```json
{
    "reportMissingImports": "none",
    "reportMissingModuleSource": "none",
    "reportAttributeAccessIssue": "none",
    "reportCallIssue": "none",
    "reportUnknownMemberType": "none",
    "reportUnknownVariableType": "none",
    "reportUnknownArgumentType": "none",
    "reportUnknownParameterType": "none",
    "reportMissingParameterType": "none",
    "reportAny": "none"
}
```

4. Run `uv sync` to ensure dependencies and project resolve properly with `package = false`.
5. Commit with message: `chore: update pyproject.toml, .env.example, and pyrightconfig`
