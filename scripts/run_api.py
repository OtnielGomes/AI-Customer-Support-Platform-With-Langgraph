"""Start the FastAPI app with a Windows-compatible asyncio loop."""

from __future__ import annotations

import asyncio
import selectors
import sys

import uvicorn


def _selector_loop() -> asyncio.AbstractEventLoop:
    """Return a SelectorEventLoop (required by psycopg async on Windows)."""
    return asyncio.SelectorEventLoop(selectors.SelectSelector())


async def _serve() -> None:
    """Run Uvicorn on the already-created event loop."""
    config = uvicorn.Config("app.main:app", host="127.0.0.1", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


def main() -> None:
    """Entry point used by local Windows and Unix development."""
    if sys.platform == "win32":
        asyncio.run(_serve(), loop_factory=_selector_loop)
        return
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
