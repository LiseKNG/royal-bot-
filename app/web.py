from fastapi import FastAPI, Request, Depends, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .config import settings
from .db import get_session
from .models import Owner, Space, Member, EventLog
from .services import owner_stats

templates = Jinja2Templates(directory="templates")
web = FastAPI(title="Telegram Community Suite", version="0.1.0")

async def resolve_owner(x_telegram_owner_id: int | None = Header(default=None),
                        x_admin_token: str | None = Header(default=None),
                        session: AsyncSession = Depends(get_session)) -> Owner:
    # Mode MVP : jeton administrateur + ID propriétaire. À remplacer par une authentification
    # Telegram Login/OIDC avant toute exposition publique.
    if not settings.web_admin_token or settings.web_admin_token in ("CHANGE_ME", "replace_me"):
        raise HTTPException(status_code=503, detail="Configure WEB_ADMIN_TOKEN avant d'utiliser l'API.")
    if x_admin_token != settings.web_admin_token:
        raise HTTPException(status_code=401, detail="Jeton d'administration invalide.")
    if not x_telegram_owner_id:
        raise HTTPException(status_code=400, detail="En-tête X-Telegram-Owner-Id requis.")
    owner = await session.scalar(select(Owner).where(Owner.telegram_id == x_telegram_owner_id))
    if not owner:
        raise HTTPException(status_code=404, detail="Propriétaire inconnu. Lance /start avec le bot.")
    return owner

@web.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
   return templates.TemplateResponse(request, "index.html")

@web.get("/health")
async def health():
    return {"status": "ok"}

@web.get("/api/me")
async def api_me(owner: Owner = Depends(resolve_owner)):
    return {"telegram_id": owner.telegram_id, "display_name": owner.display_name}

@web.get("/api/spaces")
async def api_spaces(owner: Owner = Depends(resolve_owner), session: AsyncSession = Depends(get_session)):
    rows = (await session.scalars(select(Space).where(Space.owner_id == owner.id).order_by(Space.id))).all()
    return [{"id": s.id, "chat_id": s.chat_id, "title": s.title, "username": s.username,
             "kind": s.kind, "enabled": s.enabled} for s in rows]

@web.get("/api/stats")
async def api_stats(owner: Owner = Depends(resolve_owner), session: AsyncSession = Depends(get_session)):
    return await owner_stats(session, owner.id)

@web.get("/api/members")
async def api_members(space_id: int, owner: Owner = Depends(resolve_owner),
                      session: AsyncSession = Depends(get_session), limit: int = 100):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit doit être entre 1 et 500.")
    space = await session.scalar(select(Space).where(Space.id == space_id, Space.owner_id == owner.id))
    if not space:
        raise HTTPException(status_code=404, detail="Espace introuvable.")
    rows = (await session.scalars(select(Member).where(Member.space_id == space.id)
                                  .order_by(Member.last_seen_at.desc()).limit(limit))).all()
    return [{"telegram_id": m.telegram_id, "username": m.username, "first_name": m.first_name,
             "last_name": m.last_name, "status": m.status, "warnings": m.warnings,
             "message_count": m.message_count, "last_seen_at": m.last_seen_at.isoformat()}
            for m in rows]

@web.get("/api/events")
async def api_events(owner: Owner = Depends(resolve_owner), session: AsyncSession = Depends(get_session),
                     limit: int = 100):
    limit = max(1, min(limit, 500))
    rows = (await session.scalars(select(EventLog).where(EventLog.owner_id == owner.id)
                                  .order_by(EventLog.created_at.desc()).limit(limit))).all()
    return [{"id": e.id, "space_id": e.space_id, "actor": e.actor_telegram_id,
             "target": e.target_telegram_id, "type": e.event_type, "details": e.details,
             "created_at": e.created_at.isoformat()} for e in rows]
