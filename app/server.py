"""FastAPI app for MCP for Health — serves the JSON API and the SPA."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.advocate import package_context
from app import records

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
STATIC_DIR = BASE / "static"

app = FastAPI(title="MCP for Health — Patient Advocate", version="0.1.0")


def _load(pid: str) -> dict:
    path = DATA_DIR / f"{pid}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Unknown patient {pid}")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/patients")
def list_patients() -> list[dict]:
    index_path = DATA_DIR / "index.json"
    if not index_path.exists():
        raise HTTPException(
            status_code=503,
            detail="No data. Run: uv run python scripts/generate_stories.py",
        )
    return json.loads(index_path.read_text(encoding="utf-8"))


@app.get("/api/patients/{pid}")
def get_patient(pid: str) -> dict:
    return _load(pid)


@app.get("/api/patients/{pid}/package")
def get_package(pid: str) -> dict:
    return package_context(_load(pid))


# ---- Real patient records (data/patients/<folder>/) ---------------------- #
@app.get("/api/records")
def list_records() -> list[dict]:
    return records.list_records()


@app.get("/api/records/{folder}")
def get_record(folder: str) -> dict:
    try:
        return records.parse_record(folder)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown record {folder}")


@app.get("/api/records/{folder}/regions")
def get_regions(folder: str) -> list[dict]:
    return records.load_regions(folder)


@app.get("/api/records/{folder}/middle-zone")
def get_middle_zone(folder: str) -> dict:
    return records.load_middle_zone(folder)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


# Static assets (JS/CSS). Mounted last so it doesn't shadow the API routes.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
