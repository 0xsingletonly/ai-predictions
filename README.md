# Macro Reasoning Agent v0.2

**Polymarket-Integrated Geopolitical Forecasting System**

An AI-powered reasoning agent that tracks geopolitical prediction markets on Polymarket, generates daily probability estimates using Kimi K2.5 LLM, and evaluates reasoning quality against real-money market resolution.

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- API Keys:
  - **Kimi API Key** (required): Get from [platform.moonshot.ai](https://platform.moonshot.ai/)
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
- Fetches all active Polymarket markets via **events endpoint** (~7,500+ markets)
- Filters by liquidity (default: >$50k, adjustable)
- **Sorts by**: Liquidity (highest first) → Resolution date (earliest first)
- Displays market title, condition ID, liquidity, days to resolution, and end date
- Use the condition IDs to intake questions

**Note:** The events endpoint includes markets that are grouped under events (e.g., "US forces enter Iran by...?" event with multiple date markets).

**Options:**
```bash
# Filter by keywords in market title (case-insensitive)
python cli.py discover --keywords "trump,china,war,election"

# Filter by date range (days to resolution)
python cli.py discover --min-days 7 --max-days 60   # Markets resolving in 7-60 days
python cli.py discover --max-days 30                 # Within 30 days only

# Adjust liquidity threshold
python cli.py discover --min-liquidity 100000        # $100k+ liquidity
python cli.py discover --min-liquidity 10000         # $10k+ liquidity (more results)

# Limit number of results fetched
python cli.py discover --limit 50
```

**Notes:**
- Polymarket's API tags are mostly empty, so keyword filtering is the recommended way to find topic-specific markets
- Keyword search matches substrings (e.g., `war` matches `Warriors`) - be specific
- Uses `/events` endpoint which finds 7,500+ markets vs ~100 from `/markets` endpoint
- Lower `--min-liquidity` (e.g., 10000) to find more geopolitical markets

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

There are two ways to run updates:

#### Option A: Full Update (Single Command)

Runs the complete pipeline in one go:

```bash
python cli.py update
```

**What to expect:**
- Runs the full reasoning pipeline for each active question
- Takes ~2-5 minutes depending on number of questions

#### Option B: Split Update (VPN-Friendly)

If you're using a VPN to access US-only Polymarket markets, you may hit Moonshot API rate limits. Use the split workflow:

**Step 1: Fetch Data (US VPN Required)**
```bash
# Connect to US VPN first
python cli.py fetch
```

**What to expect:**
- Fetches Polymarket prices (requires VPN for restricted markets)
- Fetches news articles
- Stores data in `pending_updates` table

**Output:**
```
📥 Fetching Polymarket data (Step 1/2)...
   Fetched: 1
   Failed: 0

✅ Data stored in pending_updates table

📝 NEXT STEP:
   1. Disconnect your VPN (if desired)
   2. Run: python cli.py reason
```

**Step 2: Run Reasoning (No VPN Needed)**
```bash
# Disconnect VPN, then:
python cli.py reason
```

**What to expect:**
- Reads from `pending_updates` table
- Runs Kimi LLM 4-step reasoning (evidence → bull → bear → posterior)
- Creates DailyLog entries
- No VPN needed - Moonshot API works from any location

**Output:**
```
🧠 Running LLM reasoning (Step 2/2)...
   Processing 1 pending update...

   Question: Kharg Island no longer under Iranian control...
   Step 1/4: Classifying evidence...
   Step 2/4: Generating bull case...
   Step 3/4: Generating bear case...
   Step 4/4: Computing posterior...
   ✓ Complete: 0.12 → 0.17

📊 Reasoning Results:
   Processed: 1
   Failed: 0

✅ Daily logs created
```

**Why split?**
- Polymarket US markets require US IP (VPN)
- Moonshot API may rate-limit VPN traffic
- Splitting lets you disconnect VPN before calling LLM APIs

**Full Pipeline Details:**
Each question runs 4 steps:
1. **Classify Evidence** - Categorize news as supports_yes/supports_no/neutral/noise
2. **Generate Bull Case** - Arguments for YES outcome
3. **Generate Bear Case** - Arguments for NO outcome  
4. **Compute Posterior** - Final probability with confidence

Each question makes 4 API calls to Kimi. Run time scales linearly with number of questions.

**Note:** The scheduler (`python -m src.scheduler.scheduler`) runs the full update automatically at 9:00 AM UTC daily.

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
   python cli.py discover --keywords "iran,israel,gaza"
   ```

2. **Intake:** Add questions you want to track
   ```bash
   python cli.py intake <condition_id>
   ```

3. **Monitor:** Check status
   ```bash
   python cli.py status
   ```

4. **Update:** Run daily reasoning

   **Option A:** Full update (single command)
   ```bash
   python cli.py update
   ```

   **Option B:** Split update (VPN-friendly for US markets)
   ```bash
   # Step 1: On US VPN - fetch Polymarket data
   python cli.py fetch
   
   # Disconnect VPN
   
   # Step 2: Run LLM reasoning
   python cli.py reason
   ```

5. **View:** Open dashboard to see charts and reasoning
   ```bash
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

### Moonshot API rate limit errors while on VPN
If you get rate limit errors when calling Moonshot API through a VPN:

**Use the split workflow:**
```bash
# Step 1: Connect VPN, fetch data
python cli.py fetch

# Step 2: Disconnect VPN, run reasoning
python cli.py reason
```

This stores Polymarket data locally, then runs LLM calls without VPN.

### API connection errors
- Ensure backend is running on port 8000
- Check `VITE_API_URL` in `frontend/.env`

### No questions showing in dashboard
- Intake questions first using `python cli.py intake <id>`
- Run at least one update using `python cli.py update`

### Empty probability chart
- Daily logs must exist for chart to render
- Run `python cli.py update` to generate logs

### "Polymarket price: None" for region-restricted markets
Some markets (e.g., Iran-related) are US-only. The system automatically:
1. Tries CLOB API first (real-time prices)
2. Falls back to events endpoint if geo-blocked

If price is still None, check your VPN connection.

---

## How Reasoning Works

The reasoning engine (`KimiReasoningAgent`) implements a **4-step structured reasoning pipeline** inspired by superforecasting techniques. Each daily update runs this pipeline for every active question.

### Overview

```
┌─────────────────┐     ┌─────────────────────────────────────────────┐
│  Input Data     │     │         4-Step Reasoning Pipeline           │
│                 │     │                                             │
│  • Prior prob   │────▶│  Step 1: Evidence Classification            │
│  • News articles│     │         ↓                                   │
│  • Market price │     │  Step 2: Bull Case Synthesis                │
│                 │     │         ↓                                   │
└─────────────────┘     │  Step 3: Bear Case Synthesis                │
                        │         ↓                                   │
┌─────────────────┐     │  Step 4: Posterior Update + WTCMM           │
│  Output         │◄────│                                             │
│                 │     └─────────────────────────────────────────────┘
│  • Posterior    │                           │
│  • Confidence   │                           ▼
│  • WTCMM        │              ┌─────────────────────┐
│  • Bull/Bear    │              │  Bias Detection     │
│  • Summary      │              │  • Anchoring        │
└─────────────────┘              │  • Overreaction     │
                                 └─────────────────────┘
```

### The 4 Steps

#### Step 1: Evidence Classification
Each news article is classified by the LLM into one of four categories:

| Category | Description | Example |
|----------|-------------|---------|
| `supports_yes` | Evidence the event is MORE likely | "UN calls for immediate ceasefire" |
| `supports_no` | Evidence the event is LESS likely | "Israel continues military operations" |
| `neutral` | Relevant but inconclusive | "Analysis of regional geopolitics" |
| `noise` | Not relevant to the question | "Celebrity news, unrelated markets" |

This creates a structured evidence base for subsequent steps.

#### Step 2: Bull Case Synthesis
The LLM generates the **strongest possible argument for HIGHER probability** (steel-manning):
- What evidence supports the "yes" outcome?
- What trends or momentum might be building?
- What could surprise the market to the upside?
- Why might the current probability be too low?

#### Step 3: Bear Case Synthesis
The LLM generates the **strongest possible argument for LOWER probability**:
- What evidence supports the "no" outcome?
- What obstacles or resistance exist?
- What could surprise the market to the downside?
- Why might the current probability be too high?

#### Step 4: Posterior Update + WTCMM
The LLM weighs both cases and outputs:

```json
{
  "posterior_probability": 0.55,  // New belief (0.05-0.95)
  "delta": 0.05,                   // Change from prior
  "update_confidence": "medium",   // low/medium/high
  "what_would_change_my_mind": "If Israel announces troop withdrawal by March 15",
  "reasoning_summary": "Diplomatic pressure increasing but military operations continue"
}
```

**Constraints:**
- Probability bounded between **0.05-0.95** (never 0 or 1 to avoid overconfidence)
- **WTCMM** (What Would Change My Mind) must be **specific and falsifiable** — not vague "if things change"
- Divergence from market: `posterior - polymarket_price`

### Bias Detection

After reasoning, the system checks for cognitive biases:

#### Anchoring Warning
Triggers when the agent makes small updates (`< 0.02`) despite claiming high confidence for multiple consecutive days. Indicates the agent may be anchored to its prior.

#### Overreaction Warning  
Triggers on large probability swings (`> 0.15`) without proportionally strong evidence. Catches emotional/overconfident updates.

### What Gets Stored

Each daily update creates a `DailyLog` record:

| Field | Description |
|-------|-------------|
| `prior_probability` | Yesterday's belief |
| `posterior_probability` | Today's belief |
| `delta` | Magnitude of update |
| `polymarket_price` | Market's belief |
| `divergence_from_market` | Agent vs market difference |
| `bull_case` | Pro-yes argument |
| `bear_case` | Pro-no argument |
| `what_would_change_my_mind` | Falsifiable reversal condition |
| `update_confidence` | low/medium/high |
| `key_evidence` | Top supporting articles |
| `anchoring_warning` | Bias flag |
| `overreaction_warning` | Bias flag |

### Cost & Performance

- **4 API calls per question per day** (one per step)
- Each call uses `kimi-k2.5` model
- Run time scales linearly with number of questions (~30-60s per question)
- With 10 questions: ~5-10 minutes, ~40 API calls

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
