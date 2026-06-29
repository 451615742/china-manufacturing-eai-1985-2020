"""
Step 3 — Manufacturing enterprise filtering.

Filters enterprise records to retain only active manufacturing enterprises
(Category C, GB/T 4754) meeting temporal existence criteria for a target year.

Filtering logic (for a given target_year):
  1. Founded IN target_year (new entrants)
  2. Founded BEFORE target_year AND approved in or after target_year (ongoing)
  3. Founded BEFORE target_year AND approved BEFORE target_year
     AND registration status is '存续' (still active)

All three temporal conditions additionally require:
  - industry_code == 'C' (Manufacturing sector)
  - sub_industry_code != 43 (excluded; see Notes)

Output is split into chunks ≤ ROW_LIMIT rows to respect the 2 GB SHP file size
limit for subsequent spatial join operations.

Input:  CSV files with industry_code, sub_industry_code, Date_of_Incorporation,
        Approval_date, Registration_status columns (post currency conversion).
Output: Filtered CSV files with the above criteria applied, plus a merged file.

Usage:
    python step3_filter_manufacturing.py --input <input_dir> --output <output_dir> --year 2015
"""

import os
import argparse
import pandas as pd

# Maximum rows per output chunk to stay under 2 GB SHP limit
ROW_LIMIT = 2_030_000


def filter_manufacturing(data, target_year):
    """
    Apply manufacturing-sector temporal existence filter.

    Parameters
    ----------
    data : pandas.DataFrame
        Enterprise records.
    target_year : int
        Target time-slice year.

    Returns
    -------
    pandas.DataFrame
        Filtered subset.
    """
    # Parse dates (coerce errors to NaT)
    incorp_year = pd.to_datetime(
        data['Date_of_Incorporation'], errors='coerce'
    ).dt.year
    approv_year = pd.to_datetime(
        data['Approval_date'], errors='coerce'
    ).dt.year

    # Temporal existence conditions
    cond_new = (incorp_year == target_year)
    cond_ongoing = (incorp_year < target_year) & (approv_year >= target_year)
    cond_surviving = (
        (incorp_year < target_year) &
        (approv_year < target_year) &
        (data['Registration_status'] == '存续')
    )

    # Sector conditions
    cond_manufacturing = (data['industry_code'] == 'C')
    cond_exclude_43 = ~data['sub_industry_code'].isin([43])

    final_condition = (
        (cond_new | cond_ongoing | cond_surviving) &
        cond_manufacturing &
        cond_exclude_43
    )
    return data[final_condition].copy()


def split_and_save(filtered_data, output_dir, file_label, row_limit=ROW_LIMIT):
    """
    Save filtered data, splitting into chunks if it exceeds row_limit.

    Returns list of output file paths.
    """
    n_rows = len(filtered_data)
    paths = []

    if n_rows <= row_limit:
        path = os.path.join(output_dir, f"filtered_{file_label}.csv")
        filtered_data.to_csv(path, index=False, encoding='utf-8-sig')
        paths.append(path)
        return paths

    n_chunks = (n_rows // row_limit) + 1
    for i in range(n_chunks):
        chunk = filtered_data.iloc[i * row_limit:(i + 1) * row_limit]
        path = os.path.join(output_dir, f"filtered_{file_label}_part{i + 1}.csv")
        chunk.to_csv(path, index=False, encoding='utf-8-sig')
        paths.append(path)
        print(f"  Chunk {i + 1}/{n_chunks}: {len(chunk)} rows → {os.path.basename(path)}")

    return paths


def main():
    parser = argparse.ArgumentParser(
        description="Step 3: Filter manufacturing enterprises for a target year."
    )
    parser.add_argument('--input', required=True,
                        help='Directory containing post-currency-conversion CSV files.')
    parser.add_argument('--output', required=True,
                        help='Directory for filtered output CSV files.')
    parser.add_argument('--year', type=int, required=True,
                        help='Target time-slice year (e.g. 2015).')
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # Collect all filtered data for merged output
    all_filtered = []

    for root, dirs, files in os.walk(args.input):
        for fname in files:
            if not fname.endswith('.csv'):
                continue
            fpath = os.path.join(root, fname)
            df = pd.read_csv(fpath, encoding='utf-8-sig')
            filtered = filter_manufacturing(df, args.year)

            if filtered.empty:
                print(f"No matches: {fname}")
                continue

            file_label = os.path.splitext(fname)[0]
            split_and_save(filtered, args.output, file_label)
            all_filtered.append(filtered)
            print(f"Filtered: {fname} → {len(filtered)} rows retained "
                  f"(out of {len(df)})")

    if not all_filtered:
        print("WARNING: No records matched the filtering criteria.")
        return

    # Merge all filtered data
    merged = pd.concat(all_filtered, ignore_index=True)
    merged_path = os.path.join(args.output, f"merged_filtered_{args.year}.csv")
    merged.to_csv(merged_path, index=False, encoding='utf-8-sig')
    print(f"\nMerged all filtered data: {len(merged)} rows → "
          f"{os.path.basename(merged_path)}")

    # If merged exceeds row limit, also split it
    if len(merged) > ROW_LIMIT:
        print(f"Merged file exceeds {ROW_LIMIT} rows; creating split copies:")
        split_and_save(merged, args.output, f"merged_{args.year}")

    print(f"\nDone. Target year: {args.year}. Total retained: {len(merged)} "
          f"manufacturing enterprise records.")


if __name__ == '__main__':
    main()
