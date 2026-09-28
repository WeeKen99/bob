# GoldView: AI-Accelerated Golden Customer Record Pipeline

> A hackathon project built with IBM Bob — consolidating fragmented banking customer data into a single trusted identity.

## 📁 Project Structure

```
bob-a-thon/
├── frontend/              # Frontend web app (Vite)
│   ├── src/               # main.js, style.css
│   └── index.html         # Vite entry point
├── backend/               # Backend API server (Express)
│   ├── src/               # index.js
│   └── routes/            # health.js, golden.js
├── use-case-1/            # Golden Customer Record use case
│   ├── data/
│   │   ├── source/        # core_banking.csv, credit_card.csv, mortgage.csv
│   │   └── output/        # golden_customers.csv, duplicate_log.csv
│   ├── schema/            # golden_customer.schema.json
│   ├── etl/               # golden_etl.py
│   └── tests/             # test_golden_etl.py (34 tests)
├── docs/                  # Architecture documentation
└── README.md
```

## 🚀 Getting Started

### Prerequisites
- Node.js v18+
- Python 3.10+
- npm

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at **http://localhost:5173**

### Backend

```bash
cd backend
npm install
node src/index.js
```

API available at **http://localhost:3000**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/golden` | GET | Returns summary stats, golden customer records, and duplicate log |

### Golden Customer ETL (Use Case 1)

```bash
cd use-case-1
python etl/golden_etl.py
```

Run tests:

```bash
python -m pytest tests/test_golden_etl.py -v
```

## 🛠️ Tech Stack

- **Frontend:** Vite (vanilla JS) — GoldView dashboard at `localhost:5173`
- **Backend:** Node.js, Express, csv-parse, CORS, dotenv — REST API at `localhost:3000`
- **ETL:** Python 3.10+ (standard library only, zero external deps)
- **Schema:** JSON Schema Draft-07
- **Tests:** pytest — 34 passing
- **AI Partner:** IBM Bob (AI SDLC Partner)

## 📦 Use Cases

| # | Title | Description |
|---|-------|-------------|
| 1 | Golden Customer Record | ETL pipeline that consolidates core banking, credit card, and mortgage data into a unified golden customer schema with fuzzy deduplication |

## 👥 Team

- WeeKen99

## 📄 License

MIT
