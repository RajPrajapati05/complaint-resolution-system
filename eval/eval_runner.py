import os
import json
import time
from dotenv import load_dotenv

from agents.router_agent import RouterAgent

load_dotenv()

EVAL_SET_PATH = "eval/eval_set.json"
EVAL_RESULTS_PATH = "eval/eval_results.json"


def run_eval():
    with open(EVAL_SET_PATH, "r", encoding="utf-8") as f:
        eval_set = json.load(f)

    router = RouterAgent()
    results = []
    total = len(eval_set)
    correct_category = 0
    correct_urgency = 0
    correct_compliance = 0

    print(f"\nRunning eval on {total} examples...\n")

    for item in eval_set:
        print(f"  [{item['id']}] {item['complaint_text'][:60]}...")
        t0 = time.time()

        try:
            prediction = router.route(item["complaint_text"])
            latency_ms = round((time.time() - t0) * 1000, 2)

            cat_correct = prediction["category"] == item["expected_category"]
            urg_correct = prediction["urgency"] == item["expected_urgency"]
            comp_correct = prediction["compliance_flag"] == item["expected_compliance_flag"]

            if cat_correct:
                correct_category += 1
            if urg_correct:
                correct_urgency += 1
            if comp_correct:
                correct_compliance += 1

            result = {
                "id": item["id"],
                "complaint_text": item["complaint_text"],
                "expected": {
                    "category": item["expected_category"],
                    "urgency": item["expected_urgency"],
                    "compliance_flag": item["expected_compliance_flag"],
                },
                "predicted": {
                    "category": prediction["category"],
                    "urgency": prediction["urgency"],
                    "compliance_flag": prediction["compliance_flag"],
                },
                "correct": {
                    "category": cat_correct,
                    "urgency": urg_correct,
                    "compliance_flag": comp_correct,
                },
                "all_correct": cat_correct and urg_correct and comp_correct,
                "latency_ms": latency_ms,
                "model_used": prediction.get("_model_used"),
                "notes": item.get("notes", ""),
            }

        except Exception as e:
            result = {
                "id": item["id"],
                "error": str(e),
                "all_correct": False,
                "latency_ms": None,
            }
            print(f"    ERROR: {e}")

        status = "PASS" if result.get("all_correct") else "FAIL"
        print(f"    {status} | cat={result.get('predicted', {}).get('category')} "
              f"urg={result.get('predicted', {}).get('urgency')} "
              f"comp={result.get('predicted', {}).get('compliance_flag')} "
              f"| {result.get('latency_ms')}ms")

        results.append(result)
        time.sleep(1)

    category_acc = round(correct_category / total * 100, 1)
    urgency_acc = round(correct_urgency / total * 100, 1)
    compliance_acc = round(correct_compliance / total * 100, 1)
    all_correct = sum(1 for r in results if r.get("all_correct"))
    overall_acc = round(all_correct / total * 100, 1)

    summary = {
        "total_examples": total,
        "category_accuracy": f"{category_acc}%",
        "urgency_accuracy": f"{urgency_acc}%",
        "compliance_flag_accuracy": f"{compliance_acc}%",
        "overall_accuracy": f"{overall_acc}%",
        "results": results,
    }

    with open(EVAL_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n=== EVAL SUMMARY ===")
    print(f"Category accuracy:        {category_acc}%  ({correct_category}/{total})")
    print(f"Urgency accuracy:         {urgency_acc}%  ({correct_urgency}/{total})")
    print(f"Compliance flag accuracy: {compliance_acc}%  ({correct_compliance}/{total})")
    print(f"Overall (all correct):    {overall_acc}%  ({all_correct}/{total})")
    print(f"\nFull results saved to {EVAL_RESULTS_PATH}")


if __name__ == "__main__":
    run_eval()