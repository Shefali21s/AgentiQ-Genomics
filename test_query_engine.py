import query_engine as qe

print(qe.search_schema())
print(qe.run_query("chr7").shape)
print(qe.run_query("7"))  # should be empty — then test diagnose
print(qe.diagnose_empty_result("7"))
