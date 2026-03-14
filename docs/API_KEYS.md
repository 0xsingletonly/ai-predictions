# API Keys Setup Guide

This document explains how to obtain the API keys required for the Macro Reasoning Agent.

---

## Required APIs

### 1. Kimi API (LLM Reasoning) **REQUIRED**

Used for the 4-step reasoning pipeline (evidence classification, bull/bear cases, posterior updates).

**Website:** https://platform.moonshot.cn/

**Steps:**
1. Go to https://platform.moonshot.cn/
2. Sign up for an account (requires Chinese phone number or international signup)
3. Navigate to "API Keys" section
4. Create a new API key
5. Add to your `.env` file:
   ```bash
   KIMI_API_KEY=your_kimi_api_key_here
   ```

**Pricing:**
- Free tier: ¥15 credits for new users
- Pay-as-you-go after free credits
- Kimi K2.5: ~¥12 per million tokens (input), ~¥60 per million tokens (output)
- Very affordable for this use case (~50-100 questions ≈ ¥5-10/day)

**Model:** We use `kimi-k2.5` which is optimized for reasoning tasks.

---

### 2. NewsAPI (News Ingestion) **OPTIONAL**

Used for fetching relevant news articles for each question.

**Website:** https://newsapi.org/

**Steps:**
1. Go to https://newsapi.org/register
2. Sign up with email
3. Get your API key from the dashboard
4. Add to your `.env` file:
   ```bash
   NEWSAPI_KEY=your_newsapi_key_here
   ```

**Free Tier Limits:**
- 100 requests per day
- 1,000 requests per month
- Perfect for this project (we fetch once per day per question)

**Note:** The system works without NewsAPI - it will simply skip news fetching and rely on other data sources.

---

### 3. Polymarket APIs **FREE - No Key Required**

Polymarket's Gamma and CLOB APIs are public and don't require authentication for read-only access.

- **Gamma API:** https://gamma-api.polymarket.com
- **CLOB API:** https://clob.polymarket.com

These are used for:
- Fetching market metadata (questions, liquidity, resolution dates)
- Getting current prices
- Discovering eligible questions

---

## Environment File Setup

Create a `.env` file in the `backend/` directory:

```bash
cd backend
cp .env.example .env
```

Edit `.env` and add your keys:

```bash
# Required
KIMI_API_KEY=sk-your-kimi-key-here

# Optional
NEWSAPI_KEY=your-newsapi-key-here
```

---

## Testing Your Setup

### Test Phase 1 (Data Pipeline)
```bash
cd backend
source venv/bin/activate
python tests/test_phase1.py
```

Expected: 4-5 tests pass (NewsAPI test skips if no key)

### Test Phase 2 (LLM Reasoning)
```bash
python tests/test_phase2.py
```

Expected: All tests pass when KIMI_API_KEY is set

### Quick API Test
```python
import asyncio
from src.agents.reasoning import KimiReasoningAgent

async def test():
    agent = KimiReasoningAgent()
    # This will raise an error if key is invalid
    print("✅ Kimi API key is valid!")

asyncio.run(test())
```

---

## Troubleshooting

### "Kimi API key required" error
- Make sure `KIMI_API_KEY` is set in your `.env` file
- Ensure you've run `source venv/bin/activate` in the backend directory
- Check that the `.env` file is in the `backend/` directory

### NewsAPI rate limit exceeded
- Free tier is 100 requests/day
- We only fetch once per day per question, so 5 questions = 5 requests
- If you hit limits, wait until the next day or upgrade to paid tier ($449/month)

### Kimi API errors
- Check your credit balance at https://platform.moonshot.cn/
- Ensure you're using the correct model name: `kimi-k2.5`
- Kimi API has rate limits - we've implemented retry logic

---

## Security Notes

- **Never commit `.env` files to git** (already in `.gitignore`)
- **Never share your API keys** in code, logs, or documentation
- **Rotate keys periodically** for security
- **Monitor usage** in the respective dashboards
