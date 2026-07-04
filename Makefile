.PHONY: validate test up down logs holochain
validate:
	python scripts/validate_runtime.py

test:
	cd services/api && PYTHONPATH=. pytest -q

up:
	docker compose --env-file .env.local up --build -d

down:
	docker compose --env-file .env.local down

logs:
	docker compose logs -f --tail=200

holochain:
	docker compose --profile holochain --env-file .env.local up --build -d
