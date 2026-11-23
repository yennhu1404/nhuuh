import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"
QUARANTINE_DIR = BASE_DIR / "data_quarantine"
ENV_PATH = BASE_DIR / ".env"

# Create directories if they don't exist
for folder in [DATA_DIR, EXPORTS_DIR, QUARANTINE_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "enterprise_dwh.db"
SEMANTIC_CATALOG_PATH = CONFIG_DIR / "semantic_catalog.json"

# Load .env manually without external dependencies
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

if ENV_PATH.exists():
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key == "GEMINI_API_KEY" and not GEMINI_API_KEY:
                    GEMINI_API_KEY = val
                elif key == "GEMINI_MODEL" and not GEMINI_MODEL:
                    GEMINI_MODEL = val
