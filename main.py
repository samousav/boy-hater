from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ChatMemberHandler,
    ConversationHandler,
)
from telegram.error import RetryAfter, Forbidden, BadRequest
from database import (
    Group,
    User,
    create_tables,
    create_user,
    create_group,
    increase_swears_and_points,
    get_user_stats,
    get_top_users,
    get_all_groups,
)
from dotenv import load_dotenv
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from texts import prompts, texts
from ai_checker import check_man_hate, chat_with_user
import os, random, re, asyncio

load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN = os.getenv("ADMIN")

sorted_variants = sorted(prompts, key=len, reverse=True)

escaped_variants = [
    re.escape(word).replace(r"\ ", r"[\s\u200c]+").replace(r"\u200c", r"[\s\u200c]?")
    for word in sorted_variants
]

PATTERN = re.compile(
    rf"(?:^|[^\w\u200c])({'|'.join(escaped_variants)})(?:$|[^\w\u200c])", re.UNICODE
)


COOLDOWN = timedelta(minutes=4)
last_swear_time: dict[tuple[int, int], datetime] = {}

app = Application.builder().token(TOKEN).build()
create_tables()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return
    await update.message.reply_text(
        "سلام. من یه باتم که از پسرا متنفره، واسه همین به هر توهینی به پسرا بهتون امتیاز میدم. شروع کن و منو به یه گروه اضافه کن."
    )


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
            ),
        )
        await context.bot.send_message(
            chat_id=ADMIN,
            text=f"👤 <b>{result.from_user.first_name} Added the bot to group</b> \n{chat.title}",
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
        await update.message.reply_text(
            "منو اد کن تو گروه بعد حرف بزن. اینجوری نمیفهمم چی میگی. blah blah blah"
        )
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

    # ——— Chat with user ———
    is_reply_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user.id == context.bot.id
    )

    if is_reply_to_bot:
        bot_previous_text = message.reply_to_message.text or ""
        await context.bot.send_chat_action(chat_id=chat.id, action="typing")
        ai_reply, model_name = await chat_with_user(text, bot_previous_text, context.bot, user.first_name)
        await message.reply_text(ai_reply)
        print(f"💬 [Argument in {chat.title}] {user.first_name}: {text} -> Bot: {ai_reply}")
        return


    # ——— Matching check ———
    match = PATTERN.search(text)

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

    waiting_message = await message.reply_text("وایسا چک کنم...")
    await context.bot.send_chat_action(chat_id=chat.id, action="typing")
    is_hate, points, reason, model_name = await check_man_hate(text, user.first_name, bot=context.bot)
    if not is_hate:
        await waiting_message.edit_text("ای بابا. منتظر یه فحش آبدار بودما!")
        return

    last_swear_time[key] = now

    increase_swears_and_points(user.id, chat.id, points)
    reply_caption = (
        f"{random.choice(texts)} {text}!\n" f"🔥 <b>+{points} امتیاز گرفتی!</b>"
    )
    if reason:
        reply_caption += f"\n💡 <i>{reason}</i>"
    await waiting_message.edit_text(reply_caption, parse_mode="HTML")
    if ADMIN:
        await context.bot.send_message(
            chat_id=ADMIN,
            text=f"👤 <b>{user.first_name}</b> roasted in <b>{chat.title}</b> (+{points} pts)\nText: <code>{text}</code>\nUsed model: {model_name}",
            parse_mode="HTML",
        )


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return
    chat = message.chat
    user = message.from_user

    if chat.type not in ("group", "supergroup"):
        await message.reply_text("این دستور فقط داخل گروه کار می‌کنه 👀")
        return

    stats = get_user_stats(user.id, chat.id)
    if not stats or (stats["points"] == 0 and stats["swear_count"] == 0):
        await message.reply_text(
            "هنوز هیچ امتیازی تو این گروه نداری 😴\n"
            "یه فحش درست‌حسابی بده تا پروفایلت ساخته بشه!"
        )
        return

    text = (
        f"👤 <b>پروفایل {user.first_name}</b>\n"
        f"🔥 امتیاز: <b>{stats['points']}</b>\n"
        f"🤬 تعداد فحش: <b>{stats['swear_count']}</b>\n"
        f"🏆 رتبه: <b>{stats['rank']}</b> از {stats['total']}\n"
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


WAITING_FOR_MESSAGE = 1


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if str(user.id) != str(ADMIN):
        await update.message.reply_text("You ain't admin nigga")
        return ConversationHandler.END
    await update.message.reply_text(
        "📢 <b>حالت پیام همگانی فعال شد.</b>\n\n"
        "متن، عکس، ویدیو، استیکر یا هرچیزی که میخوای رو الان بفرست تا برای همه گروه‌ها کپی کنم.\n"
        "اگه پشیمون شدی /cancel رو بزن.",
        parse_mode="HTML",
    )
    return WAITING_FOR_MESSAGE


async def send_to_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    all_groups = get_all_groups()
    group_ids = [group.id for group in all_groups]

    total = len(group_ids)
    if total == 0:
        await message.reply_text("بات هنوز تو هیچ گروهی عضو نیست 🤷‍♂️")
        return ConversationHandler.END

    status_message = await message.reply_text(f"⏳ در حال ارسال به {total} گروه...")

    success_count = 0
    kicked_count = 0
    failed_count = 0

    for i, group_id in enumerate(group_ids, start=1):
        try:
            await context.bot.copy_message(
                chat_id=group_id,
                from_chat_id=message.chat_id,
                message_id=message.message_id,
            )
            success_count += 1

        except RetryAfter as e:
            # If Telegram throttles, wait the exact required seconds and retry
            print(f"Flood limit reached. Sleeping for {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            try:
                await context.bot.copy_message(
                    chat_id=group_id,
                    from_chat_id=message.chat_id,
                    message_id=message.message_id,
                )
                success_count += 1
            except Exception:
                failed_count += 1

        except (Forbidden, BadRequest) as e:
            # Bot was kicked, group was deleted, or bot has no send permissions
            print(f"Cannot send to group {group_id}: {e}")
            kicked_count += 1

        except Exception as e:
            print(f"Unexpected error sending to {group_id}: {e}")
            failed_count += 1

        # Small 50ms pause between messages (~20 msgs/sec, well within 30 msg/sec limit)
        await asyncio.sleep(0.05)

        # Update progress status every 30 groups so you know it's working
        if i % 30 == 0 or i == total:
            try:
                await status_message.edit_text(
                    f"⏳ در حال ارسال... ({i}/{total})\n"
                    f"✅ موفق: {success_count} | 🚫 کیک‌شده: {kicked_count}"
                )
            except Exception:
                pass

    await status_message.edit_text(
        f"✅ <b>ارسال همگانی تکمیل شد!</b>\n\n"
        f"👥 کل گروه‌ها: {total}\n"
        f"🎯 موفق: {success_count}\n"
        f"🚫 کیک شده/دسترسی محدود: {kicked_count}\n"
        f"❌ خطای متفرقه: {failed_count}",
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 ارسال همگانی لغو شد.")
    return ConversationHandler.END


async def global_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    # Fetch the exact same sorted groups
    all_groups = get_all_groups()

    if not all_groups:
        await message.reply_text("هنوز هیچ گروهی ثبت نشده 😴")
        return

    lines = ["🏆 <b>رتبه‌بندی سمی‌ترین گروه‌ها</b>\n"]
    medals = ["🥇", "🥈", "🥉"]

    # Grab only the top 10 groups
    for i, group in enumerate(all_groups[:10], start=1):
        # Format the medal or number
        prefix = medals[i - 1] if i <= 3 else f"{i}."

        lines.append(f"{prefix} <b>{group.title}</b>\n" f"  🔥 {group.total_points} امتیاز")

    text = "\n".join(lines)
    await message.reply_text(text, parse_mode="HTML")


broadcast_handler = ConversationHandler(
    entry_points=[CommandHandler("broadcast", broadcast)],
    states={
        WAITING_FOR_MESSAGE: [
            MessageHandler(filters.ALL & ~filters.COMMAND, send_to_all)
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_broadcast)],
)

app.add_handler(broadcast_handler)
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("profile", profile))
app.add_handler(
    MessageHandler(
        filters.TEXT & filters.Regex(r"^پروفایل$") & ~filters.COMMAND, profile
    )
)
app.add_handler(CommandHandler(["top", "leaderboard"], leaderboard))
app.add_handler(
    MessageHandler(
        filters.TEXT
        & filters.Regex(r"^(تاپ|لیدربورد|رتبه بندی|رتبه‌بندی)$")
        & ~filters.COMMAND,
        leaderboard,
    )
)
app.add_handler(CommandHandler(["grouptop", "topgroups"], global_leaderboard))
app.add_handler(
    MessageHandler(
        filters.TEXT
        & filters.Regex(
            r"^(تاپ گروه ها|تاپ گروه‌ها|رتبه بندی گروه ها|رتبه‌بندی گروه‌ها)$"
        )
        & ~filters.COMMAND,
        global_leaderboard,
    )
)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
app.add_handler(ChatMemberHandler(add_to_group, ChatMemberHandler.MY_CHAT_MEMBER))

print("Bot started")
app.run_polling()
