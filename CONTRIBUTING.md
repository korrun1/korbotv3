# Contributing

KorBot v3 is a development prototype. Please keep changes focused and reproducible.

## Bug reports

Include your operating system, Python version, repository revision, minimal reproduction steps, expected behavior, actual behavior, and a sanitized traceback. Never include passwords, tokens, account numbers, or private trading records.

## Local validation

Install PyYAML and python-dotenv in a virtual environment, then run:

```sh
python -m unittest test_config_safety -v
```

This is a narrow offline suite. The legacy test_core.py suite and broker integration are not yet validated. Do not run live trading to test a contribution.

## Changes

Describe the concrete problem, explain the change, and include a regression test when fixing behavior. Use synthetic fixtures and fake services. Document any test you could not run. Preserve attribution and ensure you have rights to contribute code; the repository license is pending owner confirmation.

## Current priorities

1. Consistent configuration interfaces across modules.
2. Offline broker and market-data fixtures.
3. Working legacy tests and reproducible dependency setup.
4. Rust build layout reconciliation.
5. Accurate Arabic and English documentation.

Do not submit generated activity, duplicate changes, or unsupported performance claims to increase contribution counts.
