# Lab 07 — Book NLP Analysis (Domains 1+2)

## Theory

This lab demonstrates a practical NLP pipeline for long-form psychology text: **tokenization → embedding-oriented feature extraction → analysis**. We preprocess two public-domain books into chapter-level units, then run scalable API-based NLP plus LLM-based structured interpretation.

At scale, **sentiment analysis** gives chapter-by-chapter emotional trajectories and lets you compare arcs across books. **Entity recognition** identifies people, organizations, and core conceptual terms that form each author’s narrative network. **Topic modeling** and **text classification** provide a machine-assisted way to map themes and recurring constructs over long documents.

For higher-level interpretation, we use LLM prompting for structured psychology analysis: extracting **personality trait signals** and **behavioral pattern descriptions** in a fixed JSON schema. Prompt engineering matters here: constrain output shape, define accepted frameworks, and ask for evidence spans from source excerpts.

The lab also shows how to combine **classical NLP services (Amazon Comprehend)** with **LLM reasoning (Amazon Bedrock)**. Comprehend handles robust, repeatable extraction tasks, while Bedrock adds interpretable synthesis around frameworks like Big Five and attachment styles.

## Key Terms for Self-Study

- `sentiment analysis`
- `entity recognition`
- `topic modeling`
- `text classification`
- `tokenization`
- `BERT embeddings`
- `prompt engineering`
- `Amazon Comprehend custom classification`
- `Bedrock structured output`
- `psychology Big Five personality traits (OCEAN)`
- `attachment theory`
- `cognitive behavioral patterns`
- `NLP pipeline`

## Interview Talking Points

"I built an NLP analysis pipeline that processes psychology and dating books: Comprehend extracts sentiment and entities at scale, Bedrock with structured prompts identifies personality traits (Big Five/OCEAN model), attachment styles, and behavioral patterns. The pipeline outputs structured JSON reports comparing themes across books."

## Exam Context

This lab reinforces Domain 2 (AI services — Comprehend, Bedrock) and Domain 1 (text data preparation).

## References

- *Attached* (Amir Levine — attachment theory)
- *Models of the Mind* (Grace Lindsay)
- *Thinking, Fast and Slow* (Kahneman)
- *NLP with Transformers* (O'Reilly)
