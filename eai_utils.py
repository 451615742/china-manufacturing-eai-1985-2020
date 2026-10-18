"""Shared utilities for the 1-km EAI processing pipeline.

The final release uses sigma=0.333 grid cells, fixed weights of 0.38 and
0.62, log1p transformation, within-year min-max normalisation, and a final
within-year min-max scaling to [0, 100].
"""
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter


def minmax(values):
    values = np.asarray(values, dtype="float64")
    lo, hi = np.nanmin(values), np.nanmax(values)
    if not np.isfinite(lo) or hi <= lo:
        raise ValueError("The input does not have a finite positive range")
    return (values - lo) / (hi - lo)


def smooth_indicator(values, valid, sigma=0.333):
    filled = np.where(valid, values, 0.0).astype("float64")
    return gaussian_filter(
        filled, sigma=sigma, truncate=3.0, mode="constant", cval=0.0
    )


def synthesise_eai(count, capital, valid, sigma=0.333,
                   count_weight=0.38, capital_weight=0.62):
    count = np.asarray(count)
    capital = np.asarray(capital)
    valid = np.asarray(valid, dtype=bool)
    if count.shape != capital.shape or count.shape != valid.shape:
        raise ValueError("Count, capital, and mask arrays must have identical shapes")
    if not np.isclose(count_weight + capital_weight, 1.0):
        raise ValueError("Weights must sum to one")
    transformed = []
    for indicator in (count, capital):
        smoothed = smooth_indicator(indicator, valid, sigma)
        values = np.log1p(smoothed[valid])
        transformed.append(minmax(values))
    score = count_weight * transformed[0] + capital_weight * transformed[1]
    score = minmax(score) * 100.0
    output = np.full(count.shape, np.nan, dtype="float32")
    output[valid] = score.astype("float32")
    return output


def write_eai_geotiff(reference_path, output_path, eai):
    import rasterio

    with rasterio.open(reference_path) as reference:
        profile = reference.profile.copy()
        profile.update(dtype="float32", count=1, nodata=np.nan,
                       compress="lzw", predictor=3)
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(eai, 1)


def read_numeric_raster(path):
    import rasterio

    with rasterio.open(path) as src:
        return src.read(1), src.profile.copy()
