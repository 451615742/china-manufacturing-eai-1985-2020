"""
Step 4 — Spatial join to 1-km grid (ArcPy version).

Aggregates enterprise point features to a regular vector grid using
ArcGIS Pro's SpatialJoin tool with CONTAINS predicate.

For each grid cell, the 'Registered_capital_RMB' field (mapped from
'Register_1' in the enterprise SHP) is summed across all contained points.

**IMPORTANT — Software dependency:**
This script requires ArcGIS Pro (arcpy). It must be run inside the
ArcGIS Pro Python window or arcpy environment. arcpy is proprietary
software and is not installable via pip/conda.

An open-source alternative using geopandas.sjoin is provided as
step4_spatial_join_opensource.py for users without ArcGIS Pro access.
Results from the two implementations should be numerically identical.

Usage (inside ArcGIS Pro Python window or standalone arcpy environment):
    python step4_spatial_join.py \
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
import arcpy


def spatial_join_one(grid_shp, enterprise_shp, output_path):
    """
    Spatially join one enterprise layer to the grid.

    The 'Register_1' field (registered capital RMB) is summed per grid cell
    using the CONTAINS predicate (grid CONTAINS enterprise point).
    """
    # Build field mapping: Register_1 → RMB (SUM)
    field_mappings = arcpy.FieldMappings()
    field_map = arcpy.FieldMap()
    field_map.addInputField(enterprise_shp, "Register_1")
    output_field = field_map.outputField
    output_field.name = "RMB"
    field_map.outputField = output_field
    field_map.mergeRule = 'Sum'
    field_mappings.addFieldMap(field_map)

    arcpy.SpatialJoin_analysis(
        target_features=grid_shp,
        join_features=enterprise_shp,
        out_feature_class=output_path,
        join_operation="JOIN_ONE_TO_ONE",
        join_type="KEEP_ALL",
        field_mapping=field_mappings,
        match_option="CONTAINS",
    )
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Step 4: Spatial join of enterprise points to grid "
                    "(requires ArcGIS Pro / arcpy)."
    )
    parser.add_argument('--workspace', required=True,
                        help='Directory containing enterprise SHP files.')
    parser.add_argument('--grid', required=True,
                        help='Path to grid polygon shapefile.')
    parser.add_argument('--output', required=True,
                        help='Directory for output spatially-joined SHPs.')
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    n_processed = 0
    for dirpath, dirnames, filenames in arcpy.da.Walk(args.workspace):
        for fname in filenames:
            if not fname.endswith('.shp'):
                continue

            shp_path = os.path.join(dirpath, fname)
            base = os.path.splitext(fname)[0]
            out_path = os.path.join(args.output, f"{base}_spatial_join.shp")

            print(f"Processing: {shp_path}")
            spatial_join_one(args.grid, shp_path, out_path)
            print(f"  → {out_path}")
            n_processed += 1

    print(f"\nDone. {n_processed} shapefile(s) processed.")


if __name__ == '__main__':
    main()
