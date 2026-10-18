"""ArcGIS-compatible spatial aggregation entry point.

The open-source GeoPandas implementation is recommended when ArcPy is not
available. This script delegates to the same aggregation contract.
"""
from step4_spatial_join_opensource import main


if __name__ == "__main__":
    main()
