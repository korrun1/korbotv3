# KorBot v3

Experimental Python and Rust code for forex strategy research, backtesting, and risk management.

**Status: development prototype.** End-to-end operation has not been validated. This repository does not establish profitability, a verified win rate, or production readiness. Performance figures in older documents are unverified and should not be treated as measured results.

## بالعربية

مشروع تجريبي لدراسة استراتيجيات الفوركس والاختبار على البيانات التاريخية وإدارة المخاطر. النسخة الحالية تحتاج إلى اختبارات تكامل قبل الاعتماد عليها. لا توجد نتائج منشورة تثبت الربحية أو نسب النجاح المذكورة في الوثائق القديمة.

## Repository map

| Area | Files |
| --- | --- |
| Configuration | `config.yaml`, `config_loader.py`, `.env.example` |
| Strategy and risk modules | `strategy_engine.py`, `risk_engine.py`, `market_intel.py` |
| Data and execution integrations | `data_layer.py`, `execution_engine.py`, `databases.py` |
| Research and UI | `backtester.py`, `ai_optimization.py`, `dashboard.py` |
| Experimental additions | `enhanced/`, `new_modules/` |
| Rust source | `Cargo.toml`, `lib.rs` |
| Offline configuration tests | `test_config_safety.py` |

Python files and `config.yaml` are in the repository root, not in `src/python_controller/` or `config/`. Older setup documents describe a different layout.

## Start with offline checks

These checks do not connect to a broker, send notifications, or place orders.

```sh
git clone https://github.com/korrun1/korbotv3.git
cd korbotv3
python -m venv .venv
```

Activate `.venv` using `.venv\Scripts\activate` on Windows or `source .venv/bin/activate` on Linux/macOS, then:

```sh
python -m pip install PyYAML python-dotenv
python -m unittest test_config_safety -v
```

The configuration tests cover the shipped YAML, default file location, credential redaction, and preservation of in-memory configuration when saving. They do **not** validate trading behavior or the whole project.

## Integration status

The broader dependency list is in `requirements.txt`. Broker integrations import MetaTrader5; other modules depend on Redis, technical-analysis, ML, and GUI packages. Full installation and startup remain to be verified in a suitable environment.

Known work remaining:

- Align configuration access across the orchestrator and modules: some expect nested dictionaries while the loader exposes dotted-key access.
- Repair legacy test discovery and run `test_core.py` with its required dependencies.
- Reconcile the Rust manifest with the actual source and benchmark layout.
- Validate paper execution using a fake broker and deterministic historical fixtures before any broker-connected use.
- Replace old performance statements with reproducible results, including data provenance, costs, and limitations.

Do not connect this prototype to a funded account. No trading engine was run as part of the configuration checks.

## Credentials

Use `.env.example` as a template for a local `.env`. Keep credentials and account data out of commits, logs, and issue reports. `TRADING_MODE=paper` is the template default; it is not a substitute for auditing execution paths. Generated logs, databases, local environments, and `.env` files are ignored by Git.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for reproducible bug reports and small, tested changes. Useful work includes offline test fixtures, installation fixes, and Arabic/English documentation improvements.

## License status

Earlier documentation displays an MIT badge, but this snapshot has no LICENSE file. A badge alone is not a complete license grant. The rights holder must confirm the intended license and third-party code provenance before a license is added.
