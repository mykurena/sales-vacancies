"""Corrupt the generated CSV files on purpose, to demo the validation checks and the alert.

Run it between generating and loading the data:
    python data_generation/generate_recruiting_data.py
    python data_generation/inject_issues.py
    python ingestion/load_to_bigquery.py

Problems injected:
    1. A client is removed, so its vacancies become orphans
    2. A placement is duplicated
    3. A filled vacancy loses its close date
    4. Three marketing rows get a negative spend
    5. A won deal loses its client

To go back to clean data, run generate_recruiting_data.py and the loader again.
"""
from pathlib import Path

import pandas as pd

DATA_DIR = Path("data/generated")


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / f"{name}.csv")


def write(name: str, df: pd.DataFrame) -> None:
    df.to_csv(DATA_DIR / f"{name}.csv", index=False)


def main() -> None:
    if not (DATA_DIR / "clients.csv").exists():
        raise SystemExit("No generated data found. Run data_generation/generate_recruiting_data.py first.")

    clients, vacancies = read("clients"), read("vacancies")
    placements, marketing, deals = read("placements"), read("marketing_daily"), read("sales_deals")

    # 1. orphan vacancies: remove the client with the fewest vacancies
    client_id = vacancies["client_id"].value_counts().sort_values().index[0]
    orphaned = int((vacancies["client_id"] == client_id).sum())
    clients = clients[clients["client_id"] != client_id]

    # 2. duplicated placement
    placements = pd.concat([placements, placements.iloc[[0]]], ignore_index=True)

    # 3. filled vacancy without close date
    filled = vacancies.index[vacancies["status"] == "filled"][0]
    vacancies.loc[filled, "closed_at"] = None

    # 4. negative marketing spend
    rows = marketing.index[:3]
    marketing.loc[rows, "spend_usd"] = -marketing.loc[rows, "spend_usd"].abs()

    # 5. won deal without client
    won = deals.index[deals["stage"] == "won"][0]
    deals.loc[won, "client_id"] = None

    for name, df in [("clients", clients), ("vacancies", vacancies), ("placements", placements),
                     ("marketing_daily", marketing), ("sales_deals", deals)]:
        write(name, df)

    print("Issues injected:")
    print(f"  - client {client_id} removed ({orphaned} vacancies now orphaned)")
    print("  - 1 placement duplicated")
    print("  - 1 filled vacancy without close date")
    print("  - 3 marketing rows with negative spend")
    print("  - 1 won deal without client")


if __name__ == "__main__":
    main()
