# RELIABILITY.md

Reliability and observability standards for the Stock Valuation harness.

## Error Handling

- **Fail fast**: On any external API failure, raise immediately with a clear, structured error message
- No silent retries, no fallbacks, no returning `None` on failure
- The caller is responsible for deciding whether to retry — the data layer does not retry internally

## API Timeout

- All external API calls (yfinance and any future integrations) must enforce a **10-second hard timeout**
- Raise `TimeoutError` with context (ticker, operation) if the deadline is exceeded
- Do not set a timeout at the caller level and forget it — the timeout must be enforced at the fetch boundary

## Logging

- All log output uses Python's `logging` module with a **structured JSON formatter**
- `print()` statements are not permitted in source code
- Use `%s` placeholder style in log calls — never f-strings or `+` concatenation:
  ```python
  # correct
  logger.info('Fetched ticker: %s, price: %s', ticker, price)
  # wrong
  logger.info(f'Fetched ticker: {ticker}, price: {price}')
  ```
  This enables lazy rendering (skipped if log level is filtered) and queryable log patterns.
- Log levels:
  - `DEBUG`: diagnostic detail useful for agent inspection (raw field values, intermediate calculations)
  - `INFO`: normal operational events (ticker fetched, valuation complete)
  - `WARNING`: recoverable issues (missing optional field, falling back to estimate)
  - `ERROR`: failures that abort the current operation

## Merge Bar

A change is safe to merge when all three of the following pass:

1. `pytest` suite passes with zero failures
2. `ruff check` and `mypy` report zero errors
3. `python src/eval_buffett.py <known_ticker> -v` returns the expected intrinsic value output
