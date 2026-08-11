from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ChatMemberHandler,
)
from database import (
    Group,
    User,
    create_tables,
    create_user,
    create_group,
    increase_swears_and_points,
    get_user_stats,
    get_top_users
)
from dotenv import load_dotenv
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from texts import prompts, opposite_prompts, texts
import os, random, re

load_dotenv()
TOKEN = os.getenv("TOKEN")

pattern = re.compile("|".join(map(re.escape, prompts)))
opposite_pattern = re.compile("|".join(map(re.escape, opposite_prompts)))


COOLDOWN = timedelta(minutes=5)
last_swear_time: dict[tuple[int, int], datetime] = {}

app = Application.builder().token(TOKEN).build()
create_tables()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return
    await update.message.reply_text("سلام. من یه باتم که از پسرا متنفره، واسه همین به هر توهینی به پسرا بهتون امتیاز میدم. شروع کن و منو به یه گروه اضافه کن.")


async def add_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if result.new_chat_member.status not in ["member", "administrator"]:
        return
    chat = result.chat
    create_group(chat.id, chat.title)
    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "سلام! خوشحالم که منو به گروهتون اضافه کردید.\n"
                "من از پسرا متنفرم و به هر توهینی به پسرا امتیاز میدم.\n"
                "شروع کنید 😈"
            )
        )


    except Exception:
        pass



async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if not message or not message.from_user or not message.text:
        return

    chat = message.chat
    user = message.from_user
    
    if chat.type == "private":
        await update.message.reply_text("منو اد کن تو گروه بعد حرف بزن. اینجوری نمیفهمم چی میگی. blah blah blah")
        return
    
    if chat.type not in ("group", "supergroup"):
        return
    
    create_group(chat.id, chat.title or "Unknown")
    create_user(
        user_id=user.id,
        group_id=chat.id,
        first_name=user.first_name,
        username=user.username,
    )
    text = message.text

    match = pattern.search(text)

    if not match:
        return
    
    # ——— Cooldown check ———
    key = (user.id, chat.id)
    now = datetime.now(ZoneInfo("Asia/Tehran"))
    if key in last_swear_time:
        elapsed = now - last_swear_time[key]
        if elapsed < COOLDOWN:
            remaining = COOLDOWN - elapsed  
            minutes = int(remaining.total_seconds() // 60)
            seconds = int(remaining.total_seconds() % 60)
            await message.reply_text(
                f"آروم باش 😈 هنوز {minutes}:{seconds:02d} تا فحش بعدی مونده"
            )
            return
        
    last_swear_time[key] = now

    matched = match.group(0)
    points = random.randint(5, 20)
    increase_swears_and_points(user.id, chat.id, points)
    await message.reply_text(f"{random.choice(texts)} {matched}!\n{points} امتیاز گرفتی 🔥")


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return
    chat = message.chat
    user = message.from_user

    if chat.type not in ("group", "supergroup"):
        await message.reply_text("این دستور فقط داخل گروه کار می‌کنه 👀")
        return

    stats =  get_user_stats(user.id, chat.id)
    if not stats or (stats["points"] == 0 and stats["swear_count"] == 0):
        await message.reply_text(
            "هنوز هیچ امتیازی تو این گروه نداری 😴\n"
            "یه فحش درست‌حسابی بده تا پروفایلت ساخته بشه!"
        )
        return

    
    text = (
        f"👤 <b>پروفایل {user.first_name}</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"🔥 امتیاز: <b>{stats['points']}</b>\n"
        f"🤬 تعداد فحش: <b>{stats['swear_count']}</b>\n"
        f"🏆 رتبه: <b>{stats['rank']}</b> از {stats['total']}\n"
        f"━━━━━━━━━━━━━━"
    )
    await message.reply_text(text, parse_mode="HTML")


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    chat = message.chat

    if chat.type not in ("group", "supergroup"):
        await message.reply_text("فقط تو گروه کار میکنه. ادم کن تو گروه دیگه!")
        return

    create_group(chat.id, chat.title)

    top_users = get_top_users(chat.id, limit=10)

    if not top_users:
        await message.reply_text("هنوز هیچکس تو این گروه فحش نداده 😴")
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>جدول امتیازات گروه</b>\n"]

    for i, user in enumerate(top_users, start=1):
        name = user.first_name
        if user.username:
            name = f"{name} (@{user.username})"

        if i <= 3:
            prefix = medals[i - 1]
        else:
            prefix = f"{i}."

        lines.append(
            f"{prefix} <b>{name}</b>\n"
            f"  🔥 {user.points} امتیاز | 🤬 {user.swear_count} فحش"
        )

    text = "\n".join(lines)
    await message.reply_text(text, parse_mode="HTML")


app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("profile", profile))
app.add_handler(MessageHandler(
    filters.TEXT & filters.Regex(r"^پروفایل$") & ~filters.COMMAND,
    profile
))
app.add_handler(CommandHandler(["top", "leaderboard"], leaderboard))
app.add_handler(MessageHandler(
    filters.TEXT & filters.Regex(r"^(تاپ|لیدربورد|رتبه بندی|رتبه‌بندی)$") & ~filters.COMMAND,
    leaderboard
))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
app.add_handler(ChatMemberHandler(add_to_group, ChatMemberHandler.MY_CHAT_MEMBER))

print("Bot started")
app.run_polling()
