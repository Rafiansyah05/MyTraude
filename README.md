# AI Trading Assistant Telegram Bot (IHSG)

Fully functional Telegram bot for Indonesian Stock Market (IHSG) trading analysis and recommendations.

## Features

✅ **Automated Morning Analysis** - Scheduled analysis at 08:00 WIB every weekday
✅ **Technical Screening** - MA20, RSI, Volume accumulation detection
✅ **AI-Powered Recommendations** - Google Gemini API integration
✅ **Risk Management** - Automatic lot, capital allocation, and risk-reward calculations
✅ **Casual Chat** - Financial Q&A outside trading hours
✅ **In-Memory Sessions** - No database required, auto-cleanup
✅ **Production-Ready** - Retry logic, error handling, structured logging

## System Architecture

```
DATA LAYER
├── IDX Scraper (Indonesia Stock Exchange data)
├── Yahoo Finance Fetcher (.JK stocks)
└── Technical Indicators (MA20, RSI, Volume)

CORE ENGINE
├── Stock Screener (technical criteria)
├── Risk Manager (hardcoded calculations)
└── Response Parser (Gemini output parsing)

AI LAYER
├── Gemini Client (API integration + key rotation)
└── Prompt Builder (structured prompts)

INTERFACE LAYER
├── Telegram Bot (async handlers)
├── Session Manager (in-RAM only)
└── Scheduler (cron integration)
```

## Installation

### 1. Prerequisites

- Python 3.11+
- Linux/Windows with shell access
- Telegram Bot Token
- Google Gemini API Key(s)
- pip package manager

### 2. Setup

```bash
# Clone/download project
cd MyTraude

# Create virtual environment
python -m venv venv

# Activate venv
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit .env file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your editor
```

### 3. Configure .env File

```env
# Required
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_USER_ID=your_telegram_user_id

# API Keys (comma-separated for rotation)
GEMINI_API_KEYS=key1,key2,key3
GEMINI_MODEL=gemini-pro

# Trading Config (optional - defaults provided)
TRADING_CAPITAL_MAX=100000000
TRADING_CAPITAL_MIN=100000
TRADING_SESSION_HOUR=8
TRADING_SESSION_MINUTE=0

# Technical Parameters
MA_PERIOD=20
RSI_PERIOD=14
RSI_OVERBOUGHT=70
MIN_VOLUME_SPIKE=1.5

# Session & Logging
SESSION_TIMEOUT_MINUTES=120
LOG_LEVEL=INFO
```

## Running the Bot

### Option 1: Direct Execution

```bash
# Start bot
python main.py

# Bot will:
# 1. Initialize all components
# 2. Setup Telegram handlers
# 3. Start polling for messages
# 4. Listen for /start, /help, /analyze, /watchlist commands
```

### Option 2: Scheduled Automation (Linux Cron)

```bash
# Make script executable
chmod +x cron_script.sh

# Edit crontab
crontab -e

# Add this line (08:00 WIB, weekdays only)
0 8 * * 1-5 /path/to/MyTraude/cron_script.sh

# Verify
crontab -l

# Check logs
tail -f logs/cron_analysis.log
```

### Option 3: Systemd Service (Linux)

Create `/etc/systemd/system/trading-bot.service`:

```ini
[Unit]
Description=AI Trading Assistant Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/MyTraude
Environment="PATH=/home/ubuntu/MyTraude/venv/bin"
ExecStart=/home/ubuntu/MyTraude/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start service:

```bash
sudo systemctl start trading-bot
sudo systemctl enable trading-bot  # Auto-start on reboot
sudo systemctl status trading-bot

