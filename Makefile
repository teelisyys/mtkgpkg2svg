PROJECT_NAME=mtkgpkg2svg

poetry.lock: pyproject.toml
	poetry lock --no-update --no-interaction

.venv: poetry.lock
	poetry install --no-root
	@touch .venv

.PHONY: lint
lint: build
	poetry run isort --check $(PROJECT_NAME)
	poetry run black --check $(PROJECT_NAME)
	poetry run pylint --rcfile=.pylintrc $(PROJECT_NAME)
	#poetry run flake8 --max-line-length=124 $(PROJECT_NAME)
	poetry run mypy --show-error-codes --strict --strict-equality --warn-unreachable  $(PROJECT_NAME)


.PHONY: format
format:
	poetry run isort $(PROJECT_NAME)
	poetry run black $(PROJECT_NAME)

.PHONY: build
build: .venv

.PHONY: run
run: build
	poetry run python -m $(PROJECT_NAME)


.PHONY: test
test:
	poetry run python -m unittest test/*py

.PHONY: check
check: lint test
