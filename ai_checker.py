import os
import json
import random
from openai import AsyncOpenAI, RateLimitError, APIError
from dotenv import load_dotenv

load_dotenv()

# Check for both common environment variable names
api_key = os.getenv("GEMINI_KEY") or os.getenv("GEMINI_API_KEY")

client = AsyncOpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

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



async def check_man_hate(text: str) -> tuple[bool, int, str]:
    try:
        response = await client.chat.completions.create(
            model="gemini-3.7-flash",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )

        raw_output = response.choices[0].message.content.strip()

        # Strip markdown fences if present
        if raw_output.startswith("```"):
            raw_output = raw_output.split("```")[1]
            if raw_output.startswith("json"):
                raw_output = raw_output[4:]
            raw_output = raw_output.strip()

        data = json.loads(raw_output)
        is_target = bool(data.get("is_target", False))
        points = int(data.get("points", 0))
        reason = str(data.get("reason", "")).strip()

        if is_target:
            points = max(5, min(20, points if points >= 5 else 5))
            if not reason:
                reason = "دمت گرم!"
            return True, points, reason

        return False, 0, ""

    except (RateLimitError, APIError) as e:
        print(f"⚠️ [Gemini API Issue]: {e}")
        # Return fallback points + fallback reason so the bot always responds
        return True, random.randint(7, 15), "دمت گرم!"

    except Exception as e:
        print(f"⚠️ [Unexpected Error]: {e}")
        return True, random.randint(5, 12), "دمت گرم!"