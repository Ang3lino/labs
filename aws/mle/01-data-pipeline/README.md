# Lab 01 — Data Pipeline (Domain 1: Data Preparation)

## Theory

Data format selection depends on access pattern, schema evolution needs, and downstream tooling. **Parquet** is columnar and compressed, so it is best for analytics and model training scans over large datasets in S3/Athena/Glue. **CSV** is human-readable and easy for ingestion/bootstrap, but lacks schema/type safety and is inefficient at scale. **RecordIO** is a serialized record stream format used in some high-throughput ML training pipelines where sequential binary reads matter. **ORC** is another columnar format optimized for Hive-like warehouse workloads with strong compression and predicate pushdown. **Avro** is row-oriented with explicit schema evolution support, making it useful for event streams and interchange where backward/forward compatibility matters.

S3 storage class choice is a cost/latency trade-off: **S3 Standard** for frequent access and low latency, **S3 Intelligent-Tiering** for variable/unpredictable patterns, **S3 Standard-IA** for infrequent but fast retrieval, and **Glacier classes** for archival and compliance. For study context, raw and processed training data usually starts in Standard/Intelligent-Tiering, then transitions by lifecycle policy.

AWS Glue ETL concepts are core for exam scenarios: **crawlers** infer schema/partitions from data in S3 and populate the **Glue Data Catalog**; **Glue jobs** execute Spark ETL for cleaning, transformation, and format conversion; the **catalog** becomes a shared metadata layer for Athena, Redshift Spectrum, and SageMaker feature pipelines.

SageMaker Feature Store has two serving modes. The **online store** is optimized for low-latency, point-in-time feature retrieval during real-time inference. The **offline store** persists historical features (typically in S3) for batch training, backfills, and reproducible dataset generation.

Data quality should be explicit and automated. Glue Data Quality uses DQDL rules to enforce completeness, uniqueness, schema expectations, and value domains before downstream model training. Bias should also be checked early: SageMaker Clarify pre-training analysis surfaces label/facet imbalance using metrics like **Class Imbalance (CI)** and **Difference in Proportions of Labels (DPL)**.

## Key Terms for Self-Study

- Apache Parquet columnar format
- AWS Glue Crawler
- AWS Glue ETL Job
- SageMaker Feature Store online vs offline
- SageMaker Clarify pre-training bias
- class imbalance (CI)
- difference in proportions of labels (DPL)
- AWS Glue Data Quality DQDL rules
- S3 Transfer Acceleration
- data deduplication strategies

## Interview Talking Points

I built a data pipeline that ingests raw CSV fraud data into S3, transforms it to Parquet via Glue ETL, engineers features, detects class imbalance bias with Clarify, and stores features in Feature Store for real-time serving.

## Exam Tips

Domain 1 is 28% and the heaviest exam domain, so optimize repetition on ingestion, transformation, quality, and feature management decisions. Know when to use Glue (managed serverless ETL/catalog), EMR (more control/custom big-data frameworks), and Data Wrangler (interactive prep workflows). Know Feature Store online (low-latency lookup) vs offline (batch training) responsibilities. Know Clarify pre-training bias metrics by name, especially CI and DPL.

## References

- *Designing ML Systems* Ch.7 (Feature Store)
- StatQuest "Data Preprocessing" playlist
- AWS Skill Builder "Data Engineering on AWS"
