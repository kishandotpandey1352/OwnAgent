import evaluate
from bert_score import score
from sklearn.metrics import f1_score


def main():
    print("=" * 80)
    print("Day 6 Evaluation Setup Check")
    print("=" * 80)

    predictions = [
        "Revenue increased because of stronger cloud demand.",
        "The company faces supplier concentration risk.",
    ]

    references = [
        "Revenue grew due to strong demand for cloud services.",
        "The company is exposed to supplier concentration risk.",
    ]

    print("\nLoading ROUGE metric")
    rouge = evaluate.load("rouge")

    rouge_result = rouge.compute(
        predictions=predictions,
        references=references,
    )

    print("\nROUGE result:")
    for metric, value in rouge_result.items():
        print(f"{metric}: {value:.4f}")

    print("\nRunning BERTScore")
    precision, recall, f1 = score(
        predictions,
        references,
        lang="en",
        verbose=False,
    )

    bertscore_result = {
        "precision": float(precision.mean()),
        "recall": float(recall.mean()),
        "f1": float(f1.mean()),
    }

    print("\nBERTScore result:")
    for metric, value in bertscore_result.items():
        print(f"{metric}: {value:.4f}")

    print("\nRunning classification F1 example")
    true_labels = [1, 0, 1, 1, 0]
    predicted_labels = [1, 0, 0, 1, 0]

    classification_f1 = f1_score(true_labels, predicted_labels)

    print(f"F1 score: {classification_f1:.4f}")

    print("\n" + "=" * 80)
    print("Evaluation setup check passed")
    print("=" * 80)


if __name__ == "__main__":
    main()