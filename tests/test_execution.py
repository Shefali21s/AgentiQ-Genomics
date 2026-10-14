import query_engine as qe

result = qe.execute_query(
    chromosome="chr7",
    variant_classification="Missense_Mutation"
)

print("Status:", result["status"])
print("Mutations:", result.get("n_mutations"))
print("Samples:", result.get("n_samples"))