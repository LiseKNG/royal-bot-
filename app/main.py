import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .config import settings
from .db import init_db, engine
from .web import web
from .bot import run_polling

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(run_polling())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await engine.dispose()

app = FastAPI(title="Telegram Community Suite", lifespan=lifespan)
app.mount("/", web)
