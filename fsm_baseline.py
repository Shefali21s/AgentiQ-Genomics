"""
fsm_baseline.py  -  FSM baseline for AgentiQ-Genomics

A table-driven finite-state machine that mirrors SRS Figure 5:

  IDLE -> COLLECT_CHROMOSOME -> COLLECT_VARIANT -> EXECUTE -> DISPLAY -> END
              ^   | invalid          ^   | invalid
              +---+ (ask again)      +---+ (ask again)

Rules that make it a real FSM:
  * The machine is always in exactly one state (self.state).
  * Every move is looked up in TRANSITIONS as (state, event) -> next_state.
    An (state, event) pair that is not in the table raises an error.
  * Guards (validators) decide which event fires: INPUT_VALID or INPUT_INVALID.
  * Fixed path, no diagnosis: a '7' vs 'chr7' mismatch returns an empty result,
    and the FSM reports it as empty. It does NOT try to explain or fix it.

The engine is injected, so the FSM and the Gemini agent can share one
QueryEngine, and the FSM can be tested without the dataset.
"""

from enum import Enum


class State(Enum):
    IDLE = "IDLE"
    COLLECT_CHROMOSOME = "COLLECT_CHROMOSOME"
    COLLECT_VARIANT = "COLLECT_VARIANT"
    EXECUTE = "EXECUTE"
    DISPLAY = "DISPLAY"
    END = "END"


class Event(Enum):
    START = "START"
    INPUT_VALID = "INPUT_VALID"
    INPUT_INVALID = "INPUT_INVALID"
    TOO_MANY_INVALID = "TOO_MANY_INVALID"
    EXEC_OK = "EXEC_OK"
    EXEC_ERROR = "EXEC_ERROR"
    FINISH = "FINISH"
    RESET = "RESET"


# (current state, event) -> next state.  This table IS the state diagram.
TRANSITIONS = {
    (State.IDLE, Event.START): State.COLLECT_CHROMOSOME,

    (State.COLLECT_CHROMOSOME, Event.INPUT_VALID): State.COLLECT_VARIANT,
    (State.COLLECT_CHROMOSOME, Event.INPUT_INVALID): State.COLLECT_CHROMOSOME,
    (State.COLLECT_CHROMOSOME, Event.TOO_MANY_INVALID): State.END,

    (State.COLLECT_VARIANT, Event.INPUT_VALID): State.EXECUTE,
    (State.COLLECT_VARIANT, Event.INPUT_INVALID): State.COLLECT_VARIANT,
    (State.COLLECT_VARIANT, Event.TOO_MANY_INVALID): State.END,

    (State.EXECUTE, Event.EXEC_OK): State.DISPLAY,
    (State.EXECUTE, Event.EXEC_ERROR): State.END,

    (State.DISPLAY, Event.FINISH): State.END,

    (State.END, Event.RESET): State.IDLE,
}

PROMPTS = {
    State.COLLECT_CHROMOSOME: "Which chromosome? (e.g. chr7)",
    State.COLLECT_VARIANT: "Which variant classification? (e.g. Missense_Mutation)",
}

# Final status of a run. Matches SRS FR-07: invalid / empty / failure are distinct.
STATUS_OK = "ok"
STATUS_EMPTY = "empty_result"
STATUS_INVALID = "invalid_input"
STATUS_FAILURE = "execution_failure"

DEFAULT_VARIANTS = frozenset({
    "Missense_Mutation", "Nonsense_Mutation", "Silent",
    "Frame_Shift_Del", "Frame_Shift_Ins", "In_Frame_Del", "In_Frame_Ins",
    "Splice_Site", "Translation_Start_Site", "Nonstop_Mutation",
})


class TransitionError(Exception):
    """Raised when an event is not allowed in the current state."""


