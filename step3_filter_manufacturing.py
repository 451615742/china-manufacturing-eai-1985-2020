"""Filter manufacturing enterprises for a target year."""
import argparse
from pathlib import Path
import pandas as pd


def is_manufacturing(code):
    try:
        value = int(str(code).strip()[:2])
        return 13 <= value <= 42
    except (TypeError, ValueError):
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--industry-column", default="industry_code")
    parser.add_argument("--establishment-column", default="establishment_year")
    parser.add_argument("--approval-column", default="approval_year")
    parser.add_argument("--status-column", default="registration_status")
    args = parser.parse_args()
    target = Path(args.output)
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(Path(args.input).glob("*.csv")):
        frame = pd.read_csv(path)
        frame = frame[frame[args.industry_column].map(is_manufacturing)]
        founded = pd.to_numeric(frame[args.establishment_column], errors="coerce")
        approved = pd.to_numeric(frame[args.approval_column], errors="coerce")
        active = (founded <= args.year) & (approved.isna() | (approved >= args.year))
        frame[active].to_csv(target / path.name, index=False)


if __name__ == "__main__":
    main()
