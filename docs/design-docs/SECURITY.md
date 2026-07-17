# SECURITY.md

Security standards for the Stock Valuation harness.

## Secrets Management

- All credentials and API keys must be stored in a `.env` file that is gitignored
- Never hardcode secrets, tokens, or credentials in source files or config YAML
- The `.env` file must always be present in `.gitignore` — CI should verify this
- `.env.example` (committed) is the canonical template listing every expected env var with a placeholder value; update it whenever a new secret is introduced

## Logging Safety

- Log statements must never emit API keys, tokens, or personally identifiable information
- Redact sensitive values before passing them to any logger
- When logging external API responses, log field names and types — not raw values that could contain credentials

## External Data Validation

- All data received from yfinance or any external API must be parsed and validated before use
- Never access raw dict keys without existence checks (use `.get()` with a fallback or explicit key validation)
- Use typed dataclasses or Pydantic models at the data boundary so the shape is explicit and agent-legible
- Treat missing or unexpected fields as errors, not silent `None` values
