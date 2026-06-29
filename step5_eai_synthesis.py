"""
Step 5 — EAI (Economic Activity Intensity) synthesis.

The five-step computational pipeline:
  1. Gaussian kernel smoothing (σ = 1.0 grid-cell units ≡ 1,000 m)
  2. Logarithmic transformation (ln(x + 1))
  3. Min-max normalisation ([0, 1])
  4. CRITIC objective weighting
  5. Weighted synthesis and scaling ([0, 100])

Runs independently for each year. Outputs final_score_100 as both SHP and
GeoTIFF (Float32, Albers Equal-Area Conic projection).

Usage:
    python step5_eai_synthesis.py \
        --input-root <source_root> \
        --output-root <output_root> \
        --years 1985,1990,...,2020 \
        [--sigma 0.4] [--resolution 1000]

Dependencies:
    geopandas, numpy, pandas, scipy, scikit-learn, rasterio
"""

import os
import argparse
import geopandas as gpd
import numpy as np
from scipy.ndimage import gaussian_filter
from sklearn.preprocessing import MinMaxScaler

# Import shared utilities from the companion module
from eai_utils import (
    point_to_index,
    calculate_critic_weights,
    save_raster,
)


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process_single_grid(input_shp, output_folder, count_field, scale_field,
                        sigma, resolution):
    """
    Run the full five-step EAI pipeline on one grid shapefile.

    Parameters
    ----------
    input_shp : str
        Path to input grid shapefile (must contain count_field & scale_field).
    output_folder : str
        Directory for output SHP and TIF files.
    count_field, scale_field : str
        Column names for enterprise count and total registered capital.
    sigma : float
        Gaussian kernel sigma in grid-cell units.
    resolution : float
        Grid cell size (metres).

    Returns
    -------
    bool
        True on success.
    """
    base_name = os.path.basename(input_shp).replace('.shp', '')
    output_shp = os.path.join(output_folder, f"{base_name}_final.shp")
    output_tif = os.path.join(output_folder, f"{base_name}_final.tif")

    print(f"  Processing: {input_shp}")

    if not os.path.exists(input_shp):
        print(f"    ERROR: File not found: {input_shp}")
        return False

    gdf = gpd.read_file(input_shp)

    if count_field not in gdf.columns or scale_field not in gdf.columns:
        print(f"    SKIP: Missing required fields ({count_field}, {scale_field})")
        return False

    if gdf.crs.is_geographic:
        print(f"    SKIP: CRS is geographic; must be projected (Albers).")
        return False

    # -- Grid dimensions --
    xmin, ymin, xmax, ymax = gdf.total_bounds
    width = int(np.ceil((xmax - xmin) / resolution))
    height = int(np.ceil((ymax - ymin) / resolution))

    # -- Step 1: Rasterise + Gaussian smoothing --
    count_raster = np.full((height, width), np.nan, dtype=np.float32)
    scale_raster = np.full((height, width), np.nan, dtype=np.float32)

    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        centroid = geom.centroid
        c, r = point_to_index(centroid.x, centroid.y, xmin, ymax, resolution)
        if 0 <= r < height and 0 <= c < width:
            count_raster[r, c] = row[count_field]
            scale_raster[r, c] = row[scale_field]

    count_mask = np.isnan(count_raster)
    scale_mask = np.isnan(scale_raster)

    smooth_count = gaussian_filter(
        np.nan_to_num(count_raster), sigma=sigma,
        mode='constant', cval=0.0, truncate=3.0
    )
    smooth_scale = gaussian_filter(
        np.nan_to_num(scale_raster), sigma=sigma,
        mode='constant', cval=0.0, truncate=3.0
    )

    smooth_count[count_mask] = np.nan
    smooth_scale[scale_mask] = np.nan

    # Sample smoothed values back to vector
    smooth_cnt_vals = []
    smooth_scl_vals = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            smooth_cnt_vals.append(0)
            smooth_scl_vals.append(0)
            continue
        centroid = geom.centroid
        c, r = point_to_index(centroid.x, centroid.y, xmin, ymax, resolution)
        if 0 <= r < height and 0 <= c < width:
            vc = smooth_count[r, c]
            vs = smooth_scale[r, c]
            smooth_cnt_vals.append(vc if not np.isnan(vc) else 0)
            smooth_scl_vals.append(vs if not np.isnan(vs) else 0)
        else:
            smooth_cnt_vals.append(0)
            smooth_scl_vals.append(0)

    gdf["smooth_cnt"] = smooth_cnt_vals
    gdf["smooth_scl"] = smooth_scl_vals

    # -- Step 2: Log transform --
    gdf["log_cnt"] = np.log(gdf["smooth_cnt"] + 1)
    gdf["log_scl"] = np.log(gdf["smooth_scl"] + 1)

    # -- Step 3: Min-max normalisation --
    scaler = MinMaxScaler()
    norm_data = scaler.fit_transform(gdf[["log_cnt", "log_scl"]])
    gdf["norm_cnt"] = norm_data[:, 0]
    gdf["norm_scl"] = norm_data[:, 1]

    # -- Step 4: CRITIC weighting --
    weights = calculate_critic_weights(gdf, ["norm_cnt", "norm_scl"])
    w_cnt = weights["norm_cnt"]
    w_scl = weights["norm_scl"]
    print(f"    CRITIC weights: w_cnt={w_cnt:.4f}, w_scl={w_scl:.4f}")

    # -- Step 5: Weighted synthesis ([0, 100]) --
    gdf["final_score_raw"] = gdf["norm_cnt"] * w_cnt + gdf["norm_scl"] * w_scl
    final_scaler = MinMaxScaler(feature_range=(0, 100))
    gdf["final_score_100"] = final_scaler.fit_transform(gdf[["final_score_raw"]])

    # -- Output --
    gdf.to_file(output_shp, encoding='utf-8')
    save_raster(gdf, "final_score_100", output_tif, resolution)

    print(f"    Done: {base_name}")
    return True


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Step 5: Five-step EAI synthesis pipeline."
    )
    parser.add_argument('--input-root', required=True,
                        help='Root directory containing year subdirectories '
                             '(each with A/B/C... subfolders containing grid_albers.shp).')
    parser.add_argument('--output-root', required=True,
                        help='Root directory for output (mirrors input structure).')
    parser.add_argument('--years', required=True,
                        help='Comma-separated list of target years, e.g. '
                             '"2020,2015,2010,2005,2000,1995,1990,1985".')
    parser.add_argument('--sigma', type=float, default=1.0,
                        help='Gaussian kernel sigma in grid-cell units '
                             '(default: 1.0 → 1,000 m at 1 km resolution).')
    parser.add_argument('--resolution', type=float, default=1000,
                        help='Grid resolution in metres (default: 1000).')
    parser.add_argument('--count-field', default='Enterprise',
                        help='Column name for enterprise count (default: Enterprise).')
    parser.add_argument('--scale-field', default='Total_capi',
                        help='Column name for total registered capital '
                             '(default: Total_capi).')
    args = parser.parse_args()

    target_years = [y.strip() for y in args.years.split(',')]

    for target_year in target_years:
        print(f"\n{'='*50}")
        print(f"  Year: {target_year}")
        print(f"{'='*50}")

        input_year_dir = os.path.join(args.input_root, target_year)
        output_year_dir = os.path.join(args.output_root, target_year)

        if not os.path.exists(input_year_dir):
            print(f"  ERROR: Source directory not found: {input_year_dir}")
            continue

        os.makedirs(output_year_dir, exist_ok=True)

        # Discover sub-folders (A, B, C, ...)
        subfolders = sorted([
            d for d in os.listdir(input_year_dir)
            if os.path.isdir(os.path.join(input_year_dir, d))
        ])

        total = 0
        success = 0
        for folder in subfolders:
            src_folder = os.path.join(input_year_dir, folder)
            out_folder = os.path.join(output_year_dir, folder)
            os.makedirs(out_folder, exist_ok=True)

            shp_path = os.path.join(src_folder, "grid_albers.shp")
            if not os.path.exists(shp_path):
                print(f"  WARNING: grid_albers.shp not found in {folder}, skipping.")
                continue

            total += 1
            if process_single_grid(
                shp_path, out_folder,
                args.count_field, args.scale_field,
                args.sigma, args.resolution
            ):
                success += 1

        print(f"\n  Year {target_year} complete: {success}/{total} succeeded.")

    print("\n" + "=" * 50)
    print("  All years complete.")
    print("=" * 50)


if __name__ == '__main__':
    main()
