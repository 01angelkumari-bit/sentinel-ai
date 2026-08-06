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
