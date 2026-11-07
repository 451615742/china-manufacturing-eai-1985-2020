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


def target_year_mask(founded, approved, status, year):
    """Apply the three alternative temporal inclusion rules."""
    founded = pd.to_numeric(founded, errors="coerce")
    approved = pd.to_numeric(approved, errors="coerce")
    surviving = status.astype("string").str.strip().eq("存续").fillna(False)
    registered_this_year = founded.eq(year)
    registered_earlier = founded.lt(year)
    approved_in_or_after_year = registered_earlier & approved.ge(year)
    approved_earlier_and_surviving = registered_earlier & approved.lt(year) & surviving
    return registered_this_year | approved_in_or_after_year | approved_earlier_and_surviving


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--industry-column", default="industry_code")
    parser.add_argument("--establishment-column", default="establishment_year")
    parser.add_argument("--approval-column", default="approval_year")
    parser.add_argument("--status-column", default="registration_status",
                        help="Registration status field; 存续 denotes a surviving enterprise.")
    args = parser.parse_args()
    target = Path(args.output)
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(Path(args.input).glob("*.csv")):
        frame = pd.read_csv(path)
        frame = frame[frame[args.industry_column].map(is_manufacturing)]
        eligible = target_year_mask(frame[args.establishment_column],
                                    frame[args.approval_column],
                                    frame[args.status_column], args.year)
        frame.loc[eligible].to_csv(target / path.name, index=False)


if __name__ == "__main__":
    main()
