run:
	uv run python -m src.main

tests:
	pytest tests/ -o log_cli=true

tests_coverage:
	pytest --cov=. tests/

.PHONY: run tests tests_coverage build-docker
