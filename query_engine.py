# query_engine.py
import pandas as pd

DATA_PATH = "data/processed/real_tcga_mutations.csv"
MUTATIONS = pd.read_csv(DATA_PATH, low_memory=False)

KNOWN_CHROMOSOMES = set(MUTATIONS["Chromosome"].unique())
KNOWN_VARIANT_TYPES = set(MUTATIONS["Variant_Classification"].unique())
# MAF files declare their genome build explicitly — check it directly instead of assuming
KNOWN_ASSEMBLY = MUTATIONS["NCBI_Build"].iloc[0] if "NCBI_Build" in MUTATIONS.columns else "GRCh38"


def search_schema():
    """Tool: real schema facts, pulled directly from the actual downloaded data."""
    return {
        "chromosome_format": "has 'chr' prefix (e.g. 'chr7', not '7')",
        "assembly": KNOWN_ASSEMBLY,
        "variant_classifications": sorted(KNOWN_VARIANT_TYPES),
        "n_patients": MUTATIONS["Tumor_Sample_Barcode"].nunique(),
        "n_mutations": len(MUTATIONS),
    }


def run_query(chromosome: str, variant_classification: str = None, assembly: str = None):
    """Tool: filter real mutation records by chromosome (+ optional variant type)."""
    if assembly and assembly != KNOWN_ASSEMBLY:
        return MUTATIONS.iloc[0:0]  # genome-build mismatch -> empty, like real GMQL

    df = MUTATIONS[MUTATIONS["Chromosome"] == str(chromosome)]
    if variant_classification:
        df = df[df["Variant_Classification"] == variant_classification]
    return df


def validate_result(df: pd.DataFrame):
    return "EMPTY" if df.empty else "OK"


def diagnose_empty_result(chromosome: str, assembly: str = None):
    """Tool: self-correction diagnostic, now checking against the REAL schema."""
    if assembly and assembly != KNOWN_ASSEMBLY:
        return {
            "cause": "genome_assembly_mismatch",
            "detail": f"Requested assembly '{assembly}' but this dataset is built on '{KNOWN_ASSEMBLY}'.",
            "fix": {"assembly": KNOWN_ASSEMBLY},
        }
    normalized = str(chromosome)
    if not normalized.startswith("chr"):
        with_prefix = f"chr{normalized}"
        if with_prefix in KNOWN_CHROMOSOMES:
            return {
                "cause": "chromosome_naming_mismatch",
                "detail": f"'{chromosome}' not found, but '{with_prefix}' is valid in this dataset.",
                "fix": {"chromosome": with_prefix},
            }
    return {"cause": "unknown", "detail": "No known failure pattern matched.", "fix": None}