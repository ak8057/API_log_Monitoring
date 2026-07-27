# ML Inference Service

Optional anomaly-scoring service extracted from the cloned hackathon repository.

This service is not part of the default runtime path yet. It is being staged as a separate component so the current FastAPI + ELK workflow stays stable while the ML workflow is normalized.

Planned responsibilities:

- Read log records from the shared NDJSON stream.
- Apply the donor repo's anomaly-scoring models.
- Emit enriched anomaly documents to Elasticsearch.

Configuration should be moved to environment variables before enabling it in production-style runs.
