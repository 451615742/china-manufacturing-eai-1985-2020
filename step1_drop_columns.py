"""Remove privacy-sensitive columns from source CSV files."""
import argparse
from pathlib import Path
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--drop", nargs="*", default=["LAR", "Address"])
    args = parser.parse_args()
    source = Path(args.input)
    target = Path(args.output)
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.glob("*.csv")):
        frame = pd.read_csv(path)
        drop = [c for c in args.drop if c in frame.columns]
        frame.drop(columns=drop).to_csv(target / path.name, index=False)


if __name__ == "__main__":
    main()
