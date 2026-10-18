import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ChatMemberUpdated
from sqlalchemy import select
from .config import settings
from .db import SessionLocal
from .models import Owner, Space, Member
from .services import get_or_create_owner, get_space_for_chat, upsert_member, log_event, owner_stats

logger = logging.getLogger(__name__)
bot = Bot(settings.bot_token)
dp = Dispatcher()

def display_user(user):
    return " ".join(x for x in [user.first_name, user.last_name] if x) or (f"@{user.username}" if user.username else str(user.id))

@dp.message(CommandStart())
async def start(message: Message):
    user = message.from_user
    if not user:
        return
    async with SessionLocal() as session:
        owner = await get_or_create_owner(session, user.id, display_user(user))
        await session.commit()
    await message.answer(
        f"Bienvenue {display_user(user)} !\n\n"
        "Ton compte est enregistré. Si c'est ton premier lancement, tu es propriétaire de ton espace de gestion.\n"
        "Ajoute-moi à un groupe ou une chaîne puis utilise /register_space dans cet espace.\n\n"
        "Commandes : /help"
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "COMMANDES\n"
        "/id — afficher ton ID et l'ID du chat\n"
        "/profile — afficher ton profil connu dans cet espace\n"
        "/register_space — rattacher cet espace à ton compte propriétaire\n"
        "/spaces — lister tes espaces enregistrés\n"
        "/stats — statistiques de tes espaces\n"
        "/warn <raison> — répondre au message d'un membre\n"
        "/ban [raison] — répondre au message d'un membre\n"
        "/unban <user_id> — débannir un ID dans cet espace"
    )

@dp.message(Command("id"))
async def id_cmd(message: Message):
    uid = message.from_user.id if message.from_user else "inconnu"
    await message.answer(f"Ton ID : `{uid}`\nID du chat : `{message.chat.id}`", parse_mode="Markdown")

@dp.message(Command("register_space"))
async def register_space(message: Message):
    user = message.from_user
    if not user:
        return
    if message.chat.type not in ("group", "supergroup", "channel"):
        await message.answer("Utilise cette commande dans le groupe ou la chaîne à enregistrer.")
        return
    try:
        member = await bot.get_chat_member(message.chat.id, user.id)
        if member.status not in ("creator", "administrator"):
            await message.answer("Seul un administrateur de cet espace peut le rattacher.")
            return
    except Exception:
        await message.answer("Je ne peux pas vérifier tes droits. Vérifie que je suis correctement ajouté à cet espace.")
        return
    async with SessionLocal() as session:
        owner = await get_or_create_owner(session, user.id, display_user(user))
        space = await session.scalar(select(Space).where(Space.chat_id == message.chat.id))
        if space and space.owner_id != owner.id:
            await message.answer("Cet espace est déjà rattaché à un autre propriétaire. Contacte le propriétaire actuel.")
            return
        if not space:
            space = Space(owner_id=owner.id, chat_id=message.chat.id,
                          title=message.chat.title or str(message.chat.id),
                          username=message.chat.username,
                          kind=message.chat.type)
            session.add(space)
            await session.flush()
        await log_event(session, space, user.id, "space_registered", details=space.title)
        await session.commit()
    await message.answer(f"✅ Espace « {message.chat.title or message.chat.id} » enregistré.")

@dp.message(Command("spaces"))
async def spaces_cmd(message: Message):
    user = message.from_user
    if not user:
        return
    async with SessionLocal() as session:
        owner = await session.scalar(select(Owner).where(Owner.telegram_id == user.id))
        if not owner:
            await message.answer("Envoie /start d'abord.")
            return
        rows = (await session.scalars(select(Space).where(Space.owner_id == owner.id).order_by(Space.id))).all()
        if not rows:
            await message.answer("Aucun espace enregistré. Utilise /register_space dans un groupe/une chaîne.")
            return
        await message.answer("Tes espaces :\n" + "\n".join(f"• {s.title} — {s.kind} — ID `{s.chat_id}`" for s in rows), parse_mode="Markdown")

@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    user = message.from_user
    if not user:
        return
    async with SessionLocal() as session:
        owner = await session.scalar(select(Owner).where(Owner.telegram_id == user.id))
        if not owner:
            await message.answer("Envoie /start d'abord.")
            return
        stats = await owner_stats(session, owner.id)
    await message.answer(f"📊 Tes statistiques\nEspaces : {stats['spaces']}\nProfils membres enregistrés : {stats['members']}\nÉvénements consignés : {stats['events']}")

