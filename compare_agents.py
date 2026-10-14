
# compare_agents.py
# AgentiQ-Genomics panel demonstration

import query_engine as qe
from llm_agent import GenomicsAgent

QUESTION = "Show missense mutations on chromosome 7"

print("=" * 65)
print("AGENTIQ-GENOMICS: FSM VS GEMINI + RAG")
print("=" * 65)

print("\nQUERY:", QUESTION)

# ------------------------------------------------
# FSM REFERENCE EXECUTION
# ------------------------------------------------

print("\n[1] FSM BASELINE")
print("-" * 65)

print("Run the guided FSM dialogue separately using:")
print("python fsm_baseline.py")

print("\nReference query-engine result for canonical inputs:")

fsm_reference = qe.execute_query(
    chromosome="chr7",
    variant_classification="Missense_Mutation"
)

print("Status:", fsm_reference["status"])
print("Mutations:", fsm_reference.get("n_mutations"))
print("Samples:", fsm_reference.get("n_samples"))

# ------------------------------------------------
# GEMINI + RAG
# ------------------------------------------------

print("\n[2] GEMINI + RAG")
print("-" * 65)

agent = GenomicsAgent()
result, explanation, retries = agent.answer(QUESTION)

for event in agent.transcript:
    print(event)

print("\nExplanation:", explanation)
print("Retries:", retries)

if result is not None:
    print("Returned rows:", len(result))

print("\n" + "=" * 65)
print("DEMONSTRATION COMPLETE")
print("=" * 65)
