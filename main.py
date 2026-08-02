import os
import logging
import re
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ChatMemberHandler, filters, ContextTypes
from telegram.constants import ChatMemberStatus

# .env फाइल से वेरिएबल्स लोड करें
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
# ओनर आईडी को स्ट्रिंग से इंटीजर (int) में बदलें
OWNER_ID = int(os.getenv("OWNER_ID")) if os.getenv("OWNER_ID") else None

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

RIDDLES = [
    {
        "question": "एक राजा की अनोखी रानी, दुम के रास्ते पीती पानी। बताओ क्या?",
        "hint": "यह अंधेरे को दूर भगाता है और दिवाली पर जलाया जाता है।",
        "answers": ["दीपक", "दिया", "दीया", "deepak", "diya", "deeyak", "lamp"]
    },
    {
        "question": "हरी थी मन भरी थी, लाख मोती जड़ी थी, राजा जी के बाग में दुशाला ओढ़े खड़ी थी। बताओ क्या?",
        "hint": "इसे मक्का (Corn) भी कहते हैं और सेक कर खाया जाता है।",
        "answers": ["भुट्टा", "मक्का", "मकई", "bhutta", "makka", "makai", "corn"]
    }
]

game_state = {}

# बॉट को ग्रुप में जोड़ने पर स्वागत संदेश
async def welcome_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if result.new_chat_member.user.id == context.bot.id:
        if result.new_chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
            chat_id = result.chat.id
            group_name = result.chat.title
            
            welcome_text = (
                f"🤖 *पहेली गेम बॉट में आपका स्वागत है!*\n\n"
                f"नमस्ते *{group_name}* के सदस्यों! मैं इस ग्रुप में आप सभी के मनोरंजन के लिए आ गया हूँ।\n\n"
                f"🎮 *गेम शुरू करने के लिए:* `/paheli` टाइप करें।\n"
                f"📊 *लीडरबोर्ड देखने के लिए:* `/score` टाइप करें।"
            )
            await context.bot.send_message(chat_id=chat_id, text=welcome_text, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 स्वागत है पहेली बॉट में!\n\n"
        "🎮 शुरू करने के लिए ग्रुप में: `/paheli` लिखें।\n"
        "📊 स्कोर देखने के लिए: `/score` लिखें।"
    )

# 👑 ओनर के लिए स्पेशल कमांड (सिर्फ एडमिन/ओनर पैनल के लिए)
async def owner_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # चेक करें कि कमांड भेजने वाला ही असली ओनर है या नहीं
    if user_id == OWNER_ID:
        await update.message.reply_text("😎 *नमस्ते बॉस!* आप बॉट के मुख्य डेवलपर हैं। आप पूरी तरह सुरक्षित हैं।", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ *अस्वीकृत:* यह कमांड केवल बॉट के मालिक (Owner) के लिए है।")

async def ask_paheli(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if chat_id not in game_state:
        game_state[chat_id] = {"riddle_index": 0, "scores": {}, "active": True}
    else:
        game_state[chat_id]["riddle_index"] = (game_state[chat_id]["riddle_index"] + 1) % len(RIDDLES)
        game_state[chat_id]["active"] = True
        
    current_index = game_state[chat_id]["riddle_index"]
    riddle = RIDDLES[current_index]
    
    text = f"🎯 *नई पहेली:* \n\n\"{riddle['question']}\"\n\n💡 *हिंट:* {riddle['hint']}\n\nजवाब चैट में सामान्य रूप से लिखें!"
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")

async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if chat_id not in game_state or not game_state[chat_id]["active"]:
        return
        
    user_msg = update.message.text.strip().lower()
    user = update.message.from_user
    
    current_index = game_state[chat_id]["riddle_index"]
    allowed_answers = RIDDLES[current_index]["answers"]
    
    is_correct = False
    for ans in allowed_answers:
        ans_clean = ans.strip().lower()
        if re.search(r'\b' + re.escape(ans_clean) + r'\b', user_msg) or ans_clean in user_msg:
            is_correct = True
            break
            
    if is_correct:
        game_state[chat_id]["active"] = False
        scores = game_state[chat_id]["scores"]
        scores[user.id] = scores.get(user.id, 0) + 10
        
        main_answer = allowed_answers[0]
        
        reply = f"🎉 *बिल्कुल सही जवाब* [{user.first_name}](tg://user?id={user.id})!\n\n" \
                f"सही उत्तर था: *{main_answer}*\n" \
                f"💰 आपको मिलते हैं *10ポイント (पॉइंट्स)*।\n\n" \
                f"अगली पहेली के लिए फिर से `/paheli` टाइप करें।"
                
        await update.message.reply_text(reply, parse_mode="Markdown")

async def show_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in game_state or not game_state[chat_id]["scores"]:
        await update.message.reply_text("📉 अभी तक किसी का खाता नहीं खुला है!")
        return
        
    scores = game_state[chat_id]["scores"]
    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    
    scoreboard_text = "🏆 *पहेली लीडरबोर्ड:* \n\n"
    for i, (user_id, score) in enumerate(sorted_scores, 1):
        scoreboard_text += f"{i}. यूजर (ID: {user_id}): *{score} PTS*\n"
        
    await update.message.reply_text(scoreboard_text, parse_mode="Markdown")

def main():
    # सुरक्षा जांच
    if not TOKEN:
        print("❌ एरर: .env फाइल में BOT_TOKEN नहीं मिला!")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(ChatMemberHandler(welcome_to_group, ChatMemberHandler.MY_CHAT_MEMBER))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("paheli", ask_paheli))
    app.add_handler(CommandHandler("score", show_score))
    app.add_handler(CommandHandler("owner", owner_panel)) # 🆕 ओनर चेक कमांड
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer))

    print("बॉट पर्यावरण वेरिएबल्स (.env) के साथ चालू है...")
    app.run_polling()

if __name__ == '__main__':
    main()
