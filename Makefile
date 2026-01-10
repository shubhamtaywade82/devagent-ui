.PHONY: help install dev build up down logs clean

help:
	@echo "DevAgent - AI-Powered Development Editor"
	@echo ""
	@echo "Available commands:"
	@echo "  make install    - Install dependencies for frontend and backend"
	@echo "  make dev        - Start development servers (frontend + backend)"
	@echo "  make build      - Build production images"
	@echo "  make up         - Start all services with Docker Compose"
	@echo "  make down       - Stop all services"
	@echo "  make logs       - View logs from all services"
	@echo "  make clean      - Clean up containers and volumes"

install:
	@echo "Installing backend dependencies..."
	cd app/backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd app/frontend && npm install

dev:
	@echo "Starting development servers..."
	@echo "Backend: http://localhost:8001"
	@echo "Frontend: http://localhost:3000"
	docker-compose up

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	docker system prune -f

