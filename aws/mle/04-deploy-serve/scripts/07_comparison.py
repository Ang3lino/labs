from __future__ import annotations


def main() -> int:
    headers = ["Option", "Latency", "Cold Start", "Cost/hr Est", "Ops Overhead", "Best For"]
    rows = [
        ["SageMaker Real-time", "Low", "None", "$$$", "Low", "Steady interactive inference"],
        ["SageMaker Serverless", "Medium", "Yes", "$", "Very Low", "Bursty / spiky traffic"],
        ["SageMaker Batch", "High", "N/A", "$", "Low", "Offline bulk scoring"],
        ["EKS", "Low", "None", "$$", "High", "Kubernetes-native platform control"],
        ["ECS Fargate", "Low-Med", "Some", "$$", "Medium", "Container serving without node ops"],
        ["Lambda", "Medium", "Yes", "$", "Low", "Tiny event-driven models"],
    ]

    widths = [max(len(row[idx]) for row in [headers, *rows]) for idx in range(len(headers))]

    def format_row(values: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(values)) + " |"

    print(format_row(headers))
    print("| " + " | ".join("-" * widths[idx] for idx in range(len(headers))) + " |")
    for row in rows:
        print(format_row(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
