"""
Step 1 — Deduplication and column removal.

Performs two operations on enterprise registration CSV files:

1. **Deduplication:** Where duplicate records exist for the same firm (identified
   by the `--dedup-key` column, e.g. enterprise name), only the record with the
   highest 'Registered_capital' is retained, ensuring one unique record per firm
   per input file. This matches the criterion described in the accompanying paper.

2. **Column removal:** Drops the 'LAR' (Legal Address Representative) and
   'Address' columns, which are not needed for subsequent processing and contain
   privacy-sensitive address strings.

Input:  CSV files with full NECIPS registration fields.
Output: CSV files, deduplicated and with LAR/Address removed (suffix '_DROP').

Usage:
    python step1_drop_columns.py --input <input_dir> --output <output_dir> [--dedup-key Enterprise_name]
"""

import os
import argparse
from glob import glob
import pandas as pd


COLUMNS_TO_DROP = ['LAR', 'Address']
OUTPUT_SUFFIX = '_DROP'


def deduplicate(df, key_column, capital_column='Registered_capital'):
    """
    Deduplicate records: for each group sharing the same key_column value,
    keep the row with the maximum capital_column value.

    Parameters
    ----------
    df : pandas.DataFrame
        Input data.
    key_column : str
        Column name that identifies a unique firm (e.g. enterprise name or
        unified social credit code).
    capital_column : str
        Column name for registered capital.

    Returns
    -------
    pandas.DataFrame
        Deduplicated data (one row per unique key value).
    """
    if key_column not in df.columns:
        print(f"    WARNING: dedup key '{key_column}' not found in columns. "
              f"Skipping dedup for this file.")
        return df

    if capital_column not in df.columns:
        print(f"    WARNING: capital column '{capital_column}' not found. "
              f"Keeping first occurrence per group.")
        return df.groupby(key_column, as_index=False).first()

    # Parse capital as numeric for comparison (handle strings with commas)
    def _parse_capital(val):
        try:
            return float(str(val).replace(',', '').replace(' ', ''))
        except (ValueError, TypeError):
            return 0.0

    df = df.copy()
    df['_capital_num'] = df[capital_column].apply(_parse_capital)

    # Sort descending by capital, then drop duplicates keeping first (highest)
    df_sorted = df.sort_values('_capital_num', ascending=False)
    df_dedup = df_sorted.drop_duplicates(subset=key_column, keep='first')
    df_dedup = df_dedup.drop(columns=['_capital_num'])
    return df_dedup


def process_file(csv_path, output_dir, dedup_key=None):
    """Deduplicate (if key provided) and drop columns from a single CSV file."""
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    n_before = len(df)
    n_dup = 0

    if dedup_key:
        df = deduplicate(df, dedup_key)
        n_dup = n_before - len(df)

    df = df.drop(columns=COLUMNS_TO_DROP, errors='ignore')

    base_name = os.path.splitext(os.path.basename(csv_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}{OUTPUT_SUFFIX}.csv")
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    return output_path, n_before, len(df), n_dup


def main():
    parser = argparse.ArgumentParser(
        description="Step 1: Deduplicate (optional) and drop LAR/Address columns "
                    "from NECIPS CSV files."
    )
    parser.add_argument('--input', required=True,
                        help='Directory containing input CSV files.')
    parser.add_argument('--output', required=True,
                        help='Directory for output CSV files.')
    parser.add_argument('--dedup-key', default=None,
                        help='Column name identifying unique firms for deduplication '
                             '(e.g. Enterprise_name). If omitted, dedup is skipped.')
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    csv_files = glob(os.path.join(args.input, '*.csv'))

    if not csv_files:
        print(f"WARNING: No CSV files found in {args.input}")
        return

    total_before = 0
    total_after = 0
    total_dup = 0

    for csv_file in csv_files:
        out_path, n_before, n_after, n_dup = process_file(
            csv_file, args.output, args.dedup_key
        )
        dup_info = f", duplicates removed: {n_dup}" if args.dedup_key else ""
        print(f"Processed: {os.path.basename(csv_file)} → {os.path.basename(out_path)} "
              f"(rows: {n_before} → {n_after}{dup_info})")
        total_before += n_before
        total_after += n_after
        total_dup += n_dup

    if args.dedup_key:
        print(f"\nDone. {len(csv_files)} file(s) processed. "
              f"Total rows: {total_before} → {total_after} "
              f"({total_dup} duplicates removed).")
    else:
        print(f"\nDone. {len(csv_files)} file(s) processed. "
              f"Total rows retained: {total_after}.")


if __name__ == '__main__':
    main()
