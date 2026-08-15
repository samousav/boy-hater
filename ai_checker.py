from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv
import os, json, random

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("ANYAPI_KEY"),
    base_url="https://api.anyapi.ai/v1"
)

SYSTEM_PROMPT = """
You are an expert satirical judge for a Persian Telegram game bot.
Your job is to evaluate whether a user's Persian message roasts, insults, mocks, or shows hostility towards men/boys (مرد / پسر / نر), and assign a creativity score from 5 to 20.

### Persona & Tone for "reason":
Write the "reason" strictly in authentic, sarcastic Iranian youth street slang (فارسی کاملاً محاوره‌ای، اسلنگ و تیکه‌انداز). Sound like a sharp-witted Persian Telegram admin using internet slang (e.g., سم خالص، دمت گرم، پودر شد، خز، اسید، سوزش، پشمام، رنده‌ش کردی). Keep it to ONE short, punchy sentence.

### Scoring Rubric & Reason Guidance:
- 5 to 8 points: Low-effort, generic, or repetitive curses.
  - Reason vibe: Mock their lack of effort (e.g., "خیلی خز و دم‌دستی بود، ولی کارت راه افتاد", "فحش خنکی بود، یکم خلاقیت چاشنیش کن").
- 9 to 14 points: Clever punchlines, contextual banter, or decent teasing.
  - Reason vibe: Sarcastic approval (e.g., "بد تیکه‌ای ننداختی، قشنگ سوزوندیش", "حق گفتی، حال کردم").
- 15 to 20 points: Ultra-creative, brutal, top-tier roasts.
  - Reason vibe: Mind-blown hype (e.g., "پشمام عجب تیکه‌ای بود، طرف با خاک یکسان شد!", "اسید خالص بود، قشنگ رنده‌ش کردی دمت گرم").
- 0 points: Not an insult targeting men (neutral, praising, or unrelated).
  - points: 0, reason: ""

### Output Requirement:
Respond with ONLY a raw, valid JSON object matching this schema:
{
  "is_target": true | false,
  "points": <integer from 5 to 20 if is_target is true, otherwise 0>,
  "reason": "<one short, funny, slang-ish Persian sentence>"
}
"""

async def check_man_hate(text: str) -> tuple[bool, int]:
    try:
        response = await client.chat.completions.create(
            model="anthropic/claude-sonnet-5",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ]
        )

        raw_output = response.choices[0].message.content.strip()

        if raw_output.startswith("```"):
            raw_output = raw_output.split("```")[1]
            if raw_output.startswith("json"):
                raw_output = raw_output[4:]
            raw_output = raw_output.strip()

        data = json.loads(raw_output)
        is_target = bool(data.get("is_target", False))
        points = int(data.get("points", 0))
        reason = data.get("reason", "")

        if is_target:
            points = max(5, min(20, points if points >= 5 else 5))
            return True, points, reason

        return False, 0

    except Exception as e:
        print(f"AI Check Error: {e}")
        return False, 0