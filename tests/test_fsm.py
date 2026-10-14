"""Run with:  python -m pytest -q test_fsm_baseline.py   (or: python test_fsm_baseline.py)"""
import pandas as pd
from fsm_baseline import (FSMBaseline, State, Event, TransitionError,
                          STATUS_OK, STATUS_EMPTY, STATUS_INVALID, STATUS_FAILURE)


class FakeEngine:
    """Stands in for query_engine. Data uses chr-prefixed names, like the real MAF files."""
    def __init__(self, fail=False):
        self.fail = fail
        self.df = pd.DataFrame({
            "Chromosome": ["chr7", "chr7", "chr1"],
            "Variant_Classification": ["Missense_Mutation", "Silent", "Missense_Mutation"],
        })

    def run_query(self, chromosome, variant_classification):
        if self.fail:
            raise RuntimeError("backend down")
        d = self.df
        return d[(d.Chromosome == chromosome) &
                 (d.Variant_Classification == variant_classification)]


def make(fail=False):
    return FSMBaseline(engine=FakeEngine(fail=fail))


def test_happy_path_states_and_status():
    f = make()
    assert f.state == State.IDLE
    assert f.start() is not None and f.state == State.COLLECT_CHROMOSOME
    f.send("chr7");               assert f.state == State.COLLECT_VARIANT
    f.send("Missense_Mutation");  assert f.state == State.END
    assert f.status == STATUS_OK and len(f.result) == 1


def test_chr_mismatch_is_silent_empty_result():
    f = make()
    res, status = f.run(["7", "Missense_Mutation"])
    assert status == STATUS_EMPTY and len(res) == 0


def test_invalid_input_asks_again_then_recovers():
    f = make()
    res, status = f.run(["chr7", "missense", "Missense_Mutation"])
    assert status == STATUS_OK and len(res) == 1
    assert any("asking again" in line for line in f.transcript)


def test_too_many_invalid_aborts_with_invalid_status():
    f = make()
    res, status = f.run(["chr7", "x", "y", "z"])
    assert status == STATUS_INVALID and res is None and f.finished


def test_backend_failure_is_not_empty_result():
    f = make(fail=True)
    res, status = f.run(["chr7", "Missense_Mutation"])
    assert status == STATUS_FAILURE and f.error == "backend down"


def test_illegal_event_is_rejected():
    f = make()
    try:
        f._fire(Event.EXEC_OK)       # not allowed from IDLE
        assert False, "expected TransitionError"
    except TransitionError:
        pass


def test_no_input_accepted_after_end():
    f = make()
    f.run(["chr7", "Missense_Mutation"])
    try:
        f.send("chr1")
        assert False, "expected TransitionError"
    except TransitionError:
        pass


def test_reset_returns_to_idle():
    f = make()
    f.run(["chr7", "Missense_Mutation"])
    f.reset()
    assert f.state == State.IDLE and f.slots == {} and f.result is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)