# AI Provider Configuration

DevAgent supports multiple AI providers for code assistance, component generation, and design system creation.

## Supported Providers

### 1. Ollama (Default)

Ollama is the default provider. It runs locally and requires the Ollama service to be running.

**Configuration:**
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
USE_OPENAI_API=false
```

**Setup:**
1. Install Ollama: https://ollama.ai
2. Download model: `ollama pull llama3.2`
3. Start Ollama: `ollama serve`

### 2. OpenAI-Compatible API

Supports any OpenAI-compatible API endpoint, including:
- Open WebUI
- vLLM
- LocalAI
- Text Generation Inference (TGI)
- Ollama Router (OpenAI-compatible mode)
- Any service with OpenAI-compatible `/v1/chat/completions` endpoint

**Configuration:**
```env
OPENAI_API_BASE=http://localhost:8080/v1
OPENAI_API_MODEL=nemesis-coder
USE_OPENAI_API=true
```

### 3. Ollama Router Native API

Supports Ollama Router's native `/api/chat` endpoint with advanced features:
- `X-Task` header support for specialized tasks (e.g., "options" for options analysis)
- Auto-routing based on content
- Better integration with router-specific features

**Configuration:**
```env
OLLAMA_ROUTER_BASE=http://localhost:8080
OPENAI_API_MODEL=nemesis-coder  # Model to use
USE_OLLAMA_ROUTER=true
```

**Usage with X-Task header:**
When using Ollama Router, you can pass a `task` parameter in chat requests:
- `task: "options"` - For options analysis with nemesis-options-analyst model
- Auto-routing - Router can auto-detect tasks from content

**Example with Open WebUI:**
```env
OPENAI_API_BASE=http://localhost:8080/v1
OPENAI_API_MODEL=nemesis-coder
USE_OPENAI_API=true
```

**Example with vLLM:**
```env
OPENAI_API_BASE=http://localhost:8000/v1
OPENAI_API_MODEL=llama-2-7b-chat
USE_OPENAI_API=true
```

## Environment Variables

Add these to `/app/backend/.env`:

### Ollama Configuration
- `OLLAMA_BASE_URL` - Ollama API base URL (default: `http://localhost:11434`)
- `OLLAMA_MODEL` - Model name to use (default: `llama3.2`)

### OpenAI-Compatible API Configuration
- `OPENAI_API_BASE` - Base URL for OpenAI-compatible API (e.g., `http://localhost:8080/v1`)
- `OPENAI_API_MODEL` - Model name to use (e.g., `nemesis-coder`)
- `USE_OPENAI_API` - Set to `true` to use OpenAI-compatible API, `false` for Ollama (default: `false`)

### Ollama Router Native API Configuration
- `OLLAMA_ROUTER_BASE` - Base URL for Ollama Router (e.g., `http://localhost:8080`)
- `OPENAI_API_MODEL` - Model name to use (e.g., `nemesis-coder` or `nemesis-options-analyst`)
- `USE_OLLAMA_ROUTER` - Set to `true` to use Ollama Router native endpoint (default: `false`)

## Switching Providers

1. **To use Ollama (default):**
   ```env
   USE_OPENAI_API=false
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.2
   ```

2. **To use OpenAI-compatible API:**
   ```env
   USE_OPENAI_API=true
   OPENAI_API_BASE=http://localhost:8080/v1
   OPENAI_API_MODEL=nemesis-coder
   ```

3. **To use Ollama Router native endpoint (recommended for router features):**
   ```env
   USE_OLLAMA_ROUTER=true
   OLLAMA_ROUTER_BASE=http://localhost:8080
   OPENAI_API_MODEL=nemesis-coder
   ```

3. Restart the backend:
   ```bash
   docker-compose restart backend
   ```

## Testing Your Configuration

### Test Ollama:
```bash
curl http://localhost:11434/api/tags
```

### Test OpenAI-Compatible API:
```bash
curl --location 'http://localhost:8080/v1/chat/completions' \
--header 'Content-Type: application/json' \
--data '{
  "model": "nemesis-coder",
  "messages": [
    {
      "role": "user",
      "content": "Hello"
    }
  ],
  "stream": false
}'
```

## Features

Both providers support:
- ✅ Streaming chat responses
- ✅ Non-streaming chat
- ✅ Component generation
- ✅ Design system generation
- ✅ Context-aware responses

## Troubleshooting

### Ollama Connection Issues
- Ensure Ollama is running: `ollama serve`
- Check if model is downloaded: `ollama list`
- Verify connection: `curl http://localhost:11434/api/tags`

### OpenAI-Compatible API Issues
- Verify the API endpoint is accessible
- Check the model name matches your provider's model list
- Ensure the endpoint supports `/v1/chat/completions`
- Check CORS settings if accessing from browser

### Switching Between Providers
- Make sure only one provider is configured at a time
- Set `USE_OPENAI_API=true` for OpenAI-compatible APIs
- Set `USE_OPENAI_API=false` for Ollama
- Always restart the backend after changing configuration

