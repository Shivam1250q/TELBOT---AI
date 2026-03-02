import logging
import asyncio
from datetime import datetime
import urllib.request
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ChatAction, ParseMode
from groq import Groq
import qrcode
from fpdf import FPDF

# Import for Image Generation
from huggingface_hub import InferenceClient

# Import credentials
from config import BOT_TOKEN, GROQ_API_KEY, ADMIN_ID, HF_API_KEY

# Setup logging
logging.basicConfig(level=logging.INFO)

# Initialize Clients
client = Groq(api_key=GROQ_API_KEY)
image_client = InferenceClient(model="black-forest-labs/FLUX.1-schnell", token=HF_API_KEY)

# Databases (In-memory)
user_database = set()
image_usage_db = {} # Tracks daily image generation limits!

# ---------- AUTO-SETUP BOT MENU ----------
async def setup_commands(application):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Get help and usage instructions"),
        BotCommand("contact", "Contact the developer"),
        BotCommand("info", "Get your Telegram account info"),
        BotCommand("time", "Get current date and time"),
        BotCommand("weather", "Get current weather report"),
        BotCommand("qr", "Generate QR code from text or link"),
        BotCommand("short", "Shorten a long URL"),
        BotCommand("feedback", "Send feedback or suggestions")
    ]
    await application.bot.set_my_commands(commands)

# ---------- INTERACTIVE MENU KEYBOARD ----------
def get_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("💬 Ask AI Question", callback_data='ask_ai')],
        [InlineKeyboardButton("🔳 Generate QR Code", callback_data='qr')],
        [InlineKeyboardButton("🖼 Generate Image (AI)", callback_data='image')], 
        [InlineKeyboardButton("📄 AI PDF Generator", callback_data='pdf')],
        [InlineKeyboardButton("📱 Social Media Captions", callback_data='captions')],
        [InlineKeyboardButton("🎥 YouTube Video Ideas", callback_data='youtube')],
        [InlineKeyboardButton("💼 Resume Builder (PDF)", callback_data='resume')]
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------- SLASH COMMAND HANDLERS ----------

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 TELBOT AI MENU 🤖\n\nSelect a tool below or just chat with me normally!", 
        reply_markup=get_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_text = (
        "📞 Developer Contact:\n\n"
        "Made with ❤️ by Shivam 😈\n\n"
        "📧 Have queries, feedback, or business inquiries?\n"
        "Send an email to: shivammishra90448@gmail.com\n\n"
        "I will get back to you as soon as possible!"
    )
    await update.message.reply_text(contact_text, parse_mode=ParseMode.MARKDOWN)

async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    info = f"👤 Your Telegram Info:\n\n*Name:* {user.first_name}\n*Username:* @{user.username}\n*User ID:* {user.id}"
    await update.message.reply_text(info, parse_mode=ParseMode.MARKDOWN)

async def cmd_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await update.message.reply_text(f"🕒 Current Date & Time:\n`{now}`", parse_mode=ParseMode.MARKDOWN)

async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "weather"
    await update.message.reply_text("🌤 Please send the name of your city to get the weather:")

async def cmd_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "qr"
    await update.message.reply_text("🔳 Please send the text or link for your QR Code:", parse_mode=ParseMode.MARKDOWN)

async def cmd_short(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "short"
    await update.message.reply_text("🔗 Please send the long URL you want to shorten:")

async def cmd_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "feedback"
    await update.message.reply_text("📝 Please type your feedback or suggestion. It will be sent straight to the developer!")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) == str(ADMIN_ID):
        await update.message.reply_text(f"📊 TELBOT STATISTICS\n👥 Unique Users: {len(user_database)}", parse_mode=ParseMode.MARKDOWN)

# ---------- THE ULTIMATE START COMMAND ----------  
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_database.add(update.effective_user.id)
    chat_id = update.effective_chat.id
    
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    
    frames = [
        "🚀 Initializing TELBOT Core...",
        "⚡ Connecting to AI Neural Networks...",
        "🔒 Securing Encrypted Channels...",
        "🖼 Initializing Image Forge...",
        "✨ Systems 100% Operational!"
    ]
    
    msg = await update.message.reply_text(frames[0], parse_mode=ParseMode.MARKDOWN)
    
    for frame in frames[1:]:
        await asyncio.sleep(0.7) 
        await msg.edit_text(frame, parse_mode=ParseMode.MARKDOWN)
        
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif 12 <= hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"
        
    welcome_text = (
        f"👋 {greeting}, {update.effective_user.first_name}! \n\n"
        "Welcome to TELBOT AI 🤖 — Your ultimate all-in-one smart assistant.\n\n"
        "I can help you write code, generate professional images (2 per day limit), build resumes, create QR codes, and so much more.\n\n"
        "Let's create something fantastic! 👇"
    )
    
    await asyncio.sleep(0.5)
    await msg.edit_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
    await cmd_help(update, context) 