# Logs
sudo journalctl -u trading-bot -f
```

## Bot Commands

### /start

Display welcome message and available commands.

### /help

Show comprehensive help and usage guide.

### /analyze

Start trading analysis session:

1. Bot asks for trading capital amount
2. User enters capital (e.g., "5juta" or "5000000")
3. Bot screens stocks automatically
4. Returns recommendations with entry/target/cut loss

### /watchlist

Display list of recommended stocks to monitor.

## Trading Workflow

### Morning Session (08:00 WIB Weekdays)

1. **08:00 WIB**: Cron triggers automatic message

   ```
   "🌅 PAGI! Analisis Trading Hari Ini Dimulai
   📊 Mari mulai sesi trading pagi Anda!
   Langkah pertama: Masukkan modal trading untuk hari ini"
   ```

2. **User Input**: Enter capital amount
   - Format: "5juta" or "5000000"
   - Validated against min/max limits

3. **System Processing**:
   - Fetch IDX stock list
   - Download Yahoo Finance data (3 months)
   - Calculate technical indicators (MA20, RSI, Volume)
   - Screen stocks using criteria:
     - Price > MA20 (uptrend)
     - RSI < 70 (not overbought)
     - Volume spike > 1.5x average
   - Select top 5 candidates

4. **AI Analysis**:
   - Build structured Gemini prompt
   - Gemini analyzes and returns recommendations
   - Format: TICKER|REASON|ENTRY|TARGET|CUTLOSS
   - Examples:
     ```
     BBCA|Strong accumulation breakout|9500|9900|9300
     ASII|Volume spike uptrend|7200|7500|7000
     ```

5. **Risk Calculations** (Hardcoded Python):
   - Ms = Capital × 0.20 (20% allocation per stock)
   - Qshares = Ms / EntryPrice
   - Qlots = max(1, floor(Qshares / 100))
   - Profit target = Qshares × TargetPrice
   - Max loss = Qshares × CutLossPrice
   - Risk/Reward = (Target - Entry) / (Entry - CutLoss)

6. **Telegram Output** (Formatted):

   ```
   📈 STOCK RECOMMENDATION

   #1 BBCA
   ==================================================
   📊 Analisis: Strong accumulation with breakout above MA20

   💰 Harga Entry:  Rp      9,500
   🎯 Target Price: Rp      9,900
   🛑 Cut Loss:     Rp      9,300

   💸 Money Management:
      Modal Total:     Rp 5,000,000
      Alokasi:         Rp 1,000,000
      Jumlah Saham:    105 lembar
      Jumlah Lot:      1 lot (@ 100 saham)

   📈 Profit/Risk:
      Potensi Profit:  Rp 1,039,500
      Max Loss:        Rp 21,000
      Risk/Reward:     1:49.50
   ```

## Configuration Details

### Technical Indicators

- **MA20**: 20-period moving average (trend identification)
- **RSI14**: Relative Strength Index (overbought/oversold)
- **Relative Volume**: Current volume / average volume
- **Volume Accumulation**: Detected when volume > 1.5x average

### Screening Criteria

Stock must meet ALL criteria to pass:

1. ✓ Price > MA20 (uptrend)
2. ✓ RSI < 70 (not overbought)
3. ✓ Volume spike > 1.5x (volume increase)

### Risk Management Formulas

```
Maximum Capital per Stock:
Ms = Mtotal × 0.20

Share Quantity:
Qshares = Ms / EntryPrice

Lot Quantity:
Qlots = max(1, floor(Qshares / 100))

Profit Target:
ProfitTarget = Qshares × TargetPrice

Max Loss:
MaxLoss = Qshares × CutLossPrice

Risk-Reward Ratio:
RR = (TargetPrice - EntryPrice) / (EntryPrice - CutLossPrice)
```

### Session Management

- Sessions stored in RAM only (no database)
- Auto-cleanup after 120 minutes of inactivity
- Cleanup check every 5 minutes
- User can have only one active session

### Gemini API

- **Role**: Senior Technical & Volume Action Analyst
- **Model**: gemini-pro
- **Timeout**: 60 seconds per request
- **Retry**: 3 attempts with exponential backoff
- **Key Rotation**: Automatic rotation on API failure
- **Output Format**: Strictly TICKER|REASON|ENTRY|TARGET|CUTLOSS

## Telegram Bot Setup

### Step 1: Create Bot with BotFather

```
1. Open Telegram
2. Search for @BotFather
3. Send: /newbot
4. Follow prompts:
   - Bot name: "IHSG Trading Bot" (or your choice)
   - Bot username: "your_username_bot"
