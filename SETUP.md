# DevAgent Setup Guide

## Prerequisites

1. **Docker and Docker Compose** - For running the application
2. **Ollama** - For AI features (optional but recommended)
   - Install from: https://ollama.ai
   - Download Llama 3.2 model: `ollama pull llama3.2`
   - Start Ollama: `ollama serve`

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Start all services
make up
# or
docker-compose up -d

# View logs
make logs
# or
docker-compose logs -f

# Stop services
make down
# or
docker-compose down
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8001
- MongoDB: localhost:27017

### Option 2: Local Development

#### Backend Setup

```bash
cd app/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your settings

# Run server
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

#### Frontend Setup

```bash
cd app/frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env
# Edit .env with your backend URL

# Run development server
npm run dev
```

#### MongoDB Setup

You can either:
1. Use Docker: `docker run -d -p 27017:27017 mongo:7`
2. Install MongoDB locally

## Environment Variables

### Backend (.env in app/backend/)

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=devagent
OLLAMA_BASE_URL=http://localhost:11434
```

### Frontend (.env in app/frontend/)

```env
VITE_BACKEND_URL=http://localhost:8001
```

## Verifying Ollama Setup

To verify Ollama is running and accessible:

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Test a simple request
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Hello, how are you?",
  "stream": false
}'
```

## Troubleshooting

### Ollama Connection Issues

If you see "Ollama is not running" errors:
1. Make sure Ollama is installed: `ollama --version`
2. Start Ollama: `ollama serve`
3. Verify the model is downloaded: `ollama list`
4. If using Docker, use `host.docker.internal:11434` instead of `localhost:11434`

### MongoDB Connection Issues

1. Check if MongoDB is running: `docker ps` or `mongosh`
2. Verify connection string in backend .env
3. Check MongoDB logs: `docker-compose logs mongodb`

### Port Conflicts

If ports 3000, 8001, or 27017 are already in use:
1. Stop conflicting services
2. Or modify ports in docker-compose.yml

## Development Tips

- Frontend hot-reloads automatically on file changes
- Backend auto-restarts on code changes (with --reload flag)
- Use browser DevTools to debug frontend
- Check backend logs for API debugging
- MongoDB data persists in Docker volume `mongodb_data`

## Production Deployment

For production:
1. Build optimized frontend: `cd app/frontend && npm run build`
2. Use production Docker images
3. Set proper environment variables
4. Configure reverse proxy (nginx, etc.)
5. Enable HTTPS
6. Set up proper MongoDB authentication

