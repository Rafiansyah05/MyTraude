# Quick Start Guide

Get your trading bot running in 5 minutes.

## Prerequisites

- Python 3.11+
- Telegram Bot Token (from @BotFather)
- Google Gemini API Key
- Internet connection

## Step 1: Setup (2 minutes)

```bash
# Clone/navigate to project
cd MyTraude

# Create virtual environment
python -m venv venv

# Activate it
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Get Credentials (1 minute)

### Telegram Bot Token

1. Open Telegram
2. Search @BotFather
3. Send `/newbot`
4. Follow prompts
5. Copy the TOKEN

### User ID

1. Search @userinfobot
2. Send any message
3. Copy your USER ID

### Gemini API Key

1. Visit https://ai.google.dev/
2. Click "Get API Key"
3. Copy your key

## Step 3: Configure (1 minute)

```bash
# Copy config template
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your editor
```

Add:

```env
TELEGRAM_BOT_TOKEN=your_token_from_botfather
TELEGRAM_USER_ID=your_numeric_id
GEMINI_API_KEYS=your_gemini_api_key
```

## Step 4: Run (1 minute)

```bash
# Start bot
python main.py

# You should see:
# ✓ Settings validated
# ✓ Gemini API initialized
# ✓ All components initialized successfully
# 🤖 Starting Telegram bot polling...
```

## Step 5: Test

Open Telegram and message your bot:

```
/start
```

Bot should respond with welcome message!

Try `/help` for commands.

## Success Indicators

✅ Bot responds to /start
✅ /help shows commands
✅ /analyze asks for capital
✅ No error messages in console

## Common Issues

### "TELEGRAM_BOT_TOKEN is required"

→ Check .env has correct token

### Bot doesn't respond

→ Check TELEGRAM_USER_ID matches your Telegram ID

### "No Gemini API keys configured"

→ Add GEMINI_API_KEYS to .env

### Timeout errors

→ Check internet connection, increase timeouts in .env

## Next Steps

1. **Read Full Guide**: Open README.md
2. **Test Analysis**: Send `/analyze` and enter capital (e.g., "5juta")
3. **Setup Automation**: Follow cron setup instructions in README.md
4. **Monitor Logs**: Check logs/trading_bot.log

## File Structure

```
MyTraude/
├── main.py                # Run this to start bot
├── requirements.txt       # Dependencies
├── .env                  # Your credentials (create from .env.example)
├── README.md             # Full documentation
├── TELEGRAM_SETUP.md     # Telegram setup guide
├── GEMINI_SETUP.md       # Gemini setup guide
├── QUICKSTART.md         # This file
│
├── bot/                  # Telegram bot code
├── core/                 # Trading analysis engine
├── ai/                   # AI integration (Gemini)
├── data/                 # Data fetching
├── utils/                # Helper utilities
└── config/               # Configuration
```

## Full Commands

```
/start      - Show welcome message
/help       - Show full help
/analyze    - Start trading analysis session
/watchlist  - Show recommended stocks to watch
```

## Daily Workflow

### Manual Analysis (Any time)

```
1. Message /analyze
2. Enter capital amount (e.g., "5juta")
3. Bot screens and analyzes
4. Get recommendations with entry/target/cut loss
```

### Automated (Weekdays 08:00 WIB)

```
1. Setup cron (see README.md)
2. Bot automatically sends analysis request
3. Follow same flow as manual
```

## Need Help?

1. Check README.md for full documentation
2. See TELEGRAM_SETUP.md for bot issues
3. See GEMINI_SETUP.md for API issues
4. Check logs/trading_bot.log for errors

---

**Happy Trading! 📈**

Questions? Check the full guides:

- README.md - Complete documentation
- TELEGRAM_SETUP.md - Bot configuration
- GEMINI_SETUP.md - API setup
