"""Convert registered capital to CNY using a supplied exchange-rate table."""
import argparse
import json
from pathlib import Path
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--rates-json", required=True,
                        help="JSON mapping currency code to CNY conversion factor")
    parser.add_argument("--amount-column", default="registered_capital")
    parser.add_argument("--currency-column", default="currency")
    args = parser.parse_args()
    rates = json.loads(Path(args.rates_json).read_text(encoding="utf-8"))
    target = Path(args.output)
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(Path(args.input).glob("*.csv")):
        frame = pd.read_csv(path)
        if args.amount_column in frame and args.currency_column in frame:
            frame[args.amount_column] = (
                pd.to_numeric(frame[args.amount_column], errors="coerce")
                * frame[args.currency_column].map(rates)
            )
        frame.to_csv(target / path.name, index=False)


if __name__ == "__main__":
    main()
