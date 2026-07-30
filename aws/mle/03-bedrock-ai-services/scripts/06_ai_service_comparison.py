from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionRow:
    use_case: str
    service: str
    reason: str


ROWS = [
    DecisionRow("Customer review sentiment in app", "Comprehend", "Managed NLP for sentiment/entities at low integration effort"),
    DecisionRow("Find objects/unsafe content in images", "Rekognition", "Purpose-built CV APIs for labels, moderation, and face features"),
    DecisionRow("Extract text from invoices/forms", "Textract", "OCR plus structure extraction for lines, forms, and tables"),
    DecisionRow("Call-center audio transcription", "Transcribe", "Managed speech-to-text with speaker/channel options"),
    DecisionRow("Real-time multilingual support chat", "Translate", "Fast neural translation between many languages"),
    DecisionRow("E-commerce next-best-product", "Personalize", "Recommendation models with behavioral signals"),
    DecisionRow("Intent-based support chatbot", "Lex", "NLU chatbot platform integrated with AWS services"),
    DecisionRow("Read generated answer aloud", "Polly", "Text-to-speech voices for accessibility and voice UX"),
    DecisionRow("General-purpose GenAI app", "Bedrock", "Single managed API layer across foundation models"),
    DecisionRow("Enterprise document search portal", "Kendra", "Enterprise search with connectors and relevance tuning"),
]


def _print_table() -> None:
    headers = ("Use Case", "Service", "Why")
    widths = [
        max(len(headers[0]), max(len(row.use_case) for row in ROWS)),
        max(len(headers[1]), max(len(row.service) for row in ROWS)),
        max(len(headers[2]), max(len(row.reason) for row in ROWS)),
    ]

    def line() -> str:
        return "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    print(line())
    print(
        f"| {headers[0].ljust(widths[0])} | {headers[1].ljust(widths[1])} | {headers[2].ljust(widths[2])} |"
    )
    print(line())
    for row in ROWS:
        print(f"| {row.use_case.ljust(widths[0])} | {row.service.ljust(widths[1])} | {row.reason.ljust(widths[2])} |")
    print(line())


def main() -> int:
    _print_table()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
