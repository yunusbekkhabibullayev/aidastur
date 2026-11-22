import json
import os
import sys
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.schemas import FactCheckRequest, VerdictEnum
from app.pipeline.fact_checker import fact_checker_pipeline

DATASET_PATH = Path(__file__).resolve().parent / "benchmark_dataset.json"


def evaluate_system(limit: int = None):
    """
    Fact-checking pipeline'ning aniqlik va sifat ko'rsatkichlarini
    (Accuracy, Precision, Recall, F1, Confusion Matrix) hisoblaydi.
    """
    if not DATASET_PATH.exists():
        print(f"Dataset topilmadi: {DATASET_PATH}")
        return

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if limit:
        data = data[:limit]

    print("=" * 65)
    print("       AI FACT CHECKER - SYSTEM BENCHMARK & EVALUATION       ")
    print("=" * 65)
    print(f"Jami test namunalari: {len(data)}\n")

    classes = [VerdictEnum.TRUE.value, VerdictEnum.FALSE.value, VerdictEnum.MISLEADING.value, VerdictEnum.UNVERIFIED.value]
    matrix = {true_c: {pred_c: 0 for pred_c in classes} for true_c in classes}

    correct_predictions = 0
    results_log = []

    for item in data:
        claim_id = item["id"]
        claim_text = item["claim"]
        expected = item["expected_verdict"]

        print(f"[{claim_id}] Tekshirilmoqda: '{claim_text}'")
        try:
            req = FactCheckRequest(text=claim_text, language=item.get("language", "auto"))
            res = fact_checker_pipeline.process(req)
            predicted = res.overall_verdict.value
            score = res.overall_reliability_score
        except Exception as e:
            print(f"  -> Xatolik: {e}")
            predicted = VerdictEnum.UNVERIFIED.value
            score = 25.0

        is_match = (predicted == expected)
        if is_match:
            correct_predictions += 1
            print(f"  -> Kutilgan: {expected} | Bashorat: {predicted} [TOG'RI] (Score: {score}%)")
        else:
            print(f"  -> Kutilgan: {expected} | Bashorat: {predicted} [XATO] (Score: {score}%)")

        matrix[expected][predicted] += 1
        results_log.append({
            "id": claim_id,
            "claim": claim_text,
            "expected": expected,
            "predicted": predicted,
            "score": score
        })

    # Metrics calculation
    total_samples = len(data)
    accuracy = correct_predictions / total_samples if total_samples > 0 else 0.0

    per_class_metrics = {}
    precisions = []
    recalls = []
    f1s = []

    for c in classes:
        tp = matrix[c][c]
        fp = sum(matrix[other][c] for other in classes if other != c)
        fn = sum(matrix[c][other] for other in classes if other != c)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        precisions.append(prec)
        recalls.append(rec)
        f1s.append(f1)

        per_class_metrics[c] = {
            "TP": tp, "FP": fp, "FN": fn,
            "Precision": round(prec, 3),
            "Recall": round(rec, 3),
            "F1": round(f1, 3)
        }

    macro_precision = sum(precisions) / len(classes)
    macro_recall = sum(recalls) / len(classes)
    macro_f1 = sum(f1s) / len(classes)

    print("\n" + "=" * 65)
    print("                     EVALUATION RESULTS                      ")
    print("=" * 65)
    print(f"Overall Accuracy:  {accuracy * 100:.2f}% ({correct_predictions}/{total_samples})")
    print(f"Macro Precision:   {macro_precision * 100:.2f}%")
    print(f"Macro Recall:      {macro_recall * 100:.2f}%")
    print(f"Macro F1-Score:    {macro_f1 * 100:.2f}%")

    print("\n--- PER-CLASS METRICS ---")
    print(f"{'Class':<12} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'TP':<4}")
    print("-" * 55)
    for c in classes:
        m = per_class_metrics[c]
        print(f"{c:<12} | {m['Precision']:<10} | {m['Recall']:<10} | {m['F1']:<10} | {m['TP']:<4}")

    print("\n--- CONFUSION MATRIX ---")
    hdr = "Actual \\ Pred"
    print(f"{hdr:<15} | " + " | ".join(f"{c:<10}" for c in classes))
    print("-" * 65)
    for actual in classes:
        row = [f"{matrix[actual][pred]:<10}" for pred in classes]
        print(f"{actual:<15} | " + " | ".join(row))
    print("=" * 65)

    return {
        "accuracy": accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "per_class": per_class_metrics,
        "confusion_matrix": matrix
    }


if __name__ == "__main__":
    evaluate_system()
