"""
Step 4 — Spatial join to 1-km grid (GeoPandas open-source version).

Aggregates enterprise point features to a regular vector grid using
geopandas.sjoin. Functionally equivalent to step4_spatial_join.py but
does not require ArcGIS Pro.

For each grid cell, the 'Registered_capital_RMB' field (mapped from
'Register_1' in the enterprise SHP) is summed across all contained points.

Usage:
    python step4_spatial_join_opensource.py \
        --workspace <dir_with_enterprise_shps> \
        --grid <grid_shapefile.shp> \
        --output <output_dir>

Input:
  - Enterprise point shapefiles in workspace directory.
  - Grid polygon shapefile (1 km × 1 km).

Output:
  - Spatially joined shapefiles with '_spatial_join' suffix.
"""

import os
import argparse
from glob import glob
import geopandas as gpd
import pandas as pd


def spatial_join_one(grid_shp, enterprise_shp, output_path):
    """
    Spatially join one enterprise point layer to the grid using GeoPandas.

    Parameters
    ----------
    grid_shp : str
        Path to grid polygon shapefile.
    enterprise_shp : str
        Path to enterprise point shapefile.
    output_path : str
        Output shapefile path.

    Returns
    -------
    str
        Output path.
    """
    grid = gpd.read_file(grid_shp)
    points = gpd.read_file(enterprise_shp)

    # Ensure consistent CRS
    if grid.crs != points.crs:
        points = points.to_crs(grid.crs)

    # Spatial join: grid CONTAINS point
    joined = gpd.sjoin(grid, points, how='left', predicate='contains')

    # Sum 'Register_1' (RMB capital) per grid cell
    if 'Register_1' in joined.columns:
        agg = joined.groupby(joined.index)['Register_1'].sum().reset_index()
        agg.columns = ['index', 'RMB']
    else:
        # If no matching field, create empty RMB column
        agg = pd.DataFrame({'index': grid.index, 'RMB': 0.0})

    # Merge sum back to grid
    result = grid.copy()
    result = result.merge(agg, left_index=True, right_on='index', how='left')
    result['RMB'] = result['RMB'].fillna(0.0)

    # Drop join artifact columns
    cols_to_drop = ['index', 'index_right']
    result = result.drop(columns=[c for c in cols_to_drop if c in result.columns],
                         errors='ignore')

    result.to_file(output_path, encoding='utf-8')
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Step 4 (open-source): Spatial join of enterprise points "
                    "to grid using GeoPandas."
    )
    parser.add_argument('--workspace', required=True,
                        help='Directory containing enterprise SHP files.')
    parser.add_argument('--grid', required=True,
                        help='Path to grid polygon shapefile.')
    parser.add_argument('--output', required=True,
                        help='Directory for output spatially-joined SHPs.')
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    shp_files = glob(os.path.join(args.workspace, '**', '*.shp'), recursive=True)

    if not shp_files:
        print(f"WARNING: No SHP files found in {args.workspace}")
        return

    n_processed = 0
    for shp_path in shp_files:
        base = os.path.splitext(os.path.basename(shp_path))[0]
        out_path = os.path.join(args.output, f"{base}_spatial_join.shp")

        print(f"Processing: {shp_path}")
        spatial_join_one(args.grid, shp_path, out_path)
        print(f"  → {out_path}")
        n_processed += 1

    print(f"\nDone. {n_processed} shapefile(s) processed.")


if __name__ == '__main__':
    main()
