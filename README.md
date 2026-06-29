# EAI Dataset — Processing Pipeline

This repository contains the complete computational pipeline for constructing
the 1-km gridded manufacturing Economic Activity Intensity (EAI) dataset for
mainland China (1985–2020).

## Overview

The pipeline transforms enterprise registration records from the National
Enterprise Credit Information Publicity System (NECIPS, http://www.gsxt.gov.cn)
into a gridded EAI index through a five-step process:

```
Raw NECIPS CSV
  │
  ├── step1_drop_columns.py       Remove privacy-sensitive columns
  ├── step2_currency_conversion.py  Unify registered capital to RMB
  ├── step3_filter_manufacturing.py Filter C-class manufacturing, target year
  ├── step4_spatial_join.py         Aggregate to 1-km grid (ArcPy or GeoPandas)
  └── step5_eai_synthesis.py       Five-step EAI: Gaussian → Log → Norm → CRITIC → Score
```

## Repository contents

| File | Description |
|------|-------------|
| `eai_utils.py` | Shared utilities: rasterisation, CRITIC weights, GeoTIFF export |
| `step1_drop_columns.py` | Drop LAR and Address columns |
| `step2_currency_conversion.py` | Convert 12 foreign currencies to RMB |
| `step3_filter_manufacturing.py` | Filter manufacturing enterprises for target year |
| `step4_spatial_join.py` | Spatial join to 1-km grid (ArcGIS Pro / arcpy) |
| `step4_spatial_join_opensource.py` | Spatial join to 1-km grid (GeoPandas, no ArcGIS required) |
| `step5_eai_synthesis.py` | Five-step EAI index construction and GeoTIFF output |
| `industry_codes.csv` | GB/T 4754 manufacturing (Category C) code lookup table |
| `requirements.txt` | Python package dependencies |

## Dependencies

### Core (open-source)

```
geopandas >= 0.14.0
rasterio  >= 1.3.0
numpy     >= 1.24.0
pandas    >= 2.0.0
scipy     >= 1.10.0
scikit-learn >= 1.3.0
```

Install with:

```bash
pip install -r requirements.txt
```

### ArcGIS Pro (proprietary — step 4 only)

`step4_spatial_join.py` requires `arcpy`, which ships with ArcGIS Pro.
If ArcGIS Pro is not available, use `step4_spatial_join_opensource.py` instead,
which produces numerically identical results using `geopandas.sjoin`.

## Usage

### Quick start

Each step is a standalone script with command-line arguments:

```bash
# Step 1: Drop columns
python step1_drop_columns.py \
    --input /data/raw_csv/ \
    --output /data/01_dropped/

# Step 2: Convert currency to RMB
python step2_currency_conversion.py \
    --input /data/01_dropped/ \
    --output /data/02_rmb/

# Step 3: Filter manufacturing enterprises for a target year
python step3_filter_manufacturing.py \
    --input /data/02_rmb/ \
    --output /data/03_filtered/ \
    --year 2015

# Step 4: Spatial join to grid (ArcPy version)
python step4_spatial_join.py \
    --workspace /data/03_filtered/ \
    --grid /data/grid_1km.shp \
    --output /data/04_joined/

# Step 4 (alternative): Spatial join to grid (open-source version)
python step4_spatial_join_opensource.py \
    --workspace /data/03_filtered/ \
    --grid /data/grid_1km.shp \
    --output /data/04_joined/

# Step 5: EAI synthesis for all years
python step5_eai_synthesis.py \
    --input-root /data/04_joined/ \
    --output-root /data/05_eai/ \
    --years "2020,2015,2010,2005,2000,1995,1990,1985" \
    --sigma 1.0 \
    --resolution 1000
```

### Adjusting exchange rates

The exchange rates in `step2_currency_conversion.py` are annual averages.
If your raw data carries a different vintage, update the `EXCHANGE_RATES`
dictionary in the script. Rates are sourced from the State Administration
of Foreign Exchange (SAFE).

### Adjusting the Gaussian kernel bandwidth

The `--sigma` parameter in `step5_eai_synthesis.py` controls the spatial
smoothing range. The default value of 1.0 grid-cell units corresponds to
a 1,000 m Gaussian kernel bandwidth at 1 km resolution. Sensitivity tests
(see the accompanying paper) confirm that county-level validation metrics
are robust to bandwidth choices from 500 m to 2,000 m.

## Key parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--sigma` | 1.0 | Gaussian kernel σ in grid-cell units (1.0 × 1 km = 1,000 m) |
| `--resolution` | 1000 | Grid cell size in metres |
| `--year` | (required) | Target year for enterprise filtering |
| `--years` | (required) | Comma-separated list of years for EAI synthesis |

## Output file format

- **Intermediate (steps 1–4):** CSV and ESRI Shapefile
- **Final (step 5):**
  - `*_final.shp` — Vector grid with EAI values and intermediate fields
  - `*_final.tif` — Single-band GeoTIFF, Float32, [0, 100], NoData = NaN
  - Projection: Albers Equal-Area Conic (CGCS2000, central meridian 105°E, standard parallels 25°N / 47°N)

## Notes

1. **Step ordering:** Steps must be run sequentially. Each step reads the
   output of the previous step.
2. **ArcPy dependency:** Step 4 can use either ArcPy (proprietary) or
   GeoPandas (open-source). Results are numerically equivalent.
3. **Sub-industry code 43:** The filtering script (`step3_filter_manufacturing.py`)
   excludes GB/T 4754 code 43 (Repair of fabricated metal products, machinery
   and equipment). Modify `cond_exclude_43` in the code to include it.
4. **Cross-year comparability:** EAI values are independently normalised per
   year to [0, 100]. Direct cross-year differencing is not supported.
   See the accompanying paper (Usage Notes) for recommended cross-year
   comparison methods.
5. **Exchange rate vintage:** The bundled exchange rates are annual averages
   for one reference year. For multi-year data, update rates per year.

## Citation

If you use this code or the resulting dataset, please cite the accompanying
Data Descriptor paper:

> [Author names]. A 1-km gridded manufacturing Economic Activity Intensity
> (EAI) dataset for mainland China (1985–2020). *Scientific Data*, [year].

## Licence

This code is released under the CC BY 4.0 licence, consistent with the
accompanying dataset.
