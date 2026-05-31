# Telegram Bot Setup Guide

Step-by-step guide to create and configure your Telegram bot.

## Quick Start (5 minutes)

### 1. Create Bot with @BotFather

**Open Telegram** and search for `@BotFather`:

```
@BotFather is the one bot to rule them all. It will help you create new bots
and change settings for existing bots.

/start           - Start using this bot
/newbot          - Create a new bot
/mybots          - Edit your existing bots
/mygames         - Edit your Telegram games
```

**Send `/newbot`**:

```
BotFather: Alright, a new bot. How are we going to call it?
           Please choose a name for your bot.

You: IHSG Trading Bot

BotFather: Good. Now let's choose a username for your bot.
           It must end in `bot`. For example, TetrisBot or tetris_bot.

You: ihsg_trading_bot
```

**BotFather gives you the TOKEN**:

```
BotFather: Done! Congratulations on your new bot. You will find it at
           t.me/ihsg_trading_bot. You can now add a description,
           about section and profile picture for your bot, see /help for a
           list of commands.

Use this token to access the HTTP API:
123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

For security reasons, please keep your token secure and store it safely.
```

**Copy and save this TOKEN** - you'll need it in .env file.

### 2. Get Your User ID

**Search for `@userinfobot`** (or `/getuserbot`):

```
userinfobot: Information about the user currently using this bot:

User id: 1234567890
First name: Your Name
Username: @yourname
Language: en
```

**Copy your User ID** (the number) - you'll need this in .env file.

### 3. Update .env File

Open `.env` in your project:

```env
# From BotFather token
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# From @userinfobot
TELEGRAM_USER_ID=1234567890

# Required for analysis
GEMINI_API_KEYS=your_gemini_api_key_here
```

### 4. Test Bot Connection

```bash
# Start bot
python main.py

# In another terminal/Telegram, send to your bot:
/start
/help
```

If bot responds, ✅ you're connected!

## Telegram Bot Features

### Privacy & Security

- **Private Chats**: Bot only responds to configured user ID
- **No Group Support**: Currently single-user only
- **Token Safety**: Keep TELEGRAM_BOT_TOKEN secret
- **Session Cleanup**: Auto-cleanup after timeout

### Commands Available

- `/start` - Welcome message
- `/help` - Full help
- `/analyze` - Start trading analysis
- `/watchlist` - Show recommended stocks

### Message Types

Bot responds to:

- Direct messages (private chat)
- Commands starting with `/`
- Text input (capital amount, questions)

Bot ignores:

- Group messages (not configured for groups)
- Invalid commands
- Messages from other users (different ID)

## Troubleshooting Telegram

### Bot doesn't respond

1. **Check token**:

   ```bash
   # Test token validity
   curl -s https://api.telegram.org/bot123456:ABC-DEF1234.../getMe

   # Should return: {"ok": true, "result": {"id": ..., "is_bot": true}}
   ```

2. **Check bot is running**:

   ```bash
   ps aux | grep main.py
   ```

3. **Check logs**:

   ```bash
   tail -f logs/trading_bot.log | grep -i telegram
   ```

4. **Verify user ID**:
   - Run `/userinfobot` command in Telegram
   - Compare with TELEGRAM_USER_ID in .env

### Bot returns error messages

- **"❌ Terjadi kesalahan"**: Check logs for details
- **"❌ Modal terlalu kecil"**: Enter amount >= TRADING_CAPITAL_MIN
- **"❌ Format tidak valid"**: Use format like "5juta" or "5000000"

### Timeout issues

If bot takes too long to respond:

1. **Increase timeouts** in .env:

   ```env
   DATA_TIMEOUT_SECONDS=45
   GEMINI_TIMEOUT_SECONDS=90
   ```

2. **Check internet speed**:

   ```bash
   ping 8.8.8.8
   ```

3. **Check Gemini API**:
   - Visit https://ai.google.dev
   - Verify API key is active

### Connection fails

