"""
prepare_data.py  -  rebuild the processed CSV from the downloaded GDC MAF files

  python prepare_data.py [raw_dir] [out_csv]
  defaults: data/raw  ->  data/processed/real_tcga_mutations.csv

Prints the counts quoted in the SRS (files, records, samples, build, attributes).
"""
import sys
from pathlib import Path
import pandas as pd

raw = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw")
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/processed/real_tcga_mutations.csv")

files = sorted(raw.rglob("*.maf.gz"))
if not files:
    sys.exit(f"No .maf.gz files found under {raw}")

frames = [pd.read_csv(f, sep="\t", comment="#", compression="gzip", low_memory=False)
          for f in files]
df = pd.concat(frames, ignore_index=True)
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False)

print(f"MAF files          : {len(files)}")
print(f"Mutation records   : {len(df)}")
print(f"Distinct samples   : {df['Tumor_Sample_Barcode'].nunique()}")
print(f"Attributes         : {df.shape[1]}")
if "NCBI_Build" in df.columns:
    print(f"Genome build       : {sorted(df['NCBI_Build'].dropna().unique())}")
print(f"Chromosome format  : e.g. {sorted(df['Chromosome'].unique())[:3]}")
print(f"Written to         : {out}")