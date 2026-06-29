"""
Shared utility functions for the EAI (Economic Activity Intensity) processing pipeline.

This module provides the core computational functions used across pipeline steps:
rasterisation, Gaussian smoothing, CRITIC weighting, and GeoTIFF export.

Author: [author names]
"""

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter
from sklearn.preprocessing import MinMaxScaler
import rasterio
from rasterio.transform import from_origin


def point_to_index(x, y, xmin, ymax, res):
    """
    Convert projected coordinates to raster grid row/column indices.

    Parameters
    ----------
    x, y : float
        Projected coordinates (e.g. Albers Equal-Area Conic, metres).
    xmin : float
        Minimum X (left) extent of the raster.
    ymax : float
        Maximum Y (top) extent of the raster.
    res : float
        Grid cell resolution (metres).

    Returns
    -------
    row, col : int
        Zero-based row and column indices.
    """
    col = int((x - xmin) / res)
    row = int((ymax - y) / res)
    return row, col


def calculate_critic_weights(df, cols):
    """
    Calculate CRITIC objective weights for a set of indicators.

    The CRITIC method (Diakoulaki et al., 1995) derives weights from two
    information-theoretic criteria:
      - Contrast intensity: standard deviation of each indicator
      - Conflict: 1 minus the Pearson correlation between indicators

    In the two-indicator case, the (1 - r) factor cancels and the weights
    simplify to w_j = sigma_j / (sigma_1 + sigma_2).

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing the indicator columns.
    cols : list of str
        Column names of the indicators to weight.

    Returns
    -------
    weights : pandas.Series
        CRITIC weights indexed by column name, summing to 1.0.
    """
    std_dev = df[cols].std()
    corr_matrix = df[cols].corr()
    conflict = np.dot(1 - corr_matrix, np.ones(len(cols)))
    conflict_series = pd.Series(conflict, index=cols)
    information = std_dev * conflict_series
    weights = information / information.sum()
    return weights


def rasterize_gdf(gdf, value_field, resolution, bounds=None):
    """
    Rasterize a GeoDataFrame by centroid to a 2D numpy array.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Input vector data with geometry and a value column.
    value_field : str
        Column name containing the values to rasterise.
    resolution : float
        Output cell size (metres).
    bounds : tuple of (xmin, ymin, xmax, ymax), optional
        If None, computed from gdf.total_bounds.

    Returns
    -------
    raster : numpy.ndarray (2D, float32)
        Rasterised values; cells with no data are np.nan.
    transform : affine.Affine
        Affine transform for the raster.
    """
    if bounds is None:
        xmin, ymin, xmax, ymax = gdf.total_bounds
    else:
        xmin, ymin, xmax, ymax = bounds

    width = int(np.ceil((xmax - xmin) / resolution))
    height = int(np.ceil((ymax - ymin) / resolution))
    raster = np.full((height, width), np.nan, dtype=np.float32)

    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        centroid = geom.centroid
        c, r = point_to_index(centroid.x, centroid.y, xmin, ymax, resolution)
        if 0 <= r < height and 0 <= c < width:
            val = row[value_field]
            if pd.notna(val):
                raster[r, c] = val

    transform = from_origin(xmin, ymax, resolution, resolution)
    return raster, transform


def raster_to_gdf_values(gdf, raster, xmin, ymax, res):
    """
    Sample raster values back to GeoDataFrame rows using centroids.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        GeoDataFrame whose rows will receive sampled values.
    raster : numpy.ndarray (2D)
        Raster from which to sample.
    xmin, ymax : float
        Raster origin coordinates.
    res : float
        Cell resolution.

    Returns
    -------
    values : list
        List of sampled values (one per row); np.nan replaced with 0.
    """
    height, width = raster.shape
    values = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            values.append(0)
            continue
        centroid = geom.centroid
        c, r = point_to_index(centroid.x, centroid.y, xmin, ymax, res)
        if 0 <= r < height and 0 <= c < width:
            val = raster[r, c]
            values.append(val if not np.isnan(val) else 0)
        else:
            values.append(0)
    return values


def save_raster(gdf, score_col, out_path, resolution):
    """
    Write a GeoDataFrame attribute as a single-band GeoTIFF raster.

    Cells are rasterised by centroid. NoData cells are set to NaN (Float32).

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Input vector data.
    score_col : str
        Column name to write as raster values.
    out_path : str
        Output GeoTIFF file path.
    resolution : float
        Cell size (metres).
    """
    xmin, ymin, xmax, ymax = gdf.total_bounds
    width = int(np.ceil((xmax - xmin) / resolution))
    height = int(np.ceil((ymax - ymin) / resolution))
    transform = from_origin(xmin, ymax, resolution, resolution)
    raster_data = np.full((height, width), np.nan, dtype=np.float32)

    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        centroid = row.geometry.centroid
        c, r = point_to_index(centroid.x, centroid.y, xmin, ymax, resolution)
        if 0 <= r < height and 0 <= c < width:
            val = row[score_col]
            if pd.notna(val):
                raster_data[r, c] = val

    profile = {
        'driver': 'GTiff',
        'dtype': 'float32',
        'width': width,
        'height': height,
        'count': 1,
        'crs': gdf.crs,
        'transform': transform,
        'nodata': np.nan,
    }

    with rasterio.open(out_path, 'w', **profile) as dst:
        dst.write(raster_data, 1)
