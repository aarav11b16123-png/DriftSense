import os
import pandas as pd
import numpy as np

# Path directly targeting your dataset location
CURRENT_CSV_PATH = os.path.join("data", "processed", "current.csv")

if not os.path.exists(CURRENT_CSV_PATH):
    print(f"❌ Error: Could not find file at {CURRENT_CSV_PATH}")
    print("Available files in data/processed:", os.listdir("data/processed"))
    exit(1)

print(f"Loading {CURRENT_CSV_PATH}...")
df = pd.read_csv(CURRENT_CSV_PATH)

# Seed for reproducible drift generation
np.random.seed(42)
n_samples = len(df)

# ==============================================================================
# INJECT SYNTHETIC DRIFT INTO KEY FEATURES
# ==============================================================================

# 1. Income Shift (Mean and scale shift)
if "MonthlyIncome" in df.columns:
    df["MonthlyIncome"] = df["MonthlyIncome"].apply(
        lambda x: x * 1.85 + np.random.normal(2500, 800) if pd.notnull(x) else x
    )
    print("✅ Injected drift into: MonthlyIncome")

# 2. Debt Ratio Shift
if "DebtRatio" in df.columns:
    df["DebtRatio"] = df["DebtRatio"] * 3.2 + np.random.uniform(0.5, 2.0, size=n_samples)
    print("✅ Injected drift into: DebtRatio")

# 3. Revolving Utilization Shift
if "RevolvingUtilizationOfUnsecuredLines" in df.columns:
    df["RevolvingUtilizationOfUnsecuredLines"] = df["RevolvingUtilizationOfUnsecuredLines"] * 2.5 + np.random.exponential(scale=0.5, size=n_samples)
    print("✅ Injected drift into: RevolvingUtilizationOfUnsecuredLines")

# 4. Age Shift
if "age" in df.columns:
    df["age"] = np.clip(df["age"] - 12 + np.random.randint(-3, 4, size=n_samples), 18, 100)
    print("✅ Injected drift into: age")

# 5. Delinquency Shift
if "NumberOfTime30-59DaysPastDueNotWorse" in df.columns:
    df["NumberOfTime30-59DaysPastDueNotWorse"] = df["NumberOfTime30-59DaysPastDueNotWorse"] + np.random.poisson(lam=1.5, size=n_samples)
    print("✅ Injected drift into: NumberOfTime30-59DaysPastDueNotWorse")

# Save modified dataset back to data/processed/current.csv
df.to_csv(CURRENT_CSV_PATH, index=False)
print(f"\n🎉 Successfully updated {CURRENT_CSV_PATH} with drifted data!")