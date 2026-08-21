import pandas as pd
import sys

path = r\"Datasets\Emails\Enron_Email\emails.csv\"
nrows = 10
if len(sys.argv) > 1:
    try:
        nrows = int(sys.argv[1])
    except ValueError:
        pass

print(f\"Reading the first {nrows} lines of Enron emails dataset...\")
try:
    df = pd.read_csv(path, nrows=nrows)
    for idx, row in df.iterrows():
        print("="*50)
        print(f\"Row {idx} - File Path: {row['file']}\")
        print("-"*50)
        print(row['message'][:500] + \"\n[Truncated...]\" if len(row['message']) > 500 else row['message'])
except Exception as e:
    print(f\"Error reading file: {e}\")
