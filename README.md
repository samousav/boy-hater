# 💅 Boy-Hater Bot 🎀

> "AI is going to solve world peace and cure diseases!"
> Meanwhile, this code: Using LLMs to judge how creatively you can insult men on Telegram.

## 📖 The Lore

This chronically online masterpiece exists for one reason only: my friend **Mehraban** ([@mallaban on Telegram](https://t.me/mallaban)) woke up, chose violence, and explicitly told me to build a bot that rewards people for roasting guys. I was told to let her cook, so here we are. It is literally a gamified toxicity engine. You're welcome.

## ✨ Unhinged Features

* **AI-Powered Vibe Check:** Forwards your message through a massive AI cascade (DeepSeek, Qwen, Gemini, and Groq's Llama 3.3) to grade your roast from 5 to 20 points.
* **Anti-Cringe Mechanism:** If you use boomer curses or low-effort insults, the AI will literally roast *you* in heavy Persian street slang for having the creativity of algae.
* **Toxic Leaderboards:** Tracks the top 10 haters in your specific chat, plus a `/grouptop` global leaderboard tracking the most violently toxic groups across the database.
* **Admin Megaphone:** A `/broadcast` function built with flood-control bypasses to drop text, stickers, or images into 150+ groups simultaneously.

## 🛠️ Setup (For the Chronically Online)

If you actually want to host this menace to society yourself, open your terminal and do this:

1. Clone this absolute acid of a repo:
```bash
git clone https://github.com/samousav/boy-hater.git
cd boy-hater

```


2. Create a `.env` file because hardcoding API keys is smooth-brain behavior:
```env
TOKEN=your_telegram_bot_token
ADMIN=your_telegram_id
GEMINI_KEY=your_gemini_key
GROQ_KEY=your_groq_key
XKIRO_KEY=your_xkiro_key

```


3. Install the dependencies and spin it up:
```bash
pip install python-telegram-bot openai sqlalchemy python-dotenv
python main.py

```



---

*Disclaimer: I take zero legal or moral responsibility for the absolute destruction of male egos in your group chats. Touch grass.*
