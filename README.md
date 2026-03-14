# Macro Reasoning Agent v0.2

**Polymarket-Integrated Geopolitical Forecasting System**

An AI-powered reasoning agent that tracks geopolitical prediction markets on Polymarket, generates daily probability estimates using Kimi K2.5 LLM, and evaluates reasoning quality against real-money market resolution.

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- API Keys:
  - **Kimi API Key** (required): Get from [platform.moonshot.cn](https://platform.moonshot.cn/)
  - **NewsAPI Key** (optional): Get from [newsapi.org](https://newsapi.org/)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd ai-predictions

# Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your KIMI_API_KEY

# Setup frontend
cd ../frontend
npm install

# Create .env file
cp .env.example .env
```

---

## CLI Commands

The CLI tool (`backend/cli.py`) provides commands for managing questions, running updates, and viewing status.

### 1. Discover Eligible Questions

Find prediction markets on Polymarket that meet the criteria for tracking.

```bash
cd backend
source venv/bin/activate
python cli.py discover
```

**What to expect:**
- Searches Polymarket for markets with >$50k liquidity
- Filters by resolution horizon (2-4 weeks ideally)
- Displays market title, condition ID, liquidity, and current price
- Use these condition IDs to intake questions

**Options:**
```bash
python cli.py discover --tags geopolitics,politics    # Search specific tags
python cli.py discover --min-liquidity 100000        # Higher liquidity threshold
```

---

### 2. Intake a Question

Add a Polymarket question to the tracking system.

```bash
python cli.py intake <condition_id>
```

**Example:**
```bash
python cli.py intake 0x1234567890abcdef...
```

**What to expect:**
- Fetches market metadata from Polymarket Gamma API
- Stores question in SQLite database (`macro_reasoning.db`)
- Displays question title, category, liquidity, resolution date
- Question status set to "active"

**Output example:**
```
🔍 Intaking question with condition_id: 0x1234...

✅ Successfully intaked question:
  ID: 0x1234567890abcdef...
  Title: Will there be a ceasefire in Gaza by March 31, 2026?
  Category: geopolitics
  Liquidity: $150,000.00
  Resolution Date: 2026-03-31 00:00:00
```

---

### 3. List All Questions

View all tracked questions and their statuses.

```bash
python cli.py list
```

**What to expect:**
- Displays a table with ID, status, category, and title
- Shows both active and resolved questions

**Output example:**
```
ID                                      Status     Category        Title
================================================================================================================
0x1234...                               active     geopolitics     Will there be a ceasefire in Gaza...
0x5678...                               active     central_banks   Will Fed cut rates in 2026?
0xabcd...                               resolved   energy          Will oil hit $100?

Total: 3 questions
```

---

### 4. Check Status

View detailed status of all active questions including current probabilities.

```bash
python cli.py status
```

**What to expect:**
- Shows each active question with latest probability update
- Displays agent probability vs market price
- Shows divergence between agent and market
- Highlights any warnings (anchoring, overreaction)

**Output example:**
```
📊 ACTIVE QUESTIONS STATUS
================================================================================

📝 Will there be a ceasefire in Gaza by March 31, 2026?
   ID: 0x1234567890abcdef...
   Category: geopolitics
   Last Update: 2026-03-14
   Probability: 0.42
   Market Price: 0.45
   Divergence: -0.03
   Confidence: medium

📝 Will Fed cut rates in 2026?
   ID: 0x5678...
   Category: central_banks
   Last Update: 2026-03-14
   Probability: 0.65
   Market Price: 0.62
   Divergence: +0.03
   Confidence: high
   ⚠️  Anchoring Warning
```

---

### 5. Run Daily Update

Manually trigger the daily reasoning update for all active questions.

```bash
python cli.py update
```

**What to expect:**
- Runs the full reasoning pipeline for each active question:
  1. Fetches latest Polymarket price
  2. Fetches relevant news articles (if NewsAPI configured)
  3. Runs Kimi LLM 4-step reasoning (evidence → bull → bear → posterior)
  4. Stores daily log with probabilities and reasoning
  5. Checks for anchoring/overreaction warnings
- Takes ~2-5 minutes depending on number of questions and API latency
- Each question makes 4 API calls to Kimi

**Output example:**
```
🔄 Running daily update...

============================================================
STARTING DAILY UPDATE
============================================================
Found 2 active questions
Processing: Will there be a ceasefire in Gaza by March 31...
  Fetching market data and news...
  Polymarket price: 0.45
  Articles fetched: 5
  Prior probability: 0.42
  Running LLM reasoning...
    Step 1/4: Classifying evidence (5 articles)...
    Step 2/4: Generating bull case...
    Step 3/4: Generating bear case...
    Step 4/4: Computing posterior...
  ✅ Complete: posterior=0.38, delta=-0.04, confidence=medium
Processing: Will Fed cut rates in 2026?
  ...

============================================================
DAILY UPDATE COMPLETE: 2/2 successful
============================================================

✅ Update complete!
  Processed: 2
  Successful: 2
  Failed: 0
```

**Note:** This is also run automatically by the scheduler at 9:00 AM UTC daily.

---

### 6. Resolve a Question

Mark a question as resolved and compute final Brier scores.

```bash
python cli.py resolve <question_id> --outcome <yes|no>
```

**Example:**
```bash
python cli.py resolve 0x1234567890abcdef... --outcome yes
```

**What to expect:**
- Marks question status as "resolved"
- Records the actual outcome (yes/no)
- Computes Brier scores for both agent and market
- Compares agent performance vs market baseline

**Output example:**
```
✅ Question resolved:
  Title: Will oil hit $100?
  Outcome: NO
  Agent Brier Score: 0.1850
  Market Brier Score: 0.2200
  🎯 Agent outperformed market by 0.0350
```

**Brier Score interpretation:**
- 0.0 = Perfect prediction
- 0.25 = Random guessing (50/50)
- 1.0 = Worst possible (100% wrong)
- Lower is better

---

## Running the Full System

### Option 1: Development Mode

**Terminal 1 - Backend API:**
```bash
cd backend
source venv/bin/activate
uvicorn src.api.main:app --reload --port 8000
```

**Terminal 2 - Frontend Dashboard:**
```bash
cd frontend
npm run dev
```

**Access:**
- API: http://localhost:8000
- Dashboard: http://localhost:5173
- API Docs: http://localhost:8000/docs

### Option 2: Scheduler (Background)

Run the daily update automatically at 9:00 AM UTC:

```bash
cd backend
source venv/bin/activate
python -m src.scheduler.scheduler
```

---

## Dashboard Views

### Portfolio Overview (`/`)
- Card grid of all active questions
- Shows agent probability, market price, divergence
- Yellow warnings for >15% market divergence
- Click any card to view question detail

### Question Detail (`/question/:id`)
- Probability evolution chart (agent vs market)
- Daily log history table
- Reasoning inspector (bull case, bear case, WTCMM)
- Evidence classification

### Performance (`/performance`)
- Brier scores for resolved questions
- Agent vs market comparison
- Probability ranges and divergence stats
- Warnings summary

---

## Typical Workflow

1. **Discover:** Find interesting markets
   ```bash
   python cli.py discover
   ```

2. **Intake:** Add up to 5 questions
   ```bash
   python cli.py intake <condition_id_1>
   python cli.py intake <condition_id_2>
   ```

3. **Monitor:** Check status daily
   ```bash
   python cli.py status
   ```

4. **Update:** Run reasoning (or let scheduler do it)
   ```bash
   python cli.py update
   ```

5. **View:** Open dashboard to see charts and reasoning
   ```bash
   # In another terminal
   cd frontend && npm run dev
   ```

6. **Resolve:** When market resolves, record outcome
   ```bash
   python cli.py resolve <question_id> --outcome yes
   ```

---

## Troubleshooting

### "Kimi API key required" error
- Add `KIMI_API_KEY` to `backend/.env`
- Get key from [platform.moonshot.cn](https://platform.moonshot.cn/)

### API connection errors
- Ensure backend is running on port 8000
- Check `VITE_API_URL` in `frontend/.env`

### No questions showing in dashboard
- Intake questions first using `python cli.py intake <id>`
- Run at least one update using `python cli.py update`

### Empty probability chart
- Daily logs must exist for chart to render
- Run `python cli.py update` to generate logs

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Dashboard     │────▶│   FastAPI        │────▶│   SQLite DB     │
│   (React)       │     │   Backend        │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐      ┌──────────────┐      ┌──────────────┐
│  Kimi API     │      │  Polymarket  │      │  NewsAPI     │
│  (LLM)        │      │  (Markets)   │      │  (News)      │
└───────────────┘      └──────────────┘      └──────────────┘
```

---

## License

MIT
