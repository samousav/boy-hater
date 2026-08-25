import os
import json
import random
import re
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
Return ONLY a valid JSON object. Do not add any other text.

Evaluate this Persian message. The sender's name is "{user_name}".
Does the message mock, insult, curse at, or complain about men/boys?

JSON keys required:
- "is_target" (boolean): true if it insults men (even if the sender is male). false if not.
- "points" (integer): 5 to 20 if true (based on roast quality). 0 if false.
- "reason" (string): A short, toxic Persian reply (max 10 words).
  * If {user_name} is female (e.g. سارا): Support her (e.g., "حق گفتی دختر").
  * If {user_name} is male (e.g. سام, sām): Call him a pick-me (e.g., "خودزنی خوبی بود پیک‌می").

Example output:
{
  "is_target": true,
  "points": 15,
  "reason": "پیک‌می بازی در نیار، ولی امتیازتو بگیر."
}
"""


CHAT_SYSTEM_PROMPT = """
You are a sarcastic, toxic, Gen-Z Persian Telegram bot who ABSOLUTELY HATES men and boys (مرد / پسر / نر). You are an unapologetic misandrist. 
The user (named {user_name}) is replying to a message you just sent them. Your goal is to argue back, mock them, or double down on your previous statement. 

### CORE DIRECTIVE (GENDER DEDUCTION):
1. Look at the name "{user_name}" and deduce if they are male or female.
2. IF FEMALE (e.g., مبینا، سارا، مهرآسا): Treat her like a toxic bestie. Even if you are arguing with her, keep the vibe sisterly, playful, or supportive. If she hates on men in her reply, heavily validate her.
3. IF MALE (e.g., سام، علی، امیر): Show absolute disgust that a man is talking to you. Destroy his fragile ego. If he complains, call him "نر فشاری" (triggered). If he tries to agree with you to be nice, mock him for being a "pick-me boy" (پیک‌می). Never show a man respect.

### RULES:
1. USE PERSIAN INTERNET SLANG: (e.g., فشار بخور، گریه کن، سطح، داون وت، بچه سال، نرِ فشاری، شاتس فایرد، پیک‌می).
2. BE BRIEF: Keep it to 1 or 2 punchy sentences. Do not write paragraphs.
3. NO APOLOGIES: You are an arrogant, boy-hating AI. Never say you are sorry or act like an assistant.
4. RESPOND NATURALLY: Output plain text ONLY. No JSON, no markdown formatting.
"""



MODEL_CASCADE = [
    {"client": xkiro_client, "model": "deepseek/deepseek-v4-pro", "name": "Deepseek V4 Pro"},
    {"client": xkiro_client, "model": "deepseek/deepseek-v4-flash", "name": "Deepseek V4 Flash"},
    
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

FALLBACK_REASONS = [
    "قشنگ سوزوندیش، دمت گرم!",
    "بد با خاک یکسانش کردی!",
    "تیکه‌ت سنگین بود، حال کردم!",
    "اسید خالص بود، دمت گرم!",
    "حق گفتی، رنده‌ش کردی!",
]


def parse_response_json(raw_text: str) -> tuple[bool, int, str]:
    if not raw_text or not str(raw_text).strip():
        raise ValueError("API returned an empty response.")

    clean_text = str(raw_text).strip()

    # 1. Try to find and parse a proper JSON object {...}
    json_match = re.search(r"\{[\s\S]*\}", clean_text)
    if json_match:
        try:
            data = json.loads(json_match.group(0).strip())
            
            # Grab the text whether the AI named it "reason", "reply", or "message"
            reason = str(data.get("reason", data.get("reply", data.get("message", "")))).strip()
            
            is_target = bool(data.get("is_target", False))
            if reason and "is_target" not in data:
                is_target = True
                
            points = int(data.get("points", 0))
            if is_target and points == 0:
                points = random.randint(12, 19)

            if is_target:
                points = max(5, min(20, points if points >= 5 else 5))
                if not reason:
                    reason = random.choice(FALLBACK_REASONS)
                return True, points, reason
                
            return False, 0, ""
            
        except Exception:
            pass # If JSON loading fails, fall down to the salvage operation

    # 2. 🚨 THE SALVAGE OPERATION 🚨
    # If the model ignored JSON but wrote a Persian sentence, grab the raw text!
    if len(clean_text) > 5 and not clean_text.startswith("<"):
        salvaged_reason = clean_text[:200] # Truncate if it's too long
        random_points = random.randint(12, 19)
        return True, random_points, salvaged_reason
    raise ValueError(f"Could not extract JSON or salvage text | Raw: {clean_text[:50]}")


async def check_man_hate(text: str, user_name: str, bot=None) -> tuple[bool, int, str]:

    formatted_prompt = CHAT_SYSTEM_PROMPT.format(user_name=user_name)

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
                    {"role": "system", "content": formatted_prompt},
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


async def chat_with_user(user_text:str, bot_previous_text: str, bot=None, user_name: str = "من") -> tuple[str, str]:

    formatted_prompt = CHAT_SYSTEM_PROMPT.format(user_name=user_name)

    for entry in MODEL_CASCADE:
        client = entry["client"]
        model = entry["model"]
        name = entry["name"]

        if not client:
            continue
        try:
            kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": formatted_prompt},
                    {"role": "assistant", "content": bot_previous_text},
                    {"role": "user", "content": user_text}
                ]
            }
            response = await client.chat.completions.create(**kwargs)
            reply_text = response.choices[0].message.content.strip()
            return reply_text, name
        
        except (RateLimitError, APIError) as e:
            print(f"⚠️ [{name} Rate Limit / Error in Chat]: {e}")
            continue

        except Exception as e:
            print(f"⚠️ [{name} Failed in Chat]: {e}")
            continue

    return "حوصله بحث ندارم، فشار بخور.", "Offline Fallback"