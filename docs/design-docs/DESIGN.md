# DESIGN.md

Code architecture and design standards for the Stock Valuation harness.

## Type Safety

- All function signatures must have complete type annotations
- mypy must report zero errors — no `# type: ignore` without an explicit comment explaining why
- Use `X | None` for nullable values (not `Optional[T]`); if an argument can be `None`, it must be declared
- Never rely on implicit `None` returns
- Prefer abstract types (`collections.abc.Sequence`) over concrete types (`list`) in signatures

## Formatting

- All code must be Ruff-compliant at all times
- Maximum line length: **80 characters**
- No manual style debates — Ruff is the authority
- No unused imports, unused variables, or commented-out code blocks (enforced by Ruff)

## Naming Conventions

| Entity | Style |
|---|---|
| Modules | `lower_with_under` |
| Classes | `CapWords` |
| Constants | `CAPS_WITH_UNDER` |
| Functions / Methods | `lower_with_under()` |
| Variables | `lower_with_under` |
| Internal (private) | prefix with `_` |

## Imports

- Group in order: (1) future, (2) stdlib, (3) third-party, (4) local — separated by blank lines
- No relative imports; always use full package paths
- One import per line (exception: `from x import a, b` for closely related names)

## Exception Handling

- Always catch specific exception types (e.g., `except ValueError`, `except KeyError`)
- Bare `except:` and `except Exception:` are disallowed unless re-raised immediately
- Custom exception class names must end in `Error`
- Error messages must be actionable: include the ticker, the field, and the expected vs. actual value
- Do not use `assert` for runtime precondition validation in production code; `assert` is for tests only

## Resources and Context Managers

- Always use `with` statements for file and socket handling — never rely on `__del__` for cleanup
- For objects that don't support context managers natively, use `contextlib.closing()`

## Boolean and None Checks

- Always use `is None` / `is not None` explicitly — never `== None`
- Use implicit boolean testing for empty sequences: `if items:` not `if len(items) > 0:`
- Never compare booleans with `==`: use `if flag:` not `if flag == True:`

## Function and Module Size

- Prefer functions under **40 lines**; break longer functions into smaller, focused pieces
- No single source file should exceed **500 lines**; refactor into submodules if needed
- Module names must reflect their responsibility exactly — no generic names like `utils.py` or `helpers.py`

## Mutability

- Never use mutable objects as default argument values; use `None` and initialize inside the function
- Avoid module-level mutable globals; module-level constants (`CAPS_WITH_UNDER`) are encouraged

## Dependencies

- Any new runtime dependency requires a written rationale in `docs/design-docs/` before it is added
- Prefer the stdlib or an already-installed package over introducing a new one
- "Boring" is better: favor packages with stable APIs and strong representation in LLM training data
- See [Core Beliefs](design-docs/core-beliefs.md) for the philosophical basis

## File and Module Size

- No single source file should exceed 500 lines; split into submodules if needed
- Module names must reflect their responsibility exactly — no generic names like `utils.py` or `helpers.py`

## Layer Integrity

- Follow the dependency directions defined in [ARCHITECTURE.md](../ARCHITECTURE.md)
- The data layer (`data_fetcher.py`) must not import from the logic or application layers
- Cross-layer violations are not permitted and will be flagged in code review

## Data Layer Interface Convention

All public functions in the data layer (`data_fetcher.py`, `stock_data.py`, `stock_classification.py`) accept a `yf.Ticker` or `StockDataCache` object, not a raw ticker string. Callers must construct `yf.Ticker` once, wrap it in `StockDataCache`, and pass it down:

```python
# Correct — StockDataCache caches stock.info and protects all accesses
# with the 10-second timeout wrapper
from data_fetcher import StockDataCache
stock = StockDataCache(yf.Ticker(ticker))
data = get_stock_data(stock)
estimates = get_forward_estimates(stock)

# Acceptable for one-off calls (e.g., screening loops that only call
# get_stock_data once per ticker)
stock = yf.Ticker(ticker)
data = get_stock_data(stock)

# Wrong — do not pass raw strings to data layer functions
data = get_stock_data("AAPL")
```

`StockDataCache` lazily fetches `stock.info` on first access and caches it for the lifetime of the object, eliminating redundant network calls when multiple functions access the same ticker's info.

**Exceptions to the no-raw-string rule:**
- `get_cny_exchange_rate()` / `get_jpy_exchange_rate()` — take no arguments; FX tickers are hardcoded internally.
- `get_screening_metrics_edgar(ticker: str)` / `get_bulk_prices(tickers: list[str])` — designed for high-volume screening loops where constructing `yf.Ticker` per ticker is the rate-limiting bottleneck. These take raw ticker strings and hit EDGAR / `yf.download` directly. D/E ratio returned by `get_screening_metrics_edgar` is a true ratio (e.g., `1.5`), unlike the yfinance `debtToEquity` field which uses a ×100 representation (e.g., `150`).
