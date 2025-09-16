# Makefile

# PRISMA
migrate-dev:
	uv run prisma migrate dev
	uv run prisma generate

migrate-prod:
	uv run prisma migrate deploy
	uv run prisma generate

db-seed:
	uv run prisma db seed

studio: 
	uv run prisma studio

# DEV
dev:
	uv run fastapi dev main.py