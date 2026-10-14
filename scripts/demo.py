# demo.py
from fsm_baseline import GeCoAgentFSM
from llm_agent import GenomicsAgent

QUERY_VARIANT_TYPE = "Missense_Mutation"
QUERY_CHROMOSOME_AS_USER_TYPES_IT = "7"   # realistic phrasing — missing 'chr' prefix
QUERY_NL = f"Show {QUERY_VARIANT_TYPE.replace('_', ' ').lower()} mutations on {QUERY_CHROMOSOME_AS_USER_TYPES_IT}"


def main():
    print("#" * 70)
    print("  AgentiQ-Genomics — Mid-Term Live Demo (Real TCGA Data)")
    print(f"  Same realistic query to both systems: \"{QUERY_NL}\"")
    print("#" * 70)

    print("\n" + "=" * 70)
    print(" SYSTEM 1: GeCoAgent-style FSM Baseline (rigid, scripted)")
    print("=" * 70)
    fsm = GeCoAgentFSM()
    fsm_result = fsm.step(
        chromosome=QUERY_CHROMOSOME_AS_USER_TYPES_IT,
        variant_classification=QUERY_VARIANT_TYPE,
    )
    for line in fsm.transcript:
        print(" ", line)
    print(f"  >> FSM FINAL RESULT: {len(fsm_result)} rows. No explanation given.")

    print("\n" + "=" * 70)
    print(" SYSTEM 2: AgentiQ-Genomics LLM Agent (plans, self-corrects, explains)")
    print("=" * 70)
    agent = GenomicsAgent()
    agent_result, explanation, retries = agent.answer(QUERY_NL)
    for line in agent.transcript:
        print(" ", line)
    print(f"  >> AGENT FINAL RESULT: {len(agent_result)} rows after {retries} retry(ies).")
    print(f"  >> EXPLANATION: {explanation}")

    print("\n" + "=" * 70)
    print(" HEADLINE COMPARISON")
    print("=" * 70)
    print(f"  {'Metric':<28}{'FSM Baseline':<20}{'LLM Agent':<20}")
    print(f"  {'-'*28}{'-'*20}{'-'*20}")
    print(f"  {'Rows returned':<28}{len(fsm_result):<20}{len(agent_result):<20}")
    print(f"  {'Self-corrected?':<28}{'No':<20}{'Yes' if retries else 'No':<20}")
    print(f"  {'Explanation given?':<28}{'No':<20}{'Yes':<20}")


if __name__ == "__main__":
    main()