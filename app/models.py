from datetime import datetime, timezone
from sqlalchemy import String, BigInteger, Integer, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

def utcnow():
    return datetime.now(timezone.utc)

class Base(DeclarativeBase):
    pass

class Owner(Base):
    __tablename__ = "owners"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Space(Base):
    __tablename__ = "spaces"
    __table_args__ = (UniqueConstraint("chat_id", name="uq_spaces_chat_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("owners.id", ondelete="CASCADE"), index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kind: Mapped[str] = mapped_column(String(32), default="group")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    owner: Mapped["Owner"] = relationship()

class Member(Base):
    __tablename__ = "members"
    __table_args__ = (UniqueConstraint("space_id", "telegram_id", name="uq_member_space_user"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    space_id: Mapped[int] = mapped_column(ForeignKey("spaces.id", ondelete="CASCADE"), index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), default="")
    last_name: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), default="member")
    warnings: Mapped[int] = mapped_column(Integer, default=0)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class EventLog(Base):
    __tablename__ = "event_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("owners.id", ondelete="SET NULL"), nullable=True, index=True)
    space_id: Mapped[int | None] = mapped_column(ForeignKey("spaces.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    target_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
