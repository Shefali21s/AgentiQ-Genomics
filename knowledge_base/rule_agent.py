"""
rule_agent.py  -  rule-based diagnostic and retry prototype

NOT an LLM. Free text is parsed with keyword/regex rules, the shared engine runs
the query, and if the result is empty the engine's diagnostic proposes a fix and
the query is retried (bounded). This is the prototype shown in SRS 2.1.4; the
Gemini agent will later be measured against the same task set.
"""
import re
from dataclasses import dataclass, field

STATUS_OK = "ok"
STATUS_EMPTY = "empty_result"
STATUS_CLARIFY = "needs_clarification"
STATUS_FAILURE = "execution_failure"


@dataclass
class AgentResult:
    status: str
    rows: object = None
    chromosome: str = None
    variant_classification: str = None
    retries: int = 0
    recovered: bool = False
    summary: str = ""
    trace: list = field(default_factory=list)


class RuleBasedAgent:
    def __init__(self, engine=None, max_retries=2):
        if engine is None:
            import query_engine as engine
        self.engine = engine
        self.max_retries = max_retries

    # ---------------------------------------------------------- parsing rules
    def parse(self, text):
        """Return (chromosome, variant) exactly as the user wrote them (no normalising)."""
        chrom = None
        m = re.search(r"\bchromosome\s+([A-Za-z0-9]+)", text, re.I)
        if m:
            chrom = m.group(1)
        else:
            m = re.search(r"\b(chr[0-9XYMxym]+)\b", text, re.I)
            if m:
                chrom = m.group(1)

        t = text.lower()
        known = list(self.engine.KNOWN_VARIANT_TYPES)
        hits = []
        for v in known:
            words = v.lower().replace("_", " ")
            first = v.split("_")[0].lower()
            unique_first = sum(1 for k in known if k.split("_")[0].lower() == first) == 1
            if words in t or (unique_first and len(first) >= 5 and first in t):
                hits.append(v)
        variant = hits[0] if len(hits) == 1 else None
        return chrom, variant

    # -------------------------------------------------------------- main loop
    def ask(self, text):
        trace = []
        chrom, variant = self.parse(text)
        trace.append(f"parsed request -> chromosome={chrom!r}, variant={variant!r}")

        if chrom is None:
            trace.append("no chromosome found; asking for clarification")
            return AgentResult(STATUS_CLARIFY, summary="Which chromosome do you mean?",
                               trace=trace)

        retries = 0
        while True:
            trace.append(f"run_query(chromosome={chrom!r}, variant_classification={variant!r})")
            try:
                rows = self.engine.run_query(chromosome=chrom, variant_classification=variant)
            except Exception as exc:
                trace.append(f"execution failure: {exc}")
                return AgentResult(STATUS_FAILURE, chromosome=chrom,
                                   variant_classification=variant, retries=retries,
                                   summary=f"Backend error: {exc}", trace=trace)

            if len(rows) > 0:
                n_samples = rows["Tumor_Sample_Barcode"].nunique()
                trace.append(f"{len(rows)} rows, {n_samples} distinct samples")
                note = " (after automatic correction)" if retries else ""
                summary = (f"{len(rows)} mutation records across {n_samples} distinct "
                           f"samples for {chrom}"
                           + (f" / {variant}" if variant else "") + note + ".")
                return AgentResult(STATUS_OK, rows, chrom, variant, retries,
                                   recovered=retries > 0, summary=summary, trace=trace)

            diag = self.engine.diagnose_empty_result(chrom, variant)
            trace.append(f"0 rows -> diagnosis: {diag['cause']} ({diag['detail']})")
            fix = diag.get("fix") or {}
            new_chrom = fix.get("chromosome", chrom)
            new_variant = fix.get("variant_classification", variant)
            can_retry = (new_chrom, new_variant) != (chrom, variant) and retries < self.max_retries
            if not can_retry:
                trace.append("no applicable fix or retry budget used; stopping")
                return AgentResult(STATUS_EMPTY, rows, chrom, variant, retries,
                                   summary=f"No records. {diag['detail']}", trace=trace)
            trace.append(f"applying fix {fix}; retry {retries + 1}/{self.max_retries}")
            chrom, variant = new_chrom, new_variant
            retries += 1