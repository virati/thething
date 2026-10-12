"""Convenience launcher: `uv run python main.py` starts the Advocate app."""

import uvicorn


def main():
    uvicorn.run("app.server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
