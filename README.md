# sales-vacancies

Sales, vacancies and marketing analytics for a recruiting agency: SQL queries in BigQuery, data validation and reconciliation, pipeline health monitoring and Tableau dashboards.

> **Status:** in progress. The synthetic dataset and the BigQuery load are done; queries, validation and dashboards are next. See the [roadmap](#roadmap).

## Business questions

A recruiting agency that places remote talent with US businesses needs answers to questions like:

- How long does it take to fill a vacancy, and which departments are slowest?
- Where do candidates drop out of the hiring funnel?
- Which sourcing channels produce hires, and what does a hire cost per channel?
- How much revenue do placements generate each month, and how healthy is the sales pipeline?
- Can the numbers in the final reports be trusted? (validation and reconciliation)

## Data

All data is **synthetic**, generated with Python and Faker. Relationships between tables are consistent (foreign keys, dates, funnel stages) and checked by the generator on every run.

| Table | Rows (approx.) | Description |
|---|---|---|
| `clients` | 60 | Companies hiring through the agency |
| `vacancies` | 420 | Open roles with status (filled, open, cancelled) and salary offered |
| `candidates` | 2,900 | Candidates in LATAM, with the channel they came from |
| `applications` | 7,600 | Candidate applications and the furthest stage reached |
| `placements` | 280 | Successful hires and the fee charged |
| `marketing_daily` | 2,500 | Daily spend, clicks and leads by paid channel |
| `sales_deals` | 150 | Sales pipeline (won, lost, open) |

## Tech stack

- **Python** (pandas, Faker): synthetic data generation and loading
- **Google BigQuery** (sandbox / free tier): data warehouse
- **SQL** (BigQuery): analysis queries, validation checks
- **Tableau Public**: dashboards
- **n8n**: pipeline health check

## Repository structure

```
sales-vacancies/
├── data_generation/    # Synthetic data generator
├── ingestion/          # Load CSV files into BigQuery
├── sql/                # Analysis and validation queries (coming next)
└── README.md
```

## Getting started

### Prerequisites

- Python 3.10 to 3.12
- A Google Cloud project with BigQuery enabled (sandbox mode is enough)

### Setup and run

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # fill in your GCP project ID
gcloud auth application-default login

python data_generation/generate_recruiting_data.py
python ingestion/load_to_bigquery.py
```

The load creates the dataset `recruiting` and replaces its tables on every run.

## Roadmap

- [x] Synthetic data generator with integrity checks
- [x] Load into BigQuery
- [ ] Analysis queries: time to fill, hiring funnel, cost per hire, revenue and sales pipeline
- [ ] Validation and reconciliation queries with an audit table
- [ ] Pipeline run log (`pipeline_runs`) and a simple n8n health check
- [ ] Tableau Public dashboards (sales, vacancies, marketing)

## Limitations

- The data is synthetic, so the patterns in it (for example, referrals converting best) were built into the generator and do not describe a real company.
- The BigQuery sandbox deletes tables after 60 days. Re-running the load recreates them.

## Author

**Macarena Rios**: Geographic and Environmental Engineer, MSc student in Artificial Intelligence Sciences (UNA). Moving from GIS and data science toward data engineering.

[LinkedIn](https://www.linkedin.com/in/YOUR-PROFILE) · [GitHub](https://github.com/mykurena)
