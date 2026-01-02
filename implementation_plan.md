# Dropship Analytics Dashboard Implementation Plan

## Goal Description
Build an interactive Streamlit dashboard to analyze e-commerce order data. The dashboard will process uploaded Excel/CSV files, standardize columns, and display KPIs, charts, and tables as specified.

## User Review Required
- **Column Mapping**: The app will attempt to guess column names. If exact matches aren't found, it falls back to common variations. Users might need to rename columns in their source file if auto-detection fails completely (though we will try to be robust).
- **Geo Data**: We will use Plotly's GeoJSON for India. State name normalization will be critical.

## Proposed Changes

### [Dashboard Core]
#### [NEW] [app.py](file:///Users/shreekant/.gemini/antigravity/brain/660b5934-1c3a-417f-85f2-433e7a14ae5a/app.py)
The main application file containing:
- `load_data()`: Reads CSV/Excel, caches result.
- `map_columns()`: Renames columns to standard internal names (order_id, order_date, etc.).
- `calculate_metrics()`: Implements the specific formulas for IN_TRANSIT, DELIVERY %, RTO %, etc.
- UI Layout: CSS for card styling, columns for layout (KPIs -> Charts -> Donuts -> Map -> Tables).

#### [NEW] [requirements.txt](file:///Users/shreekant/.gemini/antigravity/brain/660b5934-1c3a-417f-85f2-433e7a14ae5a/requirements.txt)
Dependencies: `streamlit`, `pandas`, `plotly`, `openpyxl`.

## Verification Plan
### Automated Tests
- N/A for this snippet generation.

### Manual Verification
- I will verify the logic by dry-running the specific formulas provided by the user against hypothetical data points during code generation.
- The user will verify by uploading their actual file.
