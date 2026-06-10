.PHONY: help install run lint lint-fix fmt fmt-check typecheck test check clean check-env docs-install docs-serve docs-build

# Default video/output overridable on the command line:
#   make run INPUT=my_video.mp4 OUTPUT=./output MODEL=llama3 MAX=5 CROP_MODE=face CONTENT_MODE=talking-head
INPUT        ?= my_video.mp4
OUTPUT       ?= ./output
MODEL        ?= llama3
MAX          ?= 5
CROP_MODE    ?= face
CONTENT_MODE ?= talking-head
DYNAMIC      ?= 0

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies with Poetry
	poetry install

run: ## Run the pipeline (vars: INPUT, OUTPUT, MODEL, MAX, CROP_MODE, CONTENT_MODE, DYNAMIC=1)
	poetry run python shorts_factory.py \
		--input $(INPUT) \
		--output $(OUTPUT) \
		--model $(MODEL) \
		--max-shorts $(MAX) \
		--crop-mode $(CROP_MODE) \
		--content-mode $(CONTENT_MODE) \
		$(if $(filter 1 true yes,$(DYNAMIC)),--dynamic-subtitles,)

OLLAMA_HOST ?= http://localhost:11434

check-env: ## Verify CUDA, Ollama and FFmpeg are available
	poetry run python -c "import ctranslate2; print('CUDA devices:', ctranslate2.get_cuda_device_count())"
	@curl -s $(OLLAMA_HOST)/api/tags | poetry run python -c "import sys,json; d=json.load(sys.stdin); print('Ollama models:', [m['name'] for m in d.get('models',[])] or 'NONE pulled')" \
		|| echo "Ollama server NOT reachable at $(OLLAMA_HOST)"
	ffmpeg -version | head -n 1

lint: ## Lint the code with ruff
	poetry run ruff check .

lint-fix: ## Lint and apply safe ruff fixes
	poetry run ruff check --fix .

fmt: ## Format the code with ruff
	poetry run ruff format .

fmt-check: ## Check code formatting with ruff
	poetry run ruff format --check .

typecheck: ## Compile Python files to catch syntax errors
	poetry run python -m compileall -q shorts_factory.py shortificator

test: ## Run the test suite
	poetry run pytest

cov: ## Run the test suite and emit XML + HTML coverage reports
	poetry run pytest --cov-report=xml --cov-report=html

check: lint fmt-check typecheck ## Run lint, format check and syntax check

docs-install: ## Install documentation dependencies
	poetry install --only docs --no-root

docs-serve: ## Serve the documentation locally
	poetry run mkdocs serve

docs-build: ## Build the documentation site
	poetry run mkdocs build --strict

clean: ## Remove generated outputs and caches
	rm -rf $(OUTPUT) __pycache__ .pytest_cache .ruff_cache
	rm -rf .coverage coverage.xml htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