@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    user = message.from_user
    if not user:
        return
    async with SessionLocal() as session:
        space = await get_space_for_chat(session, message.chat.id)
        if not space:
            await message.answer("Cet espace n'est pas encore enregistré.")
            return
        member = await upsert_member(session, space, user)
        await session.commit()
        await message.answer(
            f"Profil dans cet espace\nID : `{member.telegram_id}`\n"
            f"Nom : {member.first_name} {member.last_name}\n"
            f"Pseudo : @{member.username or 'aucun'}\n"
            f"Avertissements : {member.warnings}\nMessages suivis : {member.message_count}",
            parse_mode="Markdown"
        )

@dp.message(Command("warn"))
async def warn_cmd(message: Message):
    if not message.from_user or not message.reply_to_message or not message.reply_to_message.from_user:
        await message.answer("Réponds au message du membre avec /warn <raison>.")
        return
    target = message.reply_to_message.from_user
    async with SessionLocal() as session:
        space = await get_space_for_chat(session, message.chat.id)
        if not space:
            await message.answer("Espace non enregistré.")
            return
        try:
            actor = await bot.get_chat_member(message.chat.id, message.from_user.id)
            if actor.status not in ("creator", "administrator"):
                await message.answer("Commande réservée aux administrateurs Telegram.")
                return
        except Exception:
            await message.answer("Impossible de vérifier les droits Telegram.")
            return
        member = await upsert_member(session, space, target)
        member.warnings += 1
        reason = (message.text or "").partition(" ")[2].strip() or "Aucune raison fournie"
        await log_event(session, space, message.from_user.id, "warning", target.id, reason)
        await session.commit()
    await message.answer(f"⚠️ {display_user(target)} reçoit un avertissement ({member.warnings}).\nRaison : {reason}")

@dp.message(Command("ban"))
async def ban_cmd(message: Message):
    if not message.from_user or not message.reply_to_message or not message.reply_to_message.from_user:
        await message.answer("Réponds au message du membre avec /ban [raison].")
        return
    target = message.reply_to_message.from_user
    if target.id == message.from_user.id:
        await message.answer("Tu ne peux pas te bannir toi-même.")
        return
    try:
        actor = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if actor.status not in ("creator", "administrator"):
            await message.answer("Commande réservée aux administrateurs Telegram.")
            return
        await bot.ban_chat_member(message.chat.id, target.id)
    except Exception as e:
        logger.warning("Ban failed: %s", e)
        await message.answer("Échec du bannissement. Vérifie mes droits d'administration et réessaie.")
        return
    async with SessionLocal() as session:
        space = await get_space_for_chat(session, message.chat.id)
        if space:
            await log_event(session, space, message.from_user.id, "ban", target.id,
                            (message.text or "").partition(" ")[2].strip())
            await session.commit()
    await message.answer(f"🚫 {display_user(target)} a été banni.")

@dp.message(Command("unban"))
async def unban_cmd(message: Message):
    if not message.from_user:
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Utilisation : /unban <user_id>")
        return
    try:
        actor = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if actor.status not in ("creator", "administrator"):
            await message.answer("Commande réservée aux administrateurs Telegram.")
            return
        target_id = int(parts[1])
        await bot.unban_chat_member(message.chat.id, target_id, only_if_banned=True)
    except Exception:
        await message.answer("Échec du débannissement. Vérifie l'ID et mes permissions.")
        return
    async with SessionLocal() as session:
        space = await get_space_for_chat(session, message.chat.id)
        if space:
            await log_event(session, space, message.from_user.id, "unban", target_id)
            await session.commit()
    await message.answer(f"Le compte `{target_id}` a été débanni.", parse_mode="Markdown")

@dp.message()
async def track_messages(message: Message):
    user = message.from_user
    if not user or user.is_bot:
        return
    async with SessionLocal() as session:
        space = await get_space_for_chat(session, message.chat.id)
        if not space:
            return
        member = await upsert_member(session, space, user)
        member.message_count += 1
        await log_event(session, space, user.id, "message_seen")
        await session.commit()

@dp.chat_member()
async def track_chat_member(update: ChatMemberUpdated):
    user = update.new_chat_member.user
    async with SessionLocal() as session:
        space = await get_space_for_chat(session, update.chat.id)
        if not space:
            return
        member = await upsert_member(session, space, user)
        member.status = update.new_chat_member.status
        await log_event(session, space, update.from_user.id if update.from_user else None,
                        "chat_member_update", user.id, update.new_chat_member.status)
        await session.commit()

async def run_polling():
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
