"""Generate synthetic data for a recruiting agency that places remote talent with US businesses.

Tables written to data/generated/ as CSV:
    clients, vacancies, candidates, applications, placements, marketing_daily, sales_deals

Everything is synthetic. Relationships are consistent (foreign keys, dates, funnel stages),
so the data can be used to practice SQL, validation and dashboards.

Usage:
    python data_generation/generate_recruiting_data.py
"""
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

SEED = 11
START = date(2025, 1, 1)
END = date(2026, 9, 30)
OUTPUT_DIR = Path("data/generated")

INDUSTRIES = ["E-commerce", "Real estate", "Healthcare", "Financial services", "Marketing agency", "Logistics", "SaaS"]
ROLES = {
    "Customer Support": ["Customer Support Representative", "Support Team Lead"],
    "Sales": ["Sales Development Rep", "Account Executive"],
    "Operations": ["Virtual Assistant", "Operations Coordinator"],
    "Marketing": ["Social Media Manager", "Content Writer"],
    "Finance": ["Bookkeeper", "Accounts Payable Specialist"],
    "Data": ["Data Analyst", "BI Developer"],
    "Engineering": ["QA Analyst", "Full Stack Developer"],
}
SALARY_BASE = {"junior": 1100, "mid": 1800, "senior": 2600}
LATAM = ["Colombia", "Mexico", "Argentina", "Brazil", "Peru", "Chile", "Paraguay", "Costa Rica", "Dominican Republic"]
LATAM_W = [0.18, 0.17, 0.14, 0.14, 0.09, 0.08, 0.06, 0.07, 0.07]
CHANNELS = ["LinkedIn Ads", "Google Ads", "Job boards", "Meta Ads", "Referral", "Outbound"]
CHANNEL_W = [0.22, 0.12, 0.26, 0.10, 0.16, 0.14]
HIRE_QUALITY = {"LinkedIn Ads": 1.2, "Google Ads": 0.8, "Job boards": 1.0, "Meta Ads": 0.6, "Referral": 3.0, "Outbound": 1.5}
STAGES = ["applied", "screened", "interview", "offer"]
STAGE_P = [0.52, 0.27, 0.15, 0.06]
PAID = {
    # channel: (campaign, base daily spend USD, cost per click, click-through rate, lead conversion)
    "LinkedIn Ads": ("candidate_sourcing", 45.0, 2.1, 0.008, 0.06),
    "Google Ads": ("candidate_sourcing", 30.0, 1.3, 0.030, 0.05),
    "Job boards": ("job_posts", 25.0, 0.9, 0.020, 0.09),
    "Meta Ads": ("brand_awareness", 18.0, 0.7, 0.012, 0.03),
}


def rand_date(rng, lo: date, hi: date) -> date:
    return lo + timedelta(days=int(rng.integers(0, (hi - lo).days + 1)))


def build_clients(rng, fake) -> pd.DataFrame:
    rows = []
    for i in range(60):
        rows.append(
            {
                "client_id": f"c_{i + 1:03d}",
                "company_name": fake.company(),
                "industry": str(rng.choice(INDUSTRIES)),
                "country": str(rng.choice(["United States", "Canada", "United Kingdom"], p=[0.88, 0.07, 0.05])),
                "signed_at": rand_date(rng, date(2024, 6, 1), date(2026, 6, 30)),
            }
        )
    return pd.DataFrame(rows)


