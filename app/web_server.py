from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .config import Settings
from .grok_client import GrokClient
from .memory import ConversationMemory

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class ChatIn(BaseModel):
    message: str
    session: str = "web"


def build_web_app(settings: Settings, grok: GrokClient, memory: ConversationMemory) -> FastAPI:
    app = FastAPI(title="Grok VPS Bot")

    def check_key(x_access_key: str | None) -> None:
        if not settings.web_access_key or x_access_key != settings.web_access_key:
            raise HTTPException(status_code=401, detail="bad access key")

    @app.get("/")
    async def index():
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/health")
    async def health():
        return {"ok": True, "model": settings.grok_model}

    @app.post("/api/chat")
    async def chat(body: ChatIn, x_access_key: str | None = Header(default=None)):
        check_key(x_access_key)
        text = body.message.strip()
        if not text:
            raise HTTPException(status_code=400, detail="empty message")
        chat_id = f"web:{body.session}"
        try:
            reply = grok.chat(memory.get(chat_id), text)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Grok API error: {exc}") from exc
        memory.append(chat_id, "user", text)
        memory.append(chat_id, "assistant", reply)
        return {"reply": reply}

    return app