5. Copy the TOKEN provided
```

### Step 2: Get Your User ID

```
1. Search for @userinfobot
2. Send any message
3. Bot returns your numeric user ID
4. Copy this ID
```

### Step 3: Configure .env

```env
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_FROM_BOTFATHER
TELEGRAM_USER_ID=YOUR_NUMERIC_ID_FROM_USERINFOBOT
```

## Google Gemini API Setup

### Step 1: Get API Key

```
1. Visit: https://ai.google.dev
2. Click "Get API Key" or "Create API Key"
3. Create new API key in Google Cloud Console
4. Copy your API key
```

### Step 2: Enable Generative Language API

```
1. Go to Google Cloud Console
2. Enable "Generative Language API"
3. Create an API key (restrict to Generative Language API)
```

### Step 3: Configure .env

```env
GEMINI_API_KEYS=your_api_key_here
GEMINI_MODEL=gemini-pro
```

For key rotation:

```env
GEMINI_API_KEYS=key1,key2,key3,key4
```

## Troubleshooting

### "TELEGRAM_BOT_TOKEN is required"

- Check .env file exists and has correct token
- Verify token format from @BotFather

### "No Gemini API keys configured"

- Ensure GEMINI_API_KEYS in .env
- Check API key is active in Google Cloud Console
- Test key at https://ai.google.dev

### "No data found for ticker"

- Stock ticker might not exist on Yahoo Finance
- Verify ticker format (e.g., BBCA.JK)
- Check internet connection

### "Timeout errors"

- Increase DATA_TIMEOUT_SECONDS in .env
- Check internet speed
- Verify Yahoo Finance is accessible

### "No stocks passed screening"

- Market might be down
- Screening criteria too strict
- Try adjusting MIN_VOLUME_SPIKE in .env

### Session expires before analysis completes

- Increase SESSION_TIMEOUT_MINUTES in .env
- Improve network/API speed
- Check Gemini API latency

## Performance Optimization

### Reduce API Calls

```env
# Cache IDX data for 5 minutes
IDX_UPDATE_INTERVAL=300

# Limit concurrent requests
# (hardcoded as semaphore in yahoo_fetcher.py)
```

### Optimize Timeouts

```env
# Faster failures
DATA_TIMEOUT_SECONDS=20
GEMINI_TIMEOUT_SECONDS=45

# Balance with reliability
RETRY_ATTEMPTS=3
RETRY_BACKOFF_SECONDS=3
```

### Reduce Dataset

```python
# In screener.py: reduce stocks checked
top_candidates = StockScreener.get_top_candidates(screened, limit=3)
```

## File Structure

```
MyTraude/
├── bot/
│   ├── telegram_bot.py      # Main bot instance
│   ├── handlers.py          # Command handlers
│   └── session_manager.py   # Session storage (RAM)
├── core/
│   ├── screener.py          # Stock screening
│   ├── indicators.py        # Technical indicators
│   ├── risk_manager.py      # Risk calculations
│   └── parser.py            # Gemini response parsing
├── ai/
│   ├── gemini_client.py     # Gemini API client
│   └── prompt_builder.py    # Prompt construction
├── data/
│   ├── idx_scraper.py       # IDX data fetching
│   └── yahoo_fetcher.py     # Yahoo Finance fetching
├── scheduler/
│   └── cron_runner.py       # Scheduled tasks
├── config/
│   └── settings.py          # Configuration
├── utils/
│   ├── logger.py            # Structured logging
│   └── helpers.py           # Utility functions
├── main.py                  # Entry point
├── requirements.txt         # Dependencies
├── .env.example             # Config template
├── cron_script.sh          # Cron wrapper
├── README.md               # This file
└── logs/                   # Log directory (auto-created)
```

## Production Deployment Checklist

- [ ] Create .env with all required keys
- [ ] Test bot locally with /start command
- [ ] Verify Gemini API works
- [ ] Test analysis workflow with /analyze
- [ ] Setup cron or systemd for automation
- [ ] Configure logging (check logs/ directory)
- [ ] Test morning automation at scheduled time
- [ ] Monitor logs for errors
- [ ] Set up log rotation (optional)
- [ ] Document API keys securely
- [ ] Setup alerts for bot failures

## Limitations

- **No Database**: All session data is in RAM, cleared on bot restart
- **Single User Focus**: Designed for personal use (scale with multiple bot instances for multi-user)
- **Market Hours Only**: Full analysis during 09:00-15:30 WIB
- **Limited History**: 3-month data for technical analysis
- **No Position Tracking**: Recommendations only, no position management

## Future Enhancements

- [ ] Database integration for position tracking
- [ ] Multiple user management
- [ ] Real-time price alerts
- [ ] Intraday analysis
- [ ] Backtesting engine
- [ ] Portfolio performance tracking
- [ ] News integration
- [ ] Sector analysis
- [ ] Options/futures support

## Support & Documentation

For issues or questions:

1. Check troubleshooting section above
2. Review logs in `logs/` directory
3. Check Gemini API quota and limits
4. Verify Telegram bot token validity

## License

For personal use only. Modify as needed.

## Disclaimer

⚠️ **This is an educational tool only.**

- Not financial advice
- Past performance ≠ future results
- Verify recommendations before trading
- Manage risk responsibly
- Do your own research (DYOR)

---

**Happy Trading! 📈**
