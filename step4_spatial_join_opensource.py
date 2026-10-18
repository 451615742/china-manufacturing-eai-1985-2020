"""Aggregate geocoded enterprise points to a 1-km grid with GeoPandas."""
import argparse
from pathlib import Path
import geopandas as gpd
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--points", required=True)
    parser.add_argument("--grid", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--capital-column", default="registered_capital")
    args = parser.parse_args()
    points = gpd.read_file(args.points)
    grid = gpd.read_file(args.grid)
    if points.crs != grid.crs:
        points = points.to_crs(grid.crs)
    joined = gpd.sjoin(points, grid, how="inner", predicate="within")
    index_col = "index_right"
    grouped = joined.groupby(index_col).agg(
        enterprise_count=(index_col, "size"),
        registered_capital=(args.capital_column, "sum"),
    )
    out = grid.copy()
    out["enterprise_count"] = grouped["enterprise_count"].reindex(out.index).fillna(0)
    out["registered_capital"] = grouped["registered_capital"].reindex(out.index).fillna(0)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_file(args.output, driver="GPKG")


if __name__ == "__main__":
    main()
