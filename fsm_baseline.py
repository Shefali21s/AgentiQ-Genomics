# fsm_baseline.py
import query_engine as qe

class GeCoAgentFSM:
    STATES = ["ASK_CHROMOSOME", "ASK_VARIANT_TYPE", "RUN_QUERY", "DONE"]

    def __init__(self):
        self.slots = {}
        self.transcript = []

    def log(self, msg):
        self.transcript.append(msg)

    def step(self, chromosome, variant_classification=None):
        self.log(f"[STATE: ASK_CHROMOSOME] -> user answers '{chromosome}'")
        self.slots["chromosome"] = chromosome

        self.log(f"[STATE: ASK_VARIANT_TYPE] -> user answers '{variant_classification}'")
        self.slots["variant_classification"] = variant_classification

        self.log("[STATE: RUN_QUERY] -> assembling and executing fixed-template query")
        result = qe.run_query(
            chromosome=self.slots["chromosome"],
            variant_classification=self.slots["variant_classification"],
        )

        if result.empty:
            self.log("[STATE: DONE] -> 0 rows returned. FSM has no mechanism to diagnose why.")
        else:
            self.log(f"[STATE: DONE] -> {len(result)} rows returned.")
        return result


if __name__ == "__main__":
    print("-- Query A: well-formed input --")
    fsm = GeCoAgentFSM()
    res = fsm.step(chromosome="chr7", variant_classification="Missense_Mutation")
    for line in fsm.transcript:
        print(line)
    print(f"RESULT: {len(res)} rows\n")

    print("-- Query B: realistic user input, '7' instead of 'chr7' (silent failure) --")
    fsm2 = GeCoAgentFSM()
    res2 = fsm2.step(chromosome="7", variant_classification="Missense_Mutation")
    for line in fsm2.transcript:
        print(line)
    print(f"RESULT: {len(res2)} rows  <-- silently empty\n")