# ---------- HANDLE BUTTON CLICKS ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    
    context.user_data["mode"] = choice 
    
    prompts = {
        "ask_ai": "💬 Ask me anything! Send your question:",
        "qr": "🔳 Send the text or link for your QR Code:",
        "image": "🖼 Describe the image you want me to create (Daily limit: 2 images):\n\nBe specific for best results!",
        "pdf": "📄 Send the topic/content for your AI PDF:\n_(Note: Generation takes 5-10 seconds for high quality)_",
        "captions": "✍ Send the topic for your social media captions:",
        "youtube": "🎥 Send a niche or topic (e.g., Tech, Cooking) for Video Ideas:",
        "resume": "💼 Send your resume details (Name, Skills, Education, Experience):"
    }
    await query.edit_message_text(text=prompts.get(choice, "Send input:"), parse_mode=ParseMode.MARKDOWN)

# ---------- HELPERS ----------  
async def ai_chat(prompt: str) -> str:
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant", 
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=800
    )
    return completion.choices[0].message.content

async def fast_qr(data: str):
    qr = qrcode.make(data)
    bio = BytesIO()
    bio.name = "qr.png"
    qr.save(bio, "PNG")
    bio.seek(0)
    return bio

async def generate_image(prompt: str):
    try:
        image = image_client.text_to_image(prompt)
        bio = BytesIO()
        bio.name = "generated_image.png"
        image.save(bio, "PNG")
        bio.seek(0)
        return bio
    except Exception as e:
        print(f"Image Generation Error: {e}")
        return None

def shorten_url(url: str) -> str:
    try:
        api_url = f"http://tinyurl.com/api-create.php?url={urllib.parse.quote(url)}"
        return urllib.request.urlopen(api_url).read().decode('utf-8')
    except:
        return "❌ Error: Could not shorten URL. Make sure it starts with http://"

def generate_pdf(title: str, content: str, filename: str):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 16)
    safe_title = title.encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, txt=safe_title, ln=1, align="C")
    pdf.ln(6)
    
    pdf.set_font("Arial", size=12)
    clean_content = content.replace("*", "").replace("", "")
    safe_content = clean_content.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, txt=safe_content)
    
    pdf.ln(10)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 10, txt="Made by Shivam", ln=1, align="C")
    
    pdf.output(filename)

