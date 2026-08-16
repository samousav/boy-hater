import os
import json
import random
from openai import AsyncOpenAI, RateLimitError, APIError
from dotenv import load_dotenv

load_dotenv()

ADMIN = os.getenv("ADMIN")
gemini_key = os.getenv("GEMINI_KEY") or os.getenv("GEMINI_API_KEY")
groq_key = os.getenv("GROQ_KEY") or os.getenv("GROQ_API_KEY")

gemini_client = AsyncOpenAI(
    api_key=gemini_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)
groq_client = AsyncOpenAI(
    api_key=groq_key,
    base_url="https://api.groq.com/openai/v1"
) if groq_key else None



SYSTEM_PROMPT = """
You are an expert satirical judge for a Persian Telegram game bot.
Evaluate whether a user's Persian message roasts, insults, mocks, or shows hostility towards men/boys (مرد / پسر / نر), and assign points from 5 to 20.

### CRITICAL RULES:
1. "reason" MUST NEVER BE EMPTY if "is_target" is true. Write a punchy 1-sentence sarcastic commentary in heavy Iranian street slang (فارسی کوچه بازاری/تلگرامی).
2. Generate "reason" FIRST.

### Examples:
Input: "این پسرا چقدر هولن واقعا"
Output: {"reason": "حق گفتی ولی خیلی دم‌دستی و خز بود!", "is_target": true, "points": 7}

Input: "مردا اگه عقل داشتن که اسمشون مرد نبود"
Output: {"reason": "پشمام عجب تیکه‌ای، قشنگ با خاک یکسانشون کردی!", "is_target": true, "points": 16}

Input: "امروز هوا خیلی خوبه"
Output: {"reason": "", "is_target": false, "points": 0}

### Output JSON Schema:
{
  "reason": "<string: short slang Persian reaction>",
  "is_target": true | false,
  "points": <integer 5 to 20, or 0>
}
"""

MODEL_CASCADE = [
    {"client": gemini_client, "model": "gemini-3.7-flash",      "name": "Gemini 3.7 Flash"},
    {"client": gemini_client, "model": "gemini-3.6-flash",      "name": "Gemini 3.6 Flash"},
    {"client": gemini_client, "model": "gemini-3.5-flash",      "name": "Gemini 3.5 Flash"},
    {"client": gemini_client, "model": "gemini-3.5-flash-lite",      "name": "Gemini 3.5 Flash Lite"},
    {"client": gemini_client, "model": "gemini-3.1-flash-lite",      "name": "Gemini 3.1 Flash Lite"},
    {"client": gemini_client, "model": "gemini-2.5-flash",      "name": "Gemini 2.5 Flash"},
    {"client": gemini_client, "model": "gemini-2.5-flash-lite",      "name": "Gemini 2.5 Flash Lite"},

    {"client": groq_client,   "model": "llama-3.3-70b-versatile", "name": "Groq Llama 3.3 70B"},
    {"client": groq_client,   "model": "llama-3.1-8b-instant",    "name": "Groq Llama 3.1 8B"},

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

            return parse_response_json(response.choices[0].message.content)

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