# Data governance

Classify inputs before use:

| Class | Examples | Default handling |
|---|---|---|
| Public | official rules, public judging rubric | may be cited with access date |
| Team-private | skills, budget, unpublished strategy | local store; disclose to providers only with consent |
| Restricted | NDA material, personal identifiers | do not ingest without documented authority |
| Third-party | public datasets, prior submissions, external documentation | retain source terms; link instead of copying |

Do not include secrets in briefs or logs. `.env` and `.rajih/` are ignored by Git. Redact exports before sharing, and obtain authorization before processing personal, restricted, or third-party data.

