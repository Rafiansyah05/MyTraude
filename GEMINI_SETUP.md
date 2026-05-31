# Google Gemini API Setup Guide

Complete guide to set up and use Google's Gemini API for AI trading analysis.

## Quick Start (3 minutes)

### 1. Get Your API Key

**Visit Google AI Platform:**

1. Go to: https://ai.google.dev/
2. Click **"Get API Key"** button
3. Select/create Google Cloud Project
4. Click **"Create API Key in Google Cloud Console"**
5. **Copy the API key** provided

### 2. Update .env File

```env
GEMINI_API_KEYS=YOUR_API_KEY_HERE
GEMINI_MODEL=gemini-pro
GEMINI_TIMEOUT_SECONDS=60
GEMINI_RETRY_ATTEMPTS=3
```

### 3. Test API Key

```bash
# Simple Python test
python -c "
import google.generativeai as genai
genai.configure(api_key='YOUR_KEY')
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content('Hello')
print('✓ API Key works!' if response else '✗ Failed')
"
```

## Detailed Setup

### Step 1: Create Google Account

If you don't have a Google account:

1. Visit https://accounts.google.com/signup
2. Create account with your email
3. Verify phone number
4. Accept terms

### Step 2: Enable Generative Language API

**Option A: Auto-Enable (Easiest)**

Go to https://ai.google.dev/ and click **"Get API Key"** - this auto-enables the API.

**Option B: Manual Enable**

1. Visit Google Cloud Console: https://console.cloud.google.com/
2. Create new project:
   - Click dropdown at top
   - Select "New Project"
   - Name: "IHSG Trading Bot"
   - Click "Create"
3. Wait for project creation (~30s)
4. Search for "Generative Language API":
   - Click "Enable"
5. Go to Credentials:
   - Create API key
   - Choose "API key" type
   - Copy the key

### Step 3: Manage API Key

**Restrict API Key (Recommended for security):**

1. Go to Google Cloud Console → Credentials
2. Click on your API key
3. Under "Application restrictions":
   - Select "IP addresses"
   - Add your server IP
4. Under "API restrictions":
   - Select "Restrict key"
   - Choose "Generative Language API"
5. Click "Save"

## Using Multiple API Keys

For reliability with key rotation:

```env
# Multiple keys (comma-separated)
GEMINI_API_KEYS=key1,key2,key3,key4

# Bot automatically rotates if one fails
```

**How it works:**

- First request: Uses key1
- If key1 fails: Rotates to key2
- If key2 fails: Rotates to key3
- Continues until success or all fail

**Why use multiple keys?**

- Bypass rate limits (distribute quota)
- Failover if one key is revoked
- Separate keys per API key quota

### Get Multiple Keys

1. Repeat steps above for each key
2. Create multiple API keys in same project
3. Each key gets separate quota

## Understanding API Quotas

### Free Tier Limits (as of 2024)

- **Requests**: 60 per minute
- **Tokens**: ~1M tokens per day
- **Characters**: Unlimited per request
- **RPM (Requests/Min)**: 60

### Monitor Usage

1. Google Cloud Console → Generative Language API
2. Check quotas and rates
3. View request logs

### Increase Quotas

1. Enable billing in Google Cloud
2. Quotas increase automatically with usage patterns
3. Contact Google Cloud Support for manual increase

## Troubleshooting

### "Invalid API Key" Error

```
google.api_core.exceptions.InvalidArgument: 400 Invalid API key
```

**Fix:**

1. Check .env file for typos
2. Regenerate key from console
3. Ensure key is for "Generative Language API"
4. Test with simple request

### "Quota Exceeded" Error

```
google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded
```

**Causes:**

- Too many requests per minute
- Too many requests per day
- Using free tier

**Fix:**

```env
# Increase delays
RETRY_BACKOFF_SECONDS=15
RETRY_ATTEMPTS=5

# Or use multiple keys for rotation
GEMINI_API_KEYS=key1,key2,key3
```

### "API Not Enabled" Error

```
The caller does not have permission to access resource
```

**Fix:**

1. Go to Google Cloud Console
2. Search for "Generative Language API"
3. Click "Enable"
4. Wait a few minutes for propagation
5. Try again

