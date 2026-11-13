# Traffic Violations Insight System

Cleaning, EDA and an interactive Streamlit dashboard for about 2 million Montgomery County (Maryland) traffic violation records, 2012 to 2025.

## Objectives

- Clean and standardize a large, messy traffic violations dataset
- Explore it with EDA to answer six key questions
- Build an interactive dashboard with filters, charts, a map and summary statistics

## Tech stack

Python 3.14, pandas, PyArrow (Parquet), Plotly, Streamlit, uv

## Project structure

```
traffic-violations/
  app.py                 Streamlit dashboard
  src/clean_data.py      Cleaning and preprocessing script
  notebooks/eda.ipynb    EDA with insights
  docs/                  Screenshots
  data/raw/              Place Traffic_Violations.csv here (not in repo)
  data/clean/            Generated Parquet file (not in repo)
```

## Setup

1. Install uv, then run `uv sync`
2. Extract the dataset and place `Traffic_Violations.csv` in `data/raw/`
3. Clean the data (about 5 to 10 minutes):
   ```
   uv run python -m src.clean_data
   ```
   Add `--sample 100000` to test on a smaller sample first.
4. Run the dashboard:
   ```
   uv run streamlit run app.py
   ```
5. Open `notebooks/eda.ipynb` for the analysis.

## Data cleaning summary

| Problem                                     | Fix                                                             |
| ------------------------------------------- | --------------------------------------------------------------- |
| Fully duplicate rows (2,354)                | Removed (rows sharing a SeqID with different charges were kept) |
| Latitude/longitude of 0 or outside Maryland | Set to missing                                                  |
| Vehicle year of 0 or 9999                   | Set to missing if outside 1960 to the next year                 |
| Make abbreviations (TOYT, HOND, CHEV...)    | Mapped to full names                                            |
| Color variants ("BLUE, DARK")               | Mapped to the base color                                        |
| Yes/No columns with mixed labels            | Converted to True/False (blank = False)                         |
| Blank search columns                        | Filled with "NOT APPLICABLE"                                    |
| Gender other than M/F                       | Set to "UNKNOWN"                                                |
| Dates and times                             | Parsed to datetime; invalid or future dates dropped             |
| Memory use                                  | Category dtypes, smaller numeric types, saved as Parquet        |

Result: 2,070,115 raw rows became 2,067,761 clean rows (1,178,080 unique stops).

New features: stop year, month, weekday, hour, time of day, violation category (keyword rules on the description), severity (fatal / injury / property damage / none) and charges per stop.

## Key insights

1. <Most common violation category and its share>
2. <Busiest police district and the missing-coordinates limitation>
3. <Busiest hours and weekdays>
4. <The drop in violations around 2020>
5. <Violation types with the highest accident rate>

## Recommendations

- <For example: focus patrols in the top districts at the busiest hours>
- <For example: target the violation types linked to the most accidents>
- <For example: improve location data quality, since many records lack coordinates>

## Dashboard

![Dashboard](docs/dashboard.png)
![Filtered dashboard](docs/dashboard_filtered.png)

## Limitations

- Demographic tables show how each group's violations split across categories. They do not measure who is more likely to be stopped.
- Violation categories come from keyword rules and are approximate.
- Some records have no valid coordinates, so hotspot analysis uses only the records that do.