```bash
# Test Telegram API connectivity
curl -s https://api.telegram.org/botTESTING123:ABC/getMe

# Test internet
ping google.com
```

## Bot Administration

### Set Bot Description

```
/setdescription

Current description:
AI Trading Assistant for Indonesian Stock Market (IHSG)

New description (or /skip):
IHSG Trading Bot - Technical Analysis & Recommendations
```

### Set Bot Avatar

```
/setuserpic

Current profile picture:
[image]

Send new image (or /skip):
[upload image]
```

### Set Bot Commands in Telegram

BotFather displays available commands:

```
/mybots
→ Select your bot
→ Edit commands

/start          - Mulai dengan bot
/help           - Lihat bantuan lengkap
/analyze        - Mulai analisis trading
/watchlist      - Lihat daftar saham
```

## Multiple Bots / Advanced

### Multiple Telegram Accounts

Create separate bot instances:

1. Create bot with each BotFather
2. Create separate .env files:
   ```
   .env.user1
   .env.user2
   ```
3. Run separate bot instances:
   ```bash
   DOTENV_FILE=.env.user1 python main.py
   DOTENV_FILE=.env.user2 python main.py &
   ```

### Webhook Mode (Advanced)

Instead of polling, use webhooks:

```python
# In telegram_bot.py (requires setup):
await application.run_webhook(...)
```

Requires:

- Public IP address
- SSL certificate
- More complex deployment

For most users, polling (current implementation) is simpler.

### Rate Limiting

Telegram has rate limits:

- 30 messages per second per bot
- Current implementation handles this automatically

If you get 429 errors:

```env
# Increase retry backoff
RETRY_BACKOFF_SECONDS=10
RETRY_ATTEMPTS=5
```

## Monitoring Bot Health

### Check Bot Status

```bash
# Send test command
curl -s https://api.telegram.org/botTOKEN:VALUE/sendMessage \
  -d chat_id=YOUR_ID \
  -d text="Health check"
```

### Monitor Logs

```bash
# Watch bot logs
tail -f logs/trading_bot.log

# Filter for errors
grep ERROR logs/trading_bot.log

# Filter for user activity
grep "User" logs/trading_bot.log | tail -20
```

### Automated Monitoring

```bash
#!/bin/bash
# check_bot.sh - Monitor bot health

BOT_LOG="logs/trading_bot.log"

# Check if bot is running
if ! pgrep -f "python main.py" > /dev/null; then
    echo "Bot is DOWN! Starting..."
    python main.py &
fi

# Check for recent errors
ERROR_COUNT=$(grep ERROR $BOT_LOG | tail -100 | wc -l)
if [ $ERROR_COUNT -gt 10 ]; then
    echo "High error rate detected: $ERROR_COUNT errors in last 100 lines"
fi

# Check log size
LOG_SIZE=$(du -h $BOT_LOG | cut -f1)
echo "Bot healthy. Log size: $LOG_SIZE"
```

Add to crontab:

```bash
*/5 * * * * /path/to/check_bot.sh
```

## Best Practices

✅ **DO:**

- Keep token in .env (never commit to git)
- Test commands manually before deploying
- Monitor logs regularly
- Use private user ID (not group chats)
- Store .env securely with restricted permissions
- Test timeouts match your network speed

❌ **DON'T:**

- Share bot token publicly
- Use bot in group chats (not designed for it)
- Hardcode credentials in code
- Ignore error logs
- Leave old .env files around
- Assume bot is working without testing

## Common Commands Reference

```
@BotFather commands:
/newbot             - Create new bot
/mybots             - Manage existing bots
/setdescription     - Set bot description
/setshortdescription - Short description
/setuserpic         - Set profile picture
/setcommands        - Define available commands
/setdefaultcommands - Default commands for all bots

Your Bot commands:
/start              - Welcome message
/help               - Show help
/analyze            - Trading analysis
/watchlist          - Stock watchlist
```

---

**Next Step**: Go back to README.md and complete Google Gemini setup