def build_vacancies(rng, clients: pd.DataFrame) -> pd.DataFrame:
    weights = rng.lognormal(0, 0.8, len(clients))
    weights = weights / weights.sum()
    rows = []
    for i in range(420):
        client = clients.iloc[int(rng.choice(len(clients), p=weights))]
        lo = max(START, client["signed_at"])
        opened = rand_date(rng, lo, END - timedelta(days=5))
        department = str(rng.choice(list(ROLES)))
        title = str(rng.choice(ROLES[department]))
        seniority = str(rng.choice(["junior", "mid", "senior"], p=[0.35, 0.45, 0.20]))
        factor = 1.25 if department in ("Data", "Engineering") else 1.0
        salary = int(round(SALARY_BASE[seniority] * factor * rng.normal(1, 0.1) / 10) * 10)

        old = opened < END - timedelta(days=120)
        p = [0.78, 0.22, 0.0] if old else [0.62, 0.13, 0.25]
        status = str(rng.choice(["filled", "cancelled", "open"], p=p))
        closed = None
        if status == "filled":
            days = int(np.clip(rng.gamma(4, 10), 7, 120))
            closed = opened + timedelta(days=days)
        elif status == "cancelled":
            closed = opened + timedelta(days=int(rng.integers(10, 60)))
        if closed is not None and closed > END:
            status, closed = "open", None

        rows.append(
            {
                "vacancy_id": f"v_{i + 1:04d}",
                "client_id": client["client_id"],
                "role_title": title,
                "department": department,
                "seniority": seniority,
                "opened_at": opened,
                "closed_at": closed,
                "status": status,
                "salary_offered_usd_month": salary,
            }
        )
    return pd.DataFrame(rows)


def build_applications_and_candidates(rng, vacancies: pd.DataFrame):
    pool = 3200
    pool_channel = rng.choice(CHANNELS, size=pool, p=CHANNEL_W)
    pool_country = rng.choice(LATAM, size=pool, p=LATAM_W)
    quality = np.array([HIRE_QUALITY[c] for c in pool_channel])

    app_rows = []
    hired = {}  # vacancy_id -> candidate index
    for _, v in vacancies.iterrows():
        n = int(rng.poisson(15)) + 3
        idx = rng.choice(pool, size=n, replace=False)
        window_end = v["closed_at"] if v["closed_at"] is not None else END
        hired_idx = None
        if v["status"] == "filled":
            w = quality[idx] / quality[idx].sum()
            hired_idx = int(rng.choice(idx, p=w))
            hired[v["vacancy_id"]] = hired_idx
        for c in idx:
            stage = "hired" if c == hired_idx else str(rng.choice(STAGES, p=STAGE_P))
            app_rows.append(
                {
                    "vacancy_id": v["vacancy_id"],
                    "candidate_id": f"cand_{int(c) + 1:05d}",
                    "applied_at": rand_date(rng, v["opened_at"], window_end),
                    "furthest_stage": stage,
                }
            )

    applications = pd.DataFrame(app_rows)
    applications.insert(0, "application_id", [f"app_{i + 1:06d}" for i in range(len(applications))])

    first_seen = applications.groupby("candidate_id")["applied_at"].min().rename("created_at")
    candidates = first_seen.reset_index()
    cand_idx = candidates["candidate_id"].str[5:].astype(int) - 1
    candidates["country"] = pool_country[cand_idx]
    candidates["source_channel"] = pool_channel[cand_idx]
    candidates = candidates[["candidate_id", "country", "source_channel", "created_at"]]
    return applications, candidates, hired


def build_placements(rng, vacancies: pd.DataFrame, hired: dict) -> pd.DataFrame:
    rows = []
    filled = vacancies[vacancies["status"] == "filled"]
    for i, (_, v) in enumerate(filled.iterrows()):
        monthly = round(v["salary_offered_usd_month"] * rng.uniform(0.95, 1.05))
        rows.append(
            {
                "placement_id": f"p_{i + 1:04d}",
                "vacancy_id": v["vacancy_id"],
                "candidate_id": f"cand_{hired[v['vacancy_id']] + 1:05d}",
                "placed_at": v["closed_at"],
                "monthly_salary_usd": int(monthly),
                "placement_fee_usd": round(float(monthly * rng.uniform(1.0, 1.5)), 2),
            }
        )
    return pd.DataFrame(rows)


