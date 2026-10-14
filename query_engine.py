
# query_engine.py
# Shared execution layer for FSM and Gemini agent

import os
from pathlib import Path
import pandas as pd

# --------------------------------------------------
# DATASET LOADING
# --------------------------------------------------

DEFAULT_DATA_PATH = (
    Path(__file__).resolve().parent
    / "data"
    / "processed"
    / "real_tcga_mutations.csv"
)

DATA_PATH = Path(
    os.environ.get("AGENTIQ_DATA", str(DEFAULT_DATA_PATH))
).expanduser()

if not DATA_PATH.is_file():
    raise FileNotFoundError(
        f"Dataset not found: {DATA_PATH}"
    )

MUTATIONS = pd.read_csv(DATA_PATH, low_memory=False)

REQUIRED_COLUMNS = {
    "Chromosome",
    "Variant_Classification",
    "Tumor_Sample_Barcode",
}

missing_columns = REQUIRED_COLUMNS - set(MUTATIONS.columns)

if missing_columns:
    raise ValueError(
        f"Missing required columns: {sorted(missing_columns)}"
    )

# Preserve dataset values; do not normalize stored data.
KNOWN_CHROMOSOMES = set(
    MUTATIONS["Chromosome"].dropna().astype(str).unique()
)

KNOWN_VARIANT_TYPES = set(
    MUTATIONS["Variant_Classification"]
    .dropna()
    .astype(str)
    .unique()
)

# --------------------------------------------------
# GENOME ASSEMBLY
# --------------------------------------------------

if "NCBI_Build" in MUTATIONS.columns:
    _builds = (
        MUTATIONS["NCBI_Build"]
        .dropna()
        .astype(str)
        .unique()
    )

    if len(_builds) != 1:
        raise ValueError(
            f"Expected one genome build, found {list(_builds)}"
        )

    KNOWN_ASSEMBLY = str(_builds[0])

else:
    # Based on previously verified GDC metadata.
    KNOWN_ASSEMBLY = "GRCh38"

# --------------------------------------------------
# SCHEMA INFORMATION
# --------------------------------------------------

def search_schema():
    """Return verified information about loaded data."""

    return {
        "chromosomes": sorted(KNOWN_CHROMOSOMES),
        "chromosome_format": "chr-prefixed",
        "assembly": KNOWN_ASSEMBLY,
        "variant_classifications": sorted(
            KNOWN_VARIANT_TYPES
        ),
        "n_samples": int(
            MUTATIONS["Tumor_Sample_Barcode"].nunique()
        ),
        "n_mutations": int(len(MUTATIONS)),
    }

# --------------------------------------------------
# EXACT-MATCH QUERY ENGINE
# --------------------------------------------------

def run_query(
    chromosome: str,
    variant_classification: str = None,
    assembly: str = None,
):
    """
    Preserve exact-match filtering.

    Returns a DataFrame, including an empty DataFrame
    when no records match.

    Use execute_query() when status information
    is required.
    """

    if assembly is not None:
        if assembly != KNOWN_ASSEMBLY:
            return MUTATIONS.iloc[0:0].copy()

    df = MUTATIONS[
        MUTATIONS["Chromosome"] == str(chromosome)
    ]

    if variant_classification is not None:
        df = df[
            df["Variant_Classification"]
            == variant_classification
        ]

    return df.copy()

# --------------------------------------------------
# RESULT STATUS
# --------------------------------------------------

def validate_result(df: pd.DataFrame):
    """Legacy DataFrame-only result validation."""

    if not isinstance(df, pd.DataFrame):
        return "FAILURE"

    return "EMPTY" if df.empty else "OK"

# --------------------------------------------------
# CHROMOSOME SUGGESTIONS
# --------------------------------------------------

def _chromosome_candidate(value):
    """Suggest canonical chr-prefixed notation."""

    core = str(value).strip()

    if core.lower().startswith("chr"):
        core = core[3:]

    core = core.upper()

    if core == "MT":
        core = "M"

    return f"chr{core}"

# --------------------------------------------------
# EMPTY-RESULT DIAGNOSTICS
# --------------------------------------------------

def diagnose_empty_result(
    chromosome: str,
    variant_classification: str = None,
    assembly: str = None,
):
    """Diagnose a zero-row result without changing inputs."""

    if assembly is not None:
        if assembly != KNOWN_ASSEMBLY:
            return {
                "cause": "genome_assembly_mismatch",
                "detail": (
                    f"Requested '{assembly}', but the "
                    f"dataset uses '{KNOWN_ASSEMBLY}'."
                ),
                "fix": {"assembly": KNOWN_ASSEMBLY},
            }

    if str(chromosome) not in KNOWN_CHROMOSOMES:
        candidate = _chromosome_candidate(chromosome)

        if candidate in KNOWN_CHROMOSOMES:
            return {
                "cause": "chromosome_naming_mismatch",
                "detail": (
                    f"'{chromosome}' is not present, "
                    f"but '{candidate}' is valid."
                ),
                "fix": {"chromosome": candidate},
            }

        return {
            "cause": "unknown_chromosome",
            "detail": (
                f"'{chromosome}' is not in the dataset."
            ),
            "fix": None,
        }

    if (
        variant_classification is not None
        and variant_classification not in KNOWN_VARIANT_TYPES
    ):
        lookup = {
            value.lower(): value
            for value in KNOWN_VARIANT_TYPES
        }

        key = (
            str(variant_classification)
            .strip()
            .lower()
            .replace(" ", "_")
        )

        if key in lookup:
            return {
                "cause": "variant_naming_mismatch",
                "detail": (
                    f"Use '{lookup[key]}' instead of "
                    f"'{variant_classification}'."
                ),
                "fix": {
                    "variant_classification": lookup[key]
                },
            }

        return {
            "cause": "unknown_variant",
            "detail": (
                f"Valid values: "
                f"{sorted(KNOWN_VARIANT_TYPES)}"
            ),
            "fix": None,
        }

    return {
        "cause": "valid_zero_rows",
        "detail": (
            "The supplied values are valid, but "
            "no records match their combination."
        ),
        "fix": None,
    }

# --------------------------------------------------
# STRUCTURED EXECUTION INTERFACE
# --------------------------------------------------

def execute_query(
    chromosome: str,
    variant_classification: str = None,
    assembly: str = None,
):
    """
    Execute a query and return a structured response.

    Status values:
        ok
        empty
        invalid
        failure
    """

    try:
        if chromosome is None or not str(chromosome).strip():
            return {
                "status": "invalid",
                "error": "Chromosome is required.",
                "diagnosis": None,
                "data": None,
            }

        df = run_query(
            chromosome=chromosome,
            variant_classification=variant_classification,
            assembly=assembly,
        )

        if df.empty:
            diagnosis = diagnose_empty_result(
                chromosome=chromosome,
                variant_classification=variant_classification,
                assembly=assembly,
            )

            if diagnosis["cause"] != "valid_zero_rows":
                return {
                    "status": "invalid",
                    "error": diagnosis["detail"],
                    "diagnosis": diagnosis,
                    "data": None,
                }

            return {
                "status": "empty",
                "error": None,
                "diagnosis": diagnosis,
                "data": df,
                "n_mutations": 0,
                "n_samples": 0,
            }

        return {
            "status": "ok",
            "error": None,
            "diagnosis": None,
            "data": df,
            "n_mutations": int(len(df)),
            "n_samples": int(
                df["Tumor_Sample_Barcode"].nunique()
            ),
        }

    except Exception as exc:
        return {
            "status": "failure",
            "error": str(exc),
            "diagnosis": None,
            "data": None,
        }
