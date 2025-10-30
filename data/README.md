Data assets
===========

Place the following CSVs in this folder and commit them so others and CI can run the model:

- dod_labs_collaboration_hubs_locations.csv
  - Expected columns: name/site/facility (any one), latitude/lat, longitude/lon/lng. Extra columns are fine.
- FY2026_SEC4201_RDTandE_All_Line_Items.csv
  - FY26 RDT&E proposed funding line items. Parsed into `model.rdte_fy26` for analysis.

Configuration
-------------

`parameters.yaml` is already set to relative paths:

data:
  labs_locations_csv: data/dod_labs_collaboration_hubs_locations.csv
  rdte_fy26_csv: data/FY2026_SEC4201_RDTandE_All_Line_Items.csv

Notes
-----

- If files are large, consider using Git LFS before committing:
  - git lfs install
  - git lfs track "*.csv"
  - commit `.gitattributes` and CSVs
- The model tolerates missing files (it just loads zero rows), but results will differ slightly (no labs-based ecosystem bonus).

