"""
demo.py  -  one command for the whole presentation

  python demo.py              run all three parts
  python demo.py --pause      wait for Enter between parts
  python demo.py --fsm-live   interactive FSM dialogue only
"""
import argparse
import query_engine as qe
from fsm_baseline import FSMBaseline
from rule_agent import RuleBasedAgent


def banner(text):
    print("\n" + "=" * 70 + f"\n{text}\n" + "=" * 70)


def wait(args):
    if args.pause:
        input("\n[Enter] to continue...")


def part_fsm():
    banner("PART 1  FSM baseline (fixed path, no diagnosis)")
    print("\nCase 1: user types '7' instead of 'chr7'")
    f = FSMBaseline()
    f.run(["7", "Missense_Mutation"])
    f.report()
    print("\nCase 2: invalid variant, FSM asks again (validation loop)")
    f = FSMBaseline()
    f.run(["chr7", "missense", "Missense_Mutation"])
    f.report()


def part_agent():
    banner("PART 2  Rule-based diagnostic and retry prototype (not an LLM)")
    request = "Show missense mutations on chromosome 7."
    print(f"\nRequest: {request}\n")
    res = RuleBasedAgent().ask(request)
    for line in res.trace:
        print("  -", line)
    print(f"\nSTATUS : {res.status}   (retries: {res.retries}, recovered: {res.recovered})")
    print(f"ANSWER : {res.summary}")


def part_data():
    banner("PART 3  Dataset check (numbers come from the loaded files)")
    s = qe.search_schema()
    print(f"Mutation records : {s['n_mutations']}")
    print(f"Distinct samples : {s['n_samples']}")
    print(f"Genome assembly  : {s['assembly']}")
    print(f"Variant classes  : {len(s['variant_classifications'])}")
    rows = qe.run_query("chr7", "Missense_Mutation")
    print(f"chr7 + Missense_Mutation: {len(rows)} records, "
          f"{rows['Tumor_Sample_Barcode'].nunique()} distinct samples")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pause", action="store_true")
    ap.add_argument("--fsm-live", action="store_true")
    args = ap.parse_args()

    if args.fsm_live:
        FSMBaseline().interactive()
    else:
        part_fsm(); wait(args)
        part_agent(); wait(args)
        part_data()