### Timeout Issues

If Gemini requests timeout:

```env
# Increase timeout
GEMINI_TIMEOUT_SECONDS=120

# Reduce retries if timeout is expected
GEMINI_RETRY_ATTEMPTS=2
```

## API Request Examples

### Direct API Call (Testing)

```bash
# Using curl
curl -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "parts": [{
        "text": "Explain IHSG stock market"
      }]
    }]
  }'
```

### Python Test

```python
import google.generativeai as genai

# Configure
genai.configure(api_key="YOUR_API_KEY")

# Create model
model = genai.GenerativeModel("gemini-pro")

# Generate response
response = model.generate_content("Test message")

# Print response
print(response.text)
```

## Using in Your Bot

The bot automatically uses Gemini API through `ai/gemini_client.py`:

```python
from ai.gemini_client import GeminiClient

# Initialize (automatic on bot start)
GeminiClient.initialize()

# Generate response
response = await GeminiClient.generate_response(prompt)

# Returns: Generated text or None
```

## Rate Limit Management

### Problem

If bot hits rate limits, requests will timeout.

### Solution 1: Use Multiple Keys

```env
# Distribute requests across keys
GEMINI_API_KEYS=key1,key2,key3,key4

# Automatic rotation on error
# Each request retry tries next key
```

### Solution 2: Increase Delays

```env
# Wait longer between retries
RETRY_BACKOFF_SECONDS=10

# More retry attempts
GEMINI_RETRY_ATTEMPTS=5

# Longer timeout per request
GEMINI_TIMEOUT_SECONDS=120
```

### Solution 3: Enable Billing

1. Google Cloud Console
2. Enable billing for project
3. Quotas increase automatically
4. More reliable service

## Production Checklist

- [ ] API key created and tested
- [ ] Key added to .env file
- [ ] API enabled in Google Cloud Console
- [ ] Quotas monitored (if using billing)
- [ ] Tested with `/analyze` command
- [ ] Multiple keys configured (optional)
- [ ] Timeouts set appropriately
- [ ] Error handling verified
- [ ] Rate limits understood
- [ ] Backup key available

## Best Practices

✅ **DO:**

- Keep API key secret (never commit to git)
- Use multiple keys for reliability
- Monitor quota usage
- Set appropriate timeouts
- Enable billing for production
- Test prompts before deployment

❌ **DON'T:**

- Share API key publicly
- Hardcode key in code
- Leave key in git history
- Use free tier for high-traffic
- Ignore timeout errors
- Make huge batch requests

## Advanced: Custom Models

### Available Models

```
- gemini-pro              (Free tier, default)
- gemini-1.5-pro         (Advanced, requires billing)
- gemini-1.5-flash       (Faster, lower cost)
- embed-model-001        (For embeddings)
```

### Switch Models

```env
GEMINI_MODEL=gemini-1.5-flash
```

### Model Comparison

| Model            | Speed     | Cost   | Context |
| ---------------- | --------- | ------ | ------- |
| gemini-pro       | Medium    | Free   | 32K     |
| gemini-1.5-pro   | Fast      | Higher | 1M      |
| gemini-1.5-flash | Very Fast | Low    | 1M      |

## Monitoring & Logs

### View API Calls in Logs

```bash
# Search for Gemini calls
grep "Gemini" logs/trading_bot.log

# Filter for errors
grep "Gemini.*ERROR" logs/trading_bot.log

# Watch live
tail -f logs/trading_bot.log | grep -i gemini
```

### Monitor Quotas

```bash
# Python script to check usage
python -c "
import google.generativeai as genai

genai.configure(api_key='YOUR_KEY')
model = genai.GenerativeModel('gemini-pro')

# Make test request
try:
    response = model.generate_content('Test')
    print('✓ API working')
    print('✓ Quota available')
except Exception as e:
    print(f'✗ Error: {e}')
"
```

## Support

- **Official Docs**: https://ai.google.dev/docs
- **API Reference**: https://ai.google.dev/api
- **Pricing**: https://ai.google.dev/pricing
- **Support**: https://support.google.com/cloud

---

**Next Step**: Start your bot and test with `/analyze` command
