# llm_agent.py
import query_engine as qe

MAX_RETRIES = 3

VARIANT_KEYWORDS = {
    "missense": "Missense_Mutation", "nonsense": "Nonsense_Mutation",
    "silent": "Silent", "frame shift insertion": "Frame_Shift_Ins",
    "frame shift deletion": "Frame_Shift_Del", "splice site": "Splice_Site",
}

def parse_query(user_query: str):
    """STAND-IN for a real LLM tool call."""
    q = user_query.lower()
    variant_classification = next((v for k, v in VARIANT_KEYWORDS.items() if k in q), None)
    chromosome = next((tok for tok in q.replace(",", " ").split()
                        if tok.startswith("chr") or tok.isdigit()), None)
    return {"chromosome": chromosome, "variant_classification": variant_classification}

class GenomicsAgent:
    def __init__(self):
        self.transcript = []

    def answer(self, user_query: str):
        params = parse_query(user_query)
        retries = 0
        result = None
        while retries < MAX_RETRIES:
            result = qe.run_query(**params)
            if qe.validate_result(result) == "OK":
                break
            diagnosis = qe.diagnose_empty_result(params["chromosome"])
            if diagnosis["fix"] is None:
                break
            params.update(diagnosis["fix"])
            retries += 1

        explanation = self._explain(result, retries)
        return result, explanation, retries

    def _explain(self, result, retries):
        if result.empty:
            return "No matching mutations found, even after self-correction attempts."
        n = len(result)
        top_type = result["Variant_Classification"].mode()[0]
        n_patients = result["Tumor_Sample_Barcode"].nunique()
        retry_note = f" after {retries} self-correction step(s)" if retries else ""
        return (f"Found {n} real mutation(s) across {n_patients} patients{retry_note}. "
                f"Most common type: {top_type}, computed directly from the returned data.")


if __name__ == "__main__":
    agent = GenomicsAgent()
    result, explanation, retries = agent.answer("Show missense mutations on 7")
    for line in agent.transcript:
        print(line)
    print(f"\nFINAL RESULT: {len(result)} rows | retries: {retries}")
    print(f"EXPLANATION: {explanation}")