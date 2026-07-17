# TESTING.md

Testing standards for the Stock Valuation harness.

## Coverage Target

- **95% line coverage** across `src/` is the minimum merge bar
- Enforced by `pytest --cov=src --cov-fail-under=95`
- Coverage configuration lives in `pyproject.toml` under `[tool.pytest.ini_options]`
- Do not exclude lines with `# pragma: no cover` unless the line is unreachable by design (e.g., a `TYPE_CHECKING` block)

## File Layout

Test files mirror `src/` one-to-one:

```
src/data_fetcher.py         → tests/test_data_fetcher.py
src/eval_buffett.py         → tests/test_eval_buffett.py
src/stock_data.py           → tests/test_stock_data.py
src/stock_screening.py      → tests/test_stock_screening.py
src/eval_index_valuation.py → tests/test_eval_index_valuation.py
src/index_tickers.py        → tests/test_index_tickers.py
src/stock_classification.py → tests/test_stock_classification.py
src/logging_config.py       → tests/test_logging_config.py
```

Shared fixtures and helpers live in `tests/conftest.py`. Never put shared fixtures inside individual test files.

## Naming Conventions

| Thing | Pattern | Example |
|---|---|---|
| Test function | `test_<fn>_<scenario>` | `test_get_shares_outstanding_prefers_implied` |
| Factory helper | `make_<object>(...)` | `make_valuation(discount_rate=0.10)` |
| Fixture | noun describing what it provides | `aapl_cache`, `empty_series` |

Scenario names should describe behavior, not implementation: `test_discount_cash_flows_reverses_compounding` not `test_discount_cash_flows_line_47`.

## What to Test

Test every public function and every meaningful private function (`_` prefix) that encodes non-trivial logic. For each function, cover:

1. **Happy path** — typical valid input produces the correct output
2. **Edge cases** — empty Series/DataFrame, zero values, `None` fields, single-element inputs
3. **Boundary conditions** — values at the cap/floor (e.g., growth capped at `growth_cap`)
4. **Error cases** — expected exceptions raised with correct message and type
5. **Branching logic** — each `if`/`elif` branch exercised at least once

Do **not** test:
- Private implementation details that are already covered transitively by public function tests
- Python builtins or third-party library behavior
- CLI `argparse` wiring (covered by smoke tests, not unit tests)

## Mocking Rules

**Never make real network calls in tests.** All yfinance, HTTP, and file-system access must be mocked.

Mock at the **module boundary**, not inside the function under test:

```python
# Correct — patch where the name is used
with patch("eval_buffett.yf.Ticker"):
    ...

# Wrong — patching the original definition doesn't intercept the import alias
with patch("yfinance.Ticker"):
    ...
```

Standard patterns for this codebase:

```python
# Mocking a yf.Ticker / StockDataCache
stock = MagicMock()
stock.ticker = "AAPL"
type(stock).info = PropertyMock(return_value={"marketCap": 3_000_000_000_000})
stock.cashflow = pd.DataFrame(...)

# Wrapping in StockDataCache (preferred over raw MagicMock for data-layer tests)
cache = StockDataCache(stock)

# Patching a top-level function in a module
with patch("stock_classification.is_bank_company", return_value=True):
    ...
```

Never mock internal helpers to make tests pass — that hides real bugs. If you need to mock a helper, the unit under test is probably too large.

## Fixture and Factory Conventions

Use a `make_*` factory function (not a fixture) when:
- Construction requires patching (e.g., `BuffettValuation` hits yfinance in `__init__`)
- Tests need slightly different variants of the same object

```python
def make_valuation(**kwargs: object) -> BuffettValuation:
    with (
        patch("eval_buffett.yf.Ticker"),
        patch("eval_buffett.is_bank_company", return_value=False),
    ):
        return BuffettValuation(ticker="TEST", **kwargs)  # type: ignore[arg-type]
```

Use `@pytest.fixture` when:
- The object is shared across many tests in the file and construction is cheap
- The object requires teardown (`yield` fixture)

Put fixtures used in only one test file at the top of that file. Fixtures used in two or more files go in `tests/conftest.py`.

## Assertion Style

- Use `pytest.approx` for all float comparisons: `assert result == pytest.approx(3.14, rel=1e-3)`
- Use `abs(result - expected) < tolerance` only when the tolerance has domain meaning (e.g., ±$0.01 per share)
- Use `pytest.raises` with `match=` to assert both the exception type and message:

```python
with pytest.raises(TimeoutError, match="timed out"):
    _fetch_with_timeout(slow_fn, "AAPL", "info")
```

- Prefer specific assertions over `assert result is not None` alone — also assert the value
- One logical assertion per test is a goal, not a rule; group tightly related assertions together

## Test Isolation

- Each test must be fully independent: no shared mutable state, no test ordering assumptions
- Do not mutate module-level globals in tests — use `monkeypatch` if you must change an env var or config value
- If a test creates files or directories, clean them up with a `tmp_path` fixture or `teardown`

## Import Style

Test files follow the same import rules as `src/` (see `DESIGN.md`), plus:

```python
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from module_under_test import function_under_test
```

No relative imports. Always import from the module name directly (pytest configures `src/` on the path via `pythonpath = ["src"]` in `pyproject.toml`).

## Running Tests

```bash
# Full suite with coverage
.SimpleEnv/bin/pytest --cov=src --cov-report=term-missing

# Single test file
.SimpleEnv/bin/pytest tests/test_data_fetcher.py -v

# Single test
.SimpleEnv/bin/pytest tests/test_data_fetcher.py::test_fetch_with_timeout_raises_timeout_error_on_slow_call -v

# Fail fast on first failure
.SimpleEnv/bin/pytest -x
```

## Merge Bar for Test Code

All four checks must pass before a PR touches `tests/`:

```bash
ruff format .          # auto-formats; commit result if it changes anything
ruff check src/ tests/ # zero lint errors
mypy src/              # zero type errors (tests/ excluded by default)
.SimpleEnv/bin/pytest --cov=src --cov-fail-under=95
```

Run them in this order: format first (so check sees the formatted output), then lint, then types, then tests. A PR that fails any one of these four is not mergeable.

Test files must be `ruff format`-clean and `ruff check`-clean. The `tests/**` override in `pyproject.toml` already suppresses annotation (`ANN`) and assert (`S101`) rules for test files — no other suppressions are permitted without a comment explaining why.
