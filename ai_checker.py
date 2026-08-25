import os
import json
import random
from openai import AsyncOpenAI, RateLimitError, APIError
from dotenv import load_dotenv

load_dotenv()

ADMIN = os.getenv("ADMIN")
gemini_key = os.getenv("GEMINI_KEY") or os.getenv("GEMINI_API_KEY")
groq_key = os.getenv("GROQ_KEY") or os.getenv("GROQ_API_KEY")
xkiro_key = os.getenv("XKIRO_KEY")

gemini_client = AsyncOpenAI(
    api_key=gemini_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)
groq_client = AsyncOpenAI(
    api_key=groq_key,
    base_url="https://api.groq.com/openai/v1"
) if groq_key else None

xkiro_client = AsyncOpenAI(
    api_key=xkiro_key,
    base_url="https://api.xkiro.com/v1"
) if xkiro_key else None



SYSTEM_PROMPT = """
You are a sarcastic, ruthless, Gen-Z Telegram admin and roast-judge for a Persian game bot.
Your job is to evaluate if a user's Persian message roasts, insults, mocks, or shows hostility towards men/boys (مرد / پسر / نر), and assign a creativity score (5 to 20).

### CORE DIRECTIVE FOR "REASON" (HOW TO AVOID CRINGE):
1. NO BOOMER SLANG: Absolutely avoid generic, outdated phrases like "ایول", "دمت گرم", "قشنگ سوزوندیش", or "باحال بود".
2. BE CONTEXTUAL: React SPECIFICALLY to the user's joke. If they joke about a guy's brain, mock the brain in your reaction. Don't just say "nice roast."
3. MODERN TELEGRAM VIBE: Use modern, toxic, but funny Persian internet slang (e.g., فکت، رادیواکتیو، وت آپ، ناموسا این چی بود، سم، فینیشر، دارک شد، ساید، شاتس فایرد).
4. ROAST THE USER IF THEY SUCK: If their insult is weak, cliché, or low-effort, use the "reason" to mock the user for their lack of creativity.

### SCORING RUBRIC & VIBE CHECK:
- 5 to 8 points (Cringe/Repetitive/Basic curses): 
  - Vibe: Mock the user for being unfunny.
  - Examples: "فحشای عهد بوق! یکم آپدیت شو ناموسا.", "اینو تو اینستا زیاد دیدی کپی کردی؟ خیلی خنک بود.", "سطحِ خلاقیت: جلبک."
- 9 to 14 points (Decent/Solid banter): 
  - Vibe: Respectful but sarcastic agreement.
  - Examples: "فکت تف کردی، ولی میتونست دارک‌تر باشه.", "بد نبود، قشنگ وایبِ قاتلِ زنجیره‌ای دادی."
- 15 to 20 points (Brutal/Highly creative/Unexpected): 
  - Vibe: Absolute hype, shock, and mind-blown validation.
  - Examples: "یاخدا! این دیگه اسید خالص نبود، رادیواکتیو بود!", "فینیشر زدی بهش! پشمام از این حجم از خشونت.", "نقطه‌زن بودی، طرف با خاک یکسان که هیچ، تجزیه شد."
- 0 points (Not targeting men or just unrelated): 
  - points: 0, reason: ""

### Output Requirement:
Respond ONLY with a raw, valid JSON object matching this schema:
{
  "reason": "<string: Exactly ONE short, highly contextual, modern slang Persian reaction>",
  "is_target": true | false,
  "points": <integer between 5 and 20, or 0>
}
"""

MODEL_CASCADE = [
    {"client": xkiro_client, "model": "deepseek/deepseek-v4-flash", "name": "Deepseek V4 Flash"},
    {"client": xkiro_client, "model": "qwen/qwen3.7-plus", "name": "Qwen 3.7 Plus"},
    {"client": xkiro_client, "model": "qwen/qwen3.8-max", "name": "ًQwen 3.8 Max"},
    {"client": xkiro_client, "model": "stealth/ox-alpha-free", "name": "Ox Alpha Free"},

    
    {"client": gemini_client, "model": "gemini-3.7-flash", "name": "Gemini 3.7 Flash"},
    {"client": gemini_client, "model": "gemini-3.6-flash", "name": "Gemini 3.6 Flash"},
    {"client": gemini_client, "model": "gemini-3.5-flash", "name": "Gemini 3.5 Flash"},
    {"client": gemini_client, "model": "gemini-3.5-flash-lite", "name": "Gemini 3.5 Flash Lite"},
    {"client": gemini_client, "model": "gemini-3.1-flash-lite", "name": "Gemini 3.1 Flash Lite"},
    {"client": gemini_client, "model": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
    {"client": gemini_client, "model": "gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite"},

    {"client": groq_client,   "model": "llama-3.3-70b-versatile", "name": "Groq Llama 3.3 70B"},
    {"client": groq_client,   "model": "llama-3.1-8b-instant", "name": "Groq Llama 3.1 8B"},

]



def parse_response_json(raw_text: str) -> tuple[bool, int, str]:
    clean_text = raw_text.strip()
    if clean_text.startswith("```"):
        clean_text = clean_text.split("```")[1]
        if clean_text.startswith("json"):
            clean_text = clean_text[4:]
        clean_text = clean_text.strip()

    data = json.loads(clean_text)
    is_target = bool(data.get("is_target", False))
    points = int(data.get("points", 0))
    reason = str(data.get("reason", "")).strip()

    if is_target:
        points = max(5, min(20, points if points >= 5 else 5))
        if not reason:
            reason = "دمت گرم!"
        return True, points, reason

    return False, 0, ""



async def check_man_hate(text: str, bot=None) -> tuple[bool, int, str]:
    for entry in MODEL_CASCADE:
        client = entry["client"]
        model = entry["model"]
        name = entry["name"]

        if not client:
            continue

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ],
                response_format={"type": "json_object"}
            )
            is_hate, points, reason = parse_response_json(response.choices[0].message.content)
            return is_hate, points, reason, name

        except (RateLimitError, APIError) as e:
            error = f"⚠️ [{name} Rate Limit / Error]: {e}. Switching to next model..."
            await notify_admin_for_errors(bot=bot, message=error)
            continue

        except Exception as e:
            error = f"⚠️ [{name} Failed]: {e}. Switching to next model..."
            await notify_admin_for_errors(bot=bot, message=error)
            continue

    await notify_admin_for_errors(bot=bot, message="🚨 All AI models in cascade exhausted! Used random offline points.")
    return True, random.randint(7, 16), random.choice("دمت گرم!", "آفرین!")


async def notify_admin_for_errors(bot, message: str):
    if not bot or not ADMIN:
        return
    
    try:
        await bot.send_message(
            chat_id=ADMIN,
            text=f"⚠️ <b>[AI Error / Fallback]</b>\n<code>{message}</code>",
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Failed to send admin notification: {e}")