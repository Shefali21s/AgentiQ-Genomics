"""python test_rule_agent.py   (uses a temporary CSV, not your real data)"""
import os, tempfile
import pandas as pd

tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
pd.DataFrame({
    "Chromosome": ["chr7", "chr7", "chr7", "chr1", "chrX"],
    "Variant_Classification": ["Missense_Mutation", "Silent", "Missense_Mutation",
                               "Nonsense_Mutation", "Missense_Mutation"],
    "Tumor_Sample_Barcode": ["A", "B", "C", "A", "D"],
    "NCBI_Build": ["GRCh38"] * 5}).to_csv(tmp.name, index=False)
os.environ["AGENTIQ_DATA"] = tmp.name

import query_engine as qe
from rule_agent import RuleBasedAgent, STATUS_OK, STATUS_EMPTY, STATUS_CLARIFY, STATUS_FAILURE


def test_parse():
    a = RuleBasedAgent()
    assert a.parse("Show missense mutations on chromosome 7.") == ("7", "Missense_Mutation")
    assert a.parse("silent variants on chr1") == ("chr1", "Silent")
    assert a.parse("show everything") == (None, None)


def test_recovers_from_chr_prefix_mismatch():
    r = RuleBasedAgent().ask("Show missense mutations on chromosome 7.")
    assert r.status == STATUS_OK and r.recovered and r.retries == 1
    assert r.chromosome == "chr7" and len(r.rows) == 2
    assert "2 mutation records across 2 distinct samples" in r.summary


def test_no_retry_when_already_correct():
    r = RuleBasedAgent().ask("missense mutations on chr7")
    assert r.status == STATUS_OK and r.retries == 0 and not r.recovered


def test_valid_zero_rows_is_empty_not_failure_and_not_retried():
    r = RuleBasedAgent().ask("nonsense mutations on chrX")
    assert r.status == STATUS_EMPTY and r.retries == 0


def test_unknown_chromosome_stops_without_fix():
    r = RuleBasedAgent().ask("missense mutations on chromosome 99")
    assert r.status == STATUS_EMPTY and r.retries == 0


def test_missing_chromosome_asks_for_clarification():
    r = RuleBasedAgent().ask("show missense mutations")
    assert r.status == STATUS_CLARIFY


def test_retry_budget_zero_does_not_retry():
    r = RuleBasedAgent(max_retries=0).ask("missense mutations on chromosome 7")
    assert r.status == STATUS_EMPTY and r.retries == 0


def test_backend_exception_is_failure():
    class Broken:
        KNOWN_VARIANT_TYPES = {"Silent"}
        def run_query(self, **kw): raise RuntimeError("backend down")
    r = RuleBasedAgent(engine=Broken()).ask("silent on chr1")
    assert r.status == STATUS_FAILURE and "backend down" in r.summary


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("PASS", n)