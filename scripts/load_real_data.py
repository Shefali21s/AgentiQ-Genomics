# load_real_data.py
import pandas as pd
import gzip
import glob
import os

# ---- Step 1: Find all real MAF files (one per patient) ----
maf_files = glob.glob("data/raw/*/*.maf.gz")
print(f"Found {len(maf_files)} MAF files")

if len(maf_files) == 0:
    print("No files found — check that data/raw/maf_data/ contains your extracted GDC download")
    exit()

# ---- Step 2: Load and combine them into one DataFrame ----
all_mafs = []
for filepath in maf_files:
    with gzip.open(filepath, "rt") as f:
        df = pd.read_csv(f, sep="\t", comment="#", low_memory=False)
        df["source_file"] = os.path.basename(filepath)
        all_mafs.append(df)

maf = pd.concat(all_mafs, ignore_index=True)
print("\nCOMBINED SHAPE:", maf.shape)

# ---- Step 3: Inspect the key columns your project actually needs ----
key_cols = ["Chromosome", "Start_Position", "End_Position",
            "Tumor_Sample_Barcode", "Variant_Classification"]
print("\nKEY COLUMNS PREVIEW:")
print(maf[key_cols].head(10))

print("\nUNIQUE CHROMOSOME VALUES (check naming convention — 'chr7' vs '7'):")
print(sorted(maf["Chromosome"].unique().tolist()))

print("\nUNIQUE PATIENT COUNT:", maf["Tumor_Sample_Barcode"].nunique())

# ---- Step 4: Try loading the sample sheet, if you have it ----
sample_sheet_path = "data/gdc_sample_sheet.tsv"
if os.path.exists(sample_sheet_path):
    sample_sheet = pd.read_csv(sample_sheet_path, sep="\t")
    print("\nSAMPLE SHEET COLUMNS:", sample_sheet.columns.tolist())
    print(sample_sheet.head())
else:
    print(f"\nNo sample sheet found at {sample_sheet_path} — proceeding without it (fine, not required)")

# ---- Step 5: Save the combined, real dataset for query_engine.py to use ----
os.makedirs("data/processed", exist_ok=True)
maf.to_csv("data/processed/real_tcga_mutations.csv", index=False)
print("\nSaved combined data to data/processed/real_tcga_mutations.csv")