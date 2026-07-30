# Lab 03 - Bedrock & AI Services

## Theory

Foundation models (FMs) are large pre-trained models that can generalize across many tasks with prompting, few-shot examples, or light adaptation. In AWS, Amazon Bedrock gives managed API access to multiple FM providers in one place, while SageMaker JumpStart is better when you want tighter control over model artifacts, custom training flows, or deeper model lifecycle integration. Bedrock is usually the default for fast generative-AI productization; JumpStart is usually preferred when you need model customization and training ownership.

RAG (Retrieval-Augmented Generation) combines retrieval from your private knowledge sources with FM generation. Why use it: keep outputs grounded in current internal facts, reduce hallucinations, and avoid retraining for every document update. When to use it: enterprise Q&A, policy assistants, support copilots, or any workload needing up-to-date proprietary context. How it works: ingest documents, chunk/embed/index, retrieve relevant context at query time, then prompt the FM with that retrieved context.

Knowledge Bases for Bedrock provide managed ingestion, chunking, indexing, and retrieval orchestration so you can implement RAG with less custom plumbing. Agents for Bedrock orchestrate tool use and multi-step action planning against APIs/workflows. Guardrails for Bedrock apply policy constraints (safety categories, blocked topics, sensitive content handling) so generated responses stay within governance requirements.

AWS AI services complement Bedrock by solving focused modality tasks: Amazon Comprehend for NLP (sentiment/entities/key phrases/language), Amazon Rekognition for computer vision, Amazon Textract for OCR/document extraction, Amazon Transcribe for speech-to-text, Amazon Translate for multilingual translation, Amazon Personalize for recommendations, Amazon Lex for chatbot interfaces, and Amazon Polly for text-to-speech voice synthesis.

## Key Terms for Self-Study

- `Amazon Bedrock`
- `foundation model`
- `RAG (Retrieval-Augmented Generation)`
- `Bedrock Knowledge Bases`
- `Bedrock Agents`
- `Bedrock Guardrails`
- `Amazon Comprehend sentiment analysis`
- `Amazon Comprehend entity recognition`
- `Amazon Rekognition object detection`
- `Amazon Textract`
- `Amazon Personalize`
- `SageMaker JumpStart`
- `fine-tuning vs prompt engineering vs RAG`

## Interview Talking Points

"I built a RAG system using Bedrock Knowledge Bases over internal documents, compared foundation models for cost/latency, and integrated Comprehend for real-time sentiment analysis"

## Exam Tips

Know WHEN to use Bedrock vs SageMaker (managed FM API vs custom training). Know RAG vs fine-tuning decision tree. Know which AI service solves which problem (Comprehend=NLP, Rekognition=images, Textract=documents, Kendra=enterprise search).

## References

- AWS Bedrock documentation: https://docs.aws.amazon.com/bedrock/
- *Designing Machine Learning Systems* (Chapter 9)
- AWS re:Invent Bedrock talks (YouTube)
