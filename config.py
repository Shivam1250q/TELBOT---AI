import os
from dotenv import load_dotenv

# Load variables from the hidden .env file
load_dotenv()

# Fetch variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")
HF_API_KEY = os.getenv("HF_API_KEY") # NEW: For the image generator!

# Validate variables (If any are missing, the bot stops and tells you exactly which one)
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not loaded. Check your .env file.")

if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY not loaded. Check your .env file.")

if not ADMIN_ID:
    raise ValueError("❌ ADMIN_ID not loaded. Check your .env file.")

if not HF_API_KEY:
    raise ValueError("❌ HF_API_KEY not loaded. Check your .env file.")