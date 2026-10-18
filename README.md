# EAI Dataset Processing Pipeline

This repository preserves the original five-step layout used for the EAI
dataset while updating the implementation to the final release parameters.

## Pipeline

1. `step1_drop_columns.py` removes privacy-sensitive fields from working copies.
2. `step2_currency_conversion.py` converts registered capital to CNY using a supplied rate table.
3. `step3_filter_manufacturing.py` retains manufacturing codes 13-42 and applies target-year rules.
4. `step4_spatial_join.py` and `step4_spatial_join_opensource.py` aggregate geocoded points to the 1-km grid.
5. `step5_eai_synthesis.py` applies Gaussian smoothing and constructs the EAI raster.

## Final parameters

- Grid: 1,000 m × 1,000 m
- Gaussian standard deviation: sigma = 0.333 grid-cell units
- Truncation: 3 sigma, with a 3 × 3 discrete neighbourhood
- Fixed weights: 0.38 for enterprise count and 0.62 for registered capital
- Transformation: log1p, followed by within-year min-max normalisation
- Final scaling: within-year EAI range 0-100
- GeoTIFF: Float32, LZW compression, predictor 3, NoData = NaN

The code does not include raw enterprise registration records, intermediate
count or capital grids, or Amap/Baidu coordinate outputs. Those inputs are
controlled or third-party materials and are not redistributed.

## Citation and licence

Please cite the associated dataset and manuscript. The code is intended for
release under the MIT License after the repository owner confirms the licence.
