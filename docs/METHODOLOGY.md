# Methodology

This project is a data-engineering and backtesting archive for 福彩3D historical results. It is not a betting system and does not provide predictive certainty.

## Data pipeline

```text
official API browser dump
  -> parse structured records
  -> deduplicate by issue
  -> build full history JSON/JSONL
  -> build rolling feature rows
  -> run walk-forward validation/test split
  -> export reports and entertainment-only forecast artifacts
```

## Default local paths

Scripts now default to repository-relative paths so a cloned repository can be reproduced without `/var/minis` paths.

| Script | Default input | Default output |
|---|---|---|
| `scripts/build_fucai3d_dataset.py` | `data/raw/official_api_2y_browser_dump.txt` | `data/2y/` |
| `scripts/build_fucai3d_all_dataset.py` | `data/raw/official_api_all_browser_dump.txt` | `data/all/` |
| `scripts/fucai3d_backtest_walkforward.py` | `data/all/history_official_all_features.json` | `reports/` |
| `scripts/fucai3d_forecast_next7days.py` | `data/all/history_official_all_features.json` | `reports/` |
| `scripts/recommender.py` | `data/all/history_official_all_train.json` when present, otherwise `/var/minis/shared/fucai3d/history.json` | same history file |

## Environment overrides

Use these variables when running outside the repository layout:

```bash
FUCAI3D_2Y_SOURCE=/path/to/official_api_2y_browser_dump.txt
FUCAI3D_ALL_SOURCE=/path/to/official_api_all_browser_dump.txt
FUCAI3D_OUTPUT_DIR=/path/to/2y/output
FUCAI3D_ALL_OUTPUT_DIR=/path/to/all/output
FUCAI3D_FEATURES_PATH=/path/to/history_official_all_features.json
FUCAI3D_REPORTS_DIR=/path/to/reports
FUCAI3D_HISTORY_PATH=/path/to/history.json
```

## Feature construction

Feature rows include current draw structure and rolling historical context, including:

- date fields and weekday
- three-position digits
- sorted group number
- sum, span, odd/even, big/small, prime counts
- repeat type: 豹子 / 组三 / 组六
- previous issue features
- rolling 30-draw hot/cold digits and digit frequencies

## Walk-forward design

The backtest uses a rolling historical window. It selects parameters on a validation split, then evaluates the selected configuration on a later held-out test split.

This structure reduces obvious look-ahead leakage, but it does not turn random lottery results into a reliable forecasting process.

## Interpreting outputs

- Exact-number TopN metrics should be compared against random baselines.
- Structural metrics such as sum/span/repeat-type can look higher because they are lower-cardinality targets.
- A higher structural hit rate is not evidence of profitable or reliable exact-number prediction.
- Forecast files are entertainment artifacts produced by recursive simulation, not operational advice.
