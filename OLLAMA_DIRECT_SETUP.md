# Using Ollama Directly (localhost:11434)

This guide shows how to configure the application to use Ollama directly at `localhost:11434` instead of going through a router/proxy.

## Quick Setup

### Option 1: Use Environment Variables (Recommended)

Create or update `/app/backend/.env`:

```env
# Use Ollama directly at localhost:11434
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Disable OpenAI-compatible API and Router
USE_OPENAI_API=false
USE_OLLAMA_ROUTER=false

# Optional: Explicitly set to None to ensure direct Ollama usage
OPENAI_API_BASE=
OLLAMA_ROUTER_BASE=
```

### Option 2: Use Ollama Python Library

If you want to use the [Ollama Python library](https://github.com/ollama/ollama-python) instead of HTTP requests, you can modify the code to use it directly.

**Install the library:**
```bash
pip install ollama
```

**Example usage:**
```python
from ollama import chat

response = chat(model='llama3.2', messages=[
    {
        'role': 'user',
        'content': 'Why is the sky blue?',
    },
])
print(response['message']['content'])
```

## Current Implementation

The application currently uses HTTP requests to Ollama's REST API at `http://localhost:11434/api/generate` and `http://localhost:11434/api/chat`.

### Default Configuration

- **OLLAMA_BASE_URL**: `http://localhost:11434` (default)
- **OLLAMA_MODEL**: `llama3.2` (default)
- **USE_OPENAI_API**: `false` (default - uses Ollama directly)
- **USE_OLLAMA_ROUTER**: `false` (default - uses Ollama directly)

## Verification

### 1. Check Ollama is Running

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Should return a list of available models
```

### 2. Test Ollama API

```bash
# Test generate endpoint
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Hello, how are you?",
  "stream": false
}'
```

### 3. Check Backend Logs

When the backend starts, it will use:
- `OLLAMA_BASE_URL` if `USE_OPENAI_API=false` and `USE_OLLAMA_ROUTER=false`
- Direct HTTP requests to `{OLLAMA_BASE_URL}/api/generate` or `{OLLAMA_BASE_URL}/api/chat`

## Troubleshooting

### Issue: Still connecting to 172.17.0.1:8080

**Solution:** Check your environment variables:
```bash
# In your backend directory
cat .env | grep -E "OLLAMA|OPENAI|ROUTER"

# Make sure these are set:
USE_OPENAI_API=false
USE_OLLAMA_ROUTER=false
OLLAMA_BASE_URL=http://localhost:11434
```

### Issue: Ollama not found

**Solution:**
1. Install Ollama: https://ollama.ai
2. Start Ollama: `ollama serve`
3. Pull a model: `ollama pull llama3.2`
4. Verify: `curl http://localhost:11434/api/tags`

### Issue: Connection refused

**Solution:**
- Make sure Ollama is running: `ollama serve`
- Check if port 11434 is available: `netstat -an | grep 11434`
- If using Docker, ensure Ollama is accessible from the container

## Using Ollama Python Library (Future Enhancement)

To use the Ollama Python library instead of HTTP requests:

1. **Install:**
   ```bash
   pip install ollama
   ```

2. **Update code** in `app/backend/main.py`:
   ```python
   from ollama import chat, AsyncClient

   # For async
   async def generate_ollama_response_stream(prompt: str):
       async for chunk in await AsyncClient().chat(
           model=OLLAMA_MODEL,
           messages=[{'role': 'user', 'content': prompt}],
           stream=True
       ):
           yield chunk['message']['content']
   ```

3. **Benefits:**
   - Cleaner API
   - Better error handling
   - Type hints support
   - Easier to maintain

## References

- [Ollama Python Library](https://github.com/ollama/ollama-python)
- [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Ollama Installation](https://ollama.ai)

