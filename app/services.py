from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Owner, Space, Member, EventLog

async def get_or_create_owner(session: AsyncSession, user_id: int, name: str = "") -> Owner:
    owner = await session.scalar(select(Owner).where(Owner.telegram_id == user_id))
    if owner:
        if name:
            owner.display_name = name
        return owner
    owner = Owner(telegram_id=user_id, display_name=name)
    session.add(owner)
    await session.flush()
    return owner

async def upsert_member(session: AsyncSession, space: Space, user) -> Member:
    member = await session.scalar(select(Member).where(
        Member.space_id == space.id, Member.telegram_id == user.id
    ))
    if member is None:
        member = Member(space_id=space.id, telegram_id=user.id)
        session.add(member)
    member.username = user.username
    member.first_name = user.first_name or ""
    member.last_name = user.last_name or ""
    member.last_seen_at = func.now()
    return member

async def get_space_for_chat(session: AsyncSession, chat_id: int) -> Space | None:
    return await session.scalar(select(Space).where(Space.chat_id == chat_id, Space.enabled.is_(True)))

async def log_event(session: AsyncSession, space: Space | None, actor: int | None,
                    event_type: str, target: int | None = None, details: str = ""):
    session.add(EventLog(owner_id=space.owner_id if space else None,
                         space_id=space.id if space else None,
                         actor_telegram_id=actor, target_telegram_id=target,
                         event_type=event_type, details=details))

async def owner_stats(session: AsyncSession, owner_id: int) -> dict:
    spaces = await session.scalar(select(func.count(Space.id)).where(Space.owner_id == owner_id)) or 0
    members = await session.scalar(select(func.count(Member.id)).join(Space).where(Space.owner_id == owner_id)) or 0
    events = await session.scalar(select(func.count(EventLog.id)).where(EventLog.owner_id == owner_id)) or 0
    return {"spaces": spaces, "members": members, "events": events}
