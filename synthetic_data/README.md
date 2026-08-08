# Synthetic data

Only synthetic, non-sensitive datasets belong here. `seed.py` uses a fixed Faker seed, generates 365 consecutive days of sales, writes relational CSV files to `synthetic_data/csv`, and can optionally load the configured database.

Generate CSV files:

```powershell
backend\.venv-win\Scripts\python.exe synthetic_data\seed.py
```

Apply migrations and replace existing BI seed rows:

```powershell
backend\.venv-win\Scripts\python.exe synthetic_data\seed.py --database --reset
```

Never use `--reset` against a production database.

## Dashboard-ready business exports

`build_business_datasets.mjs` generates deterministic, non-sensitive datasets in `synthetic_data/business_exports`:

- `Sales.csv`: 1,460 regional sales segments across 365 consecutive days.
- `Support.csv`: 600 uniquely identified support tickets with priority, status, and sentiment.
- `HR.csv`: 200 uniquely identified employee records with department, leave, performance, and joining date.
- `Sentinel-Business-Data.xlsx`: a formatted Excel companion containing all three datasets.

Run the generator from the repository root using the bundled spreadsheet runtime configured for the project. The seed is fixed so repeated runs produce stable records for demonstrations and tests.
