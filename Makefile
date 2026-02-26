.PHONY: up-infra down-infra up-all down-all

up-infra:
	@echo "Starting infra..."
	docker compose up
down-infra:
	@echo "Removing infra..."
	docker compose down

up-all:
	@echo "Starting simulation..."
	docker compose --profile app up
down-all:
	@echo "Removing simulation..."
	docker compose --profile app down