# ---------- INTELLIGENT MESSAGE HANDLER ----------  
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_database.add(user_id)
    chat_id = update.effective_chat.id
    mode = context.user_data.get("mode", "ask_ai")

    # BUG FIX: Actively block photos/stickers/documents when text is needed
    if not update.message.text:
        await update.message.reply_text(
            "🚫 Oops! Incorrect Input Detected.\n\n"
            "I need *text* or a *link* to process your request. I cannot process photos, documents, or stickers for this tool.\n\n"
            "Please type your input and send it again!", 
            parse_mode=ParseMode.MARKDOWN
        )
        return # Keeps them in their current mode so they can try again

    text = update.message.text.strip()

    try:
        if mode == "short":
            await update.message.reply_text("🔗 Shortening...")
            short_link = shorten_url(text)
            await update.message.reply_text(f"✅ Here is your shortened link:\n{short_link}", parse_mode=ParseMode.MARKDOWN)
            
        elif mode == "feedback":
            await update.message.reply_text("✅ Thank you! Your feedback has been sent directly to Shivam.", parse_mode=ParseMode.MARKDOWN)
            print(f"FEEDBACK FROM {update.effective_user.first_name}: {text}")
            
        elif mode == "weather":
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            reply = await ai_chat(f"Provide a brief, realistic current weather estimate and climate description for: {text}. Keep it under 3 sentences.")
            await update.message.reply_text(f"🌤 Weather Info for {text}:\n\n{reply}", parse_mode=ParseMode.MARKDOWN)
            
        elif mode == "qr": 
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
            qr_img = await fast_qr(text)
            await update.message.reply_photo(photo=qr_img, caption="Here is your QR 🔳\n\n✨ Made by Shivam 😈", parse_mode=ParseMode.MARKDOWN)

        elif mode == "image":
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            if user_id not in image_usage_db or image_usage_db[user_id]["date"] != today_str:
                image_usage_db[user_id] = {"count": 0, "date": today_str}
                
            if image_usage_db[user_id]["count"] >= 2:
                await update.message.reply_text(
                    "🚫 Daily Limit Reached!\n\nYou have already generated 2 images today to conserve server resources. Please come back tomorrow to generate more!", 
                    parse_mode=ParseMode.MARKDOWN
                )
                context.user_data.clear()
                await update.message.reply_text("Need anything else? 👇", reply_markup=get_menu_keyboard())
                return
            
            status_msg = await update.message.reply_text(f"🧠 Forging your masterpiece... (Used: {image_usage_db[user_id]['count']}/2 today) ⏳", parse_mode=ParseMode.MARKDOWN)
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
            
            image_bio = await generate_image(text)
            
            if image_bio:
                image_usage_db[user_id]["count"] += 1
                await status_msg.edit_text("✅ Masterpiece complete! Uploading...", parse_mode=ParseMode.MARKDOWN)
                await update.message.reply_photo(
                    photo=image_bio, 
                    caption=f"🖼 Result for: {text[:40]}...\n\nGenerated professionally by TELBOT AI 😈", 
                    parse_mode=ParseMode.MARKDOWN
                )
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ Image generation failed. Please try a different description, or try again later.")

        elif mode == "pdf":
            status_msg = await update.message.reply_text("🧠 AI is writing the content... Please wait a few seconds ⏳", parse_mode=ParseMode.MARKDOWN)
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            content = await ai_chat(f"Write a comprehensive, professional article about: {text}. Do not use emojis.")
            
            await status_msg.edit_text("📄 Formatting into PDF...", parse_mode=ParseMode.MARKDOWN)
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)
            
            generate_pdf(f"Topic: {text[:20]}...", content, "ai_content.pdf")
            with open("ai_content.pdf", "rb") as pdf_file:
                await update.message.reply_document(pdf_file, filename="AI_Content.pdf", caption="✨ Made by Shivam 😈", parse_mode=ParseMode.MARKDOWN)
            await status_msg.delete()

        elif mode == "captions":
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            reply = await ai_chat(f"Write 5 trendy social media captions with hashtags and emojis for: {text}")
            await update.message.reply_text(reply + "\n\n✨ Made by Shivam 😈")

        elif mode == "youtube":
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            reply = await ai_chat(f"Give me 5 highly engaging, click-worthy YouTube video ideas and titles for the niche: {text}")
            await update.message.reply_text(reply + "\n\n✨ Made by Shivam 😈", parse_mode=ParseMode.MARKDOWN)

        elif mode == "resume":
            status_msg = await update.message.reply_text("💼 AI is designing your resume... ⏳", parse_mode=ParseMode.MARKDOWN)
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)
            resume_text = await ai_chat(f"Create a clean professional resume using these details. Do not use emojis or complicated symbols:\n{text}")
            
            generate_pdf("Professional Resume", resume_text, "resume.pdf")
            with open("resume.pdf", "rb") as resume_file:
                await update.message.reply_document(resume_file, filename="Resume.pdf", caption="✨ Made by Shivam 😈", parse_mode=ParseMode.MARKDOWN)
            await status_msg.delete()

        else: # ask_ai / fallback
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            reply = await ai_chat(text)
            await update.message.reply_text(reply + "\n\n✨ Made by Shivam 😈", parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        await update.message.reply_text(f"❌ An error occurred. Please try again or type /start. \nError: {e}")

    # Reset mode and show menu
    context.user_data.clear()
    await update.message.reply_text("Need anything else? 👇", reply_markup=get_menu_keyboard())

# ---------- MAIN APPLICATION ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(setup_commands).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("contact", cmd_contact))
    app.add_handler(CommandHandler("info", cmd_info))
    app.add_handler(CommandHandler("time", cmd_time))
    app.add_handler(CommandHandler("weather", cmd_weather))
    app.add_handler(CommandHandler("qr", cmd_qr)) 
    app.add_handler(CommandHandler("short", cmd_short))
    app.add_handler(CommandHandler("feedback", cmd_feedback))
    app.add_handler(CommandHandler("stats", stats)) 
    
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # CRITICAL FIX: Changed from filters.TEXT to filters.ALL so the bot catches and rejects photos logically
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    print("🔥 TELBOT AI is online (Limits Applied, Image Bug Fixed, and Ready for Deployment!)")
    app.run_polling()

# CORRECT ENTRY POINT SYNTAX
if __name__ == "__main__":
    main()