class FSMBaseline:
    def __init__(self, engine=None, valid_variants=DEFAULT_VARIANTS, max_invalid=3):
        # engine must expose run_query(chromosome=..., variant_classification=...)
        # and return a pandas DataFrame (empty DataFrame = valid zero-row result).
        if engine is None:
            import query_engine as engine  # the shared engine module
        self.engine = engine
        self.valid_variants = set(valid_variants)
        self.max_invalid = max_invalid
        self.reset()

    # ---------- lifecycle ----------
    def reset(self):
        self.state = State.IDLE
        self.slots = {}
        self.invalid_count = 0
        self.result = None
        self.error = None
        self.status = None
        self.transcript = []

    def start(self):
        """IDLE -> COLLECT_CHROMOSOME. Returns the first prompt."""
        self._fire(Event.START)
        return self.prompt()

    def prompt(self):
        return PROMPTS.get(self.state)

    @property
    def finished(self):
        return self.state == State.END

    # ---------- core ----------
    def _fire(self, event):
        key = (self.state, event)
        if key not in TRANSITIONS:
            raise TransitionError(f"event {event.name} not allowed in state {self.state.name}")
        nxt = TRANSITIONS[key]
        self._log(f"  {self.state.name} --{event.name}--> {nxt.name}")
        self.state = nxt

    def _log(self, msg):
        self.transcript.append(msg)

    # ---------- guards (validators) ----------
    @staticmethod
    def _valid_chromosome(text):
        # Baseline guard: checks that the input is a plausible chromosome token only.
        # It does NOT normalise '7' -> 'chr7'. That limitation is what the
        # Gemini agent is later compared on.
        t = text.strip()
        return bool(t) and t.replace("chr", "", 1).replace("_", "").isalnum()

    def _valid_variant(self, text):
        return text.strip() in self.valid_variants

    # ---------- one dialogue turn ----------
    def send(self, text):
        """Feed one user answer. Returns the next prompt, or None when finished."""
        if self.state not in (State.COLLECT_CHROMOSOME, State.COLLECT_VARIANT):
            raise TransitionError(f"no input expected in state {self.state.name}")

        text = (text or "").strip()
        self._log(f"[{self.state.name}] user: {text!r}")

        if self.state == State.COLLECT_CHROMOSOME:
            ok, slot = self._valid_chromosome(text), "chromosome"
        else:
            ok, slot = self._valid_variant(text), "variant_classification"

        if ok:
            self.slots[slot] = text
            self.invalid_count = 0
            self._fire(Event.INPUT_VALID)
        else:
            self.invalid_count += 1
            if self.invalid_count >= self.max_invalid:
                self.status = STATUS_INVALID
                self._log(f"  too many invalid answers ({self.invalid_count}); aborting")
                self._fire(Event.TOO_MANY_INVALID)
                return None
            self._log(f"  invalid {slot}; asking again "
                      f"({self.invalid_count}/{self.max_invalid})")
            self._fire(Event.INPUT_INVALID)
            return self.prompt()

        if self.state == State.EXECUTE:
            self._execute()
            return None
        return self.prompt()

    def _execute(self):
        self._log(f"[EXECUTE] fixed template with {self.slots}")
        try:
            self.result = self.engine.run_query(
                chromosome=self.slots["chromosome"],
                variant_classification=self.slots["variant_classification"],
            )
        except Exception as exc:  # backend failure is NOT an empty result
            self.error = str(exc)
            self.status = STATUS_FAILURE
            self._log(f"  execution failure: {self.error}")
            self._fire(Event.EXEC_ERROR)
            return

        self._fire(Event.EXEC_OK)          # EXECUTE -> DISPLAY
        if len(self.result) == 0:
            self.status = STATUS_EMPTY
            self._log("[DISPLAY] 0 rows. FSM has no mechanism to diagnose why.")
        else:
            self.status = STATUS_OK
            self._log(f"[DISPLAY] {len(self.result)} rows returned.")
        self._fire(Event.FINISH)           # DISPLAY -> END

    # ---------- helper for demos and the benchmark ----------
    def run(self, answers):
        """Scripted run: start, then feed answers until the machine reaches END."""
        self.reset()
        self.start()
        for text in answers:
            if self.finished:
                break
            self.send(text)
        return self.result, self.status

    # ---------- interactive use ----------
    def interactive(self):
        self.reset()
        msg = self.start()
        while not self.finished:
            msg = self.send(input(msg + " > "))
        self.report()

    def report(self):
        print("\n".join(self.transcript))
        print(f"STATUS: {self.status}")
        if self.result is not None:
            print(f"ROWS:   {len(self.result)}")


if __name__ == "__main__":
    scenarios = [
        ("A: well-formed input", ["chr7", "Missense_Mutation"]),
        ("B: '7' instead of 'chr7' (silent empty result)", ["7", "Missense_Mutation"]),
        ("C: invalid variant, then corrected (re-ask loop)",
         ["chr7", "missense", "Missense_Mutation"]),
        ("D: three invalid answers (abort)", ["chr7", "x", "y", "z"]),
    ]
    for title, answers in scenarios:
        print(f"-- Query {title} --")
        fsm = FSMBaseline()
        fsm.run(answers)
        fsm.report()
        print()