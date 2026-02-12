.PHONY: dev test

dev:
	uvicorn size_rec.app:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest -q