def build_marketing(rng) -> pd.DataFrame:
    dates = pd.date_range(START, END, freq="D")
    frames = []
    for channel, (campaign, base, cpc, ctr, conv) in PAID.items():
        trend = np.linspace(0.8, 1.3, len(dates))
        weekday = np.where(dates.dayofweek < 5, 1.1, 0.8)
        spend = base * trend * weekday * rng.normal(1, 0.12, len(dates)).clip(0.5, None)
        clicks = (spend / (cpc * rng.normal(1, 0.08, len(dates)).clip(0.5, None))).round().astype(int)
        impressions = (clicks / (ctr * rng.normal(1, 0.1, len(dates)).clip(0.5, None))).round().astype(int)
        leads = rng.binomial(clicks, conv)
        frames.append(
            pd.DataFrame(
                {
                    "date": dates.date,
                    "channel": channel,
                    "campaign_name": campaign,
                    "spend_usd": spend.round(2),
                    "impressions": impressions,
                    "clicks": clicks,
                    "leads": leads,
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def build_sales_deals(rng, fake, clients: pd.DataFrame) -> pd.DataFrame:
    reps = [fake.first_name() for _ in range(5)]
    rows = []
    for i in range(150):
        created = rand_date(rng, START, END - timedelta(days=3))
        recent = created > END - timedelta(days=60)
        stage = str(rng.choice(["won", "lost", "open"], p=[0.30, 0.30, 0.40] if recent else [0.47, 0.53, 0.0]))
        closed = None
        if stage != "open":
            closed = created + timedelta(days=int(np.clip(rng.gamma(3, 9), 3, 90)))
            if closed > END:
                stage, closed = "open", None
        rows.append(
            {
                "deal_id": f"d_{i + 1:04d}",
                "owner": str(rng.choice(reps)),
                "stage": stage,
                "amount_usd": round(float(rng.lognormal(8.0, 0.5)), 2),
                "created_at": created,
                "closed_at": closed,
                "client_id": str(rng.choice(clients["client_id"])) if stage == "won" else None,
            }
        )
    return pd.DataFrame(rows)


def check_integrity(t: dict) -> None:
    assert t["vacancies"]["client_id"].isin(t["clients"]["client_id"]).all()
    assert t["applications"]["vacancy_id"].isin(t["vacancies"]["vacancy_id"]).all()
    assert t["applications"]["candidate_id"].isin(t["candidates"]["candidate_id"]).all()
    assert t["placements"]["vacancy_id"].isin(t["vacancies"]["vacancy_id"]).all()
    assert t["placements"]["candidate_id"].isin(t["candidates"]["candidate_id"]).all()
    assert (t["vacancies"]["status"].eq("filled").sum() == len(t["placements"]))
    hired = t["applications"][t["applications"]["furthest_stage"] == "hired"]
    assert len(hired) == len(t["placements"])
    closed = t["vacancies"].dropna(subset=["closed_at"])
    assert (closed["closed_at"] >= closed["opened_at"]).all()
    assert t["vacancies"][t["vacancies"]["status"] == "open"]["closed_at"].isna().all()


def main() -> None:
    rng = np.random.default_rng(SEED)
    Faker.seed(SEED)
    fake = Faker()

    clients = build_clients(rng, fake)
    vacancies = build_vacancies(rng, clients)
    applications, candidates, hired = build_applications_and_candidates(rng, vacancies)
    placements = build_placements(rng, vacancies, hired)
    marketing = build_marketing(rng)
    deals = build_sales_deals(rng, fake, clients)

    tables = {
        "clients": clients,
        "vacancies": vacancies,
        "candidates": candidates,
        "applications": applications,
        "placements": placements,
        "marketing_daily": marketing,
        "sales_deals": deals,
    }
    check_integrity(tables)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)
        print(f"  {name}: {len(df):,} rows")
    print("Integrity checks passed. Files written to", OUTPUT_DIR)


if __name__ == "__main__":
    main()
