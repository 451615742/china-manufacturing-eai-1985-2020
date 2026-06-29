"""
Step 2 — Currency conversion to RMB.

Converts the 'Registered_capital' field from various foreign currencies to
unified Renminbi (CNY). Exchange rates are annual averages sourced from the
State Administration of Foreign Exchange (SAFE) for the specified reference year.

The script handles 12 foreign currencies plus two RMB denominations:
  - 万澳大利亚元, 万德国马克, 万港元, 万加元, 万美元, 万欧元,
    万日元, 万瑞士法郎, 万新加坡元, 万英镑, 万丹麦克朗, 万韩元
  - 万元人民币, 万人民币 (pass-through, rate = 1.0)

Edge case: rows whose 'Registered_capital' string matches none of the known
currency patterns receive a value of 0 in 'Registered_capital_RMB'.
This is logged as a warning per file.

Input:  CSV files with 'Registered_capital' column (post drop-columns).
Output: CSV files with added 'Registered_capital_RMB' column (suffix '_RMB').

Usage:
    python step2_currency_conversion.py --input <input_dir> --output <output_dir>
"""

import os
import argparse
import re
from glob import glob
import pandas as pd


# Annual average exchange rates to RMB (CNY).
# Source: State Administration of Foreign Exchange (SAFE).
# Reference year: adjust as needed for your data vintage.
# Units: all rates expressed as CNY per 万 (10,000) of foreign currency.
EXCHANGE_RATES = {
    '万澳大利亚元': 4.7622,
    '万德国马克':   3.9880,
    '万港元':       0.88932,
    '万加元':       5.1455,
    '万美元':       6.8976,
    '万欧元':       7.8755,
    '万日元':       0.064626,
    '万瑞士法郎':   7.3567,
    '万新加坡元':   4.9991,
    '万英镑':       8.8493,
    '万丹麦克朗':   1.056,
    '万韩元':       0.58517,
    '万元人民币':   1.0,
    '万人民币':     1.0,
}

OUTPUT_SUFFIX = '_RMB'


def convert_capital(value):
    """
    Convert a single Registered_capital string to RMB numeric value.

    Parameters
    ----------
    value : str
        Raw 'Registered_capital' cell, e.g. '100万美元'.

    Returns
    -------
    float
        Converted value in CNY. Returns 0.0 if no currency pattern matches.
    """
    value_str = str(value).replace(',', '')
    for currency, rate in EXCHANGE_RATES.items():
        if currency in value_str:
            number_str = value_str.replace(currency, '').strip()
            try:
                number = float(number_str)
            except ValueError:
                return 0.0
            return number * rate
    return 0.0


def process_file(csv_path, output_dir):
    """Convert a single CSV file's Registered_capital column to RMB."""
    df = pd.read_csv(csv_path, encoding='utf-8-sig')

    # Track zero-assignments for reporting
    df['Registered_capital_RMB'] = df['Registered_capital'].apply(convert_capital)
    zero_mask = df['Registered_capital_RMB'] == 0.0
    n_zero = zero_mask.sum()

    # Output with a stable suffix (replaces original _DROP suffix)
    base_name = os.path.splitext(os.path.basename(csv_path))[0]
    # Remove any existing step suffix to keep names clean
    base_name = base_name.replace('_DROP', '')
    output_path = os.path.join(output_dir, f"{base_name}{OUTPUT_SUFFIX}.csv")
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    return output_path, len(df), n_zero


def main():
    parser = argparse.ArgumentParser(
        description="Step 2: Convert registered capital to RMB using SAFE exchange rates."
    )
    parser.add_argument('--input', required=True,
                        help='Directory containing CSV files with Registered_capital column.')
    parser.add_argument('--output', required=True,
                        help='Directory for output CSV files.')
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    csv_files = glob(os.path.join(args.input, '*.csv'))

    if not csv_files:
        print(f"WARNING: No CSV files found in {args.input}")
        return

    total_rows = 0
    total_zero = 0
    for csv_file in csv_files:
        out_path, n_rows, n_zero = process_file(csv_file, args.output)
        pct = 100 * n_zero / n_rows if n_rows > 0 else 0
        print(f"Processed: {os.path.basename(csv_file)} → {os.path.basename(out_path)} "
              f"(rows: {n_rows}, unmatched: {n_zero} [{pct:.1f}%])")
        total_rows += n_rows
        total_zero += n_zero

    total_pct = 100 * total_zero / total_rows if total_rows > 0 else 0
    print(f"\nDone. {len(csv_files)} file(s), {total_rows} total rows. "
          f"Unmatched currencies: {total_zero} ({total_pct:.1f}%).")


if __name__ == '__main__':
    main()
