.PHONY: help inngest-dev

INNGEST_URL ?= http://127.0.0.1:8000/api/inngest

help:
	@echo "Available targets:"
	@echo "  inngest-dev   Run Inngest dev server"
	@echo "  python-dev   Run Inngest dev server"

inngest-dev:
	npx inngest-cli@latest dev -u $(INNGEST_URL) --no-discovery

python-dev:
	uv run uvicorn main:app --reload
