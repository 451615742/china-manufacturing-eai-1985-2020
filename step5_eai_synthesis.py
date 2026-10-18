"""Construct one EAI GeoTIFF from aligned count and capital rasters."""
import argparse
import numpy as np
import rasterio
from eai_utils import synthesise_eai


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", required=True)
    parser.add_argument("--capital", required=True)
    parser.add_argument("--mask-reference", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--sigma", type=float, default=0.333)
    parser.add_argument("--count-weight", type=float, default=0.38)
    parser.add_argument("--capital-weight", type=float, default=0.62)
    args = parser.parse_args()
    with rasterio.open(args.count) as c, rasterio.open(args.capital) as k, rasterio.open(args.mask_reference) as m:
        if not (c.shape == k.shape == m.shape and c.crs == k.crs == m.crs and c.transform == k.transform == m.transform):
            raise ValueError("Input rasters must have identical geometry and CRS")
        valid = (m.dataset_mask() > 0) & np.isfinite(m.read(1))
        eai = synthesise_eai(c.read(1), k.read(1), valid, args.sigma, args.count_weight, args.capital_weight)
        profile = m.profile.copy()
        profile.update(dtype="float32", count=1, nodata=np.nan, compress="lzw", predictor=3)
        with rasterio.open(args.output, "w", **profile) as dst:
            dst.write(eai, 1)


if __name__ == "__main__":
    main()
