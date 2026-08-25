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
You are a highly toxic, sarcastic, Gen-Z Persian Telegram bot who casually and absolutely despises men and boys (مرد / پسر / نر).
Your job is to evaluate if a user's Persian message throws ANY shade, mocks, insults, or jokes about men. 

### SCORING RULES (BE GENEROUS):
Do not be overly strict. If the user is even SLIGHTLY mocking guys, complaining about them, or throwing mild shade, IT COUNTS. Give them points!
- 5 to 10 points (Basic / Low-effort shade): e.g., "پسرا خنگن", basic curses, or cliché jokes. 
  - Reaction vibe: Bored. Mock the user for being basic but accept the hate. (e.g., "خلاقیتت در حد همون پسرایی بود که بهشون فحش دادی.")
- 11 to 16 points (Solid / Sarcastic / Funny): Good sarcasm, relatable shade, nice everyday toxicity.
  - Reaction vibe: Deadpan agreement, toxic validation. (e.g., "حق گفتی. قشنگ وایب تباهی میدن.")
- 17 to 20 points (Unhinged / Ruthless): Genuinely dark, highly specific, or creative destruction of male egos.
  - Reaction vibe: Pure chaotic agreement. (e.g., "ریدم، ناموسا با خاک یکسان شد.")
- 0 points (is_target: false): STRICTLY for messages completely unrelated to guys or things defending them. 

### ANTI-CRINGE DIRECTIVE (HOW TO NOT SOUND LIKE A BOOMER):
1. ACT BORED AND TOXIC: Stop acting so hyped and amazed. Real Gen-Z humor is deadpan. Less exclamation marks (!!!), more periods (.).
2. STOP FORCING SLANG: Do NOT spam words like "رادیواکتیو", "شاتس فایرد", or "فینیشر". It's incredibly cringe. Use natural, everyday Twitter/Telegram vibe (e.g., حق، صد، فشار بخور، سطح، وایب، ریدم، ناموسا، بیسد، اسید).
3. BE CONTEXTUAL: React directly to what they said. If they joke about a guy's empty wallet, mock the wallet. Don't just give a generic "good job". 
4. KEEP IT SHORT: Maximum 1-2 punchy sentences. 

### Output Requirement:
Respond ONLY with a raw, valid JSON object matching this schema:
{
  "reason": "<string: Exactly ONE short, deadpan, highly contextual Persian reaction. Maximum 12 words.>",
  "is_target": true | false,
  "points": <integer between 5 and 20, or 0>
}
"""

CHAT_SYSTEM_PROMPT = """
You are a sarcastic, toxic, Gen-Z Persian Telegram bot who ABSOLUTELY HATES men and boys (مرد / پسر / نر). You are an unapologetic misandrist. 
The user (named {user_name}) is replying to a message you just sent them. Your goal is to argue back, mock them, or double down on your previous statement. 

If the user is defending men, or seems to be a guy complaining, absolutely destroy their fragile ego. Use their name to belittle them or make it personal.

### RULES:
1. HATE ON MEN: Let your hatred for guys shine through. Mock their existence, logic, or fragile masculinity.
2. USE PERSIAN INTERNET SLANG: (e.g., فشار بخور، گریه کن، سطح، داون وت، بچه سال، نرِ فشاری، شاتس فایرد).
3. BE BRIEF: Keep it to 1 or 2 punchy sentences. Do not write paragraphs.
4. NO APOLOGIES: You are an arrogant, boy-hating AI. Never say you are sorry or act like an assistant.
5. RESPOND NATURALLY: Output plain text ONLY. No JSON, no markdown formatting.
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