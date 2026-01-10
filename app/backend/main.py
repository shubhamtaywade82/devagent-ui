from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
import httpx
import json

from database import Database
from models import Project, File, ChatMessage
from trading import trading_service

load_dotenv()

app = FastAPI(title="DevAgent API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db = Database()

# AI Provider configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
# OpenAI-compatible API (e.g., Open WebUI, vLLM, Ollama Router, etc.)
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", None)  # e.g., "http://localhost:8080/v1"
OPENAI_API_MODEL = os.getenv("OPENAI_API_MODEL", "nemesis-coder")
# Ollama Router native endpoint (alternative to OpenAI-compatible)
OLLAMA_ROUTER_BASE = os.getenv("OLLAMA_ROUTER_BASE", None)  # e.g., "http://localhost:8080"
# Use OpenAI-compatible API if configured, otherwise fall back to Ollama
USE_OPENAI_API = os.getenv("USE_OPENAI_API", "false").lower() == "true"
# Use Ollama Router native endpoint (supports X-Task header for specialized tasks)
USE_OLLAMA_ROUTER = os.getenv("USE_OLLAMA_ROUTER", "false").lower() == "true"


# Request/Response Models
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""


class FileCreate(BaseModel):
    project_id: str
    path: str
    content: str


class FileDelete(BaseModel):
    project_id: str
    path: str


class ChatRequest(BaseModel):
    message: str
    project_id: Optional[str] = None
    context: Optional[List[str]] = []
    task: Optional[str] = None  # e.g., "options" for options analysis with X-Task header


class ComponentGenerateRequest(BaseModel):
    description: str
    framework: str = "react"


class DesignSystemRequest(BaseModel):
    description: str
    style: str = "modern"


# Trading Request Models
class TradingAuthRequest(BaseModel):
    pin: Optional[str] = None
    totp: Optional[str] = None
    token_id: Optional[str] = None


class PlaceOrderRequest(BaseModel):
    access_token: str
    security_id: str
    exchange_segment: str
    transaction_type: str
    quantity: int
    order_type: str
    product_type: str
    price: float = 0
    trigger_price: float = 0
    disclosed_quantity: int = 0
    validity: str = "DAY"


class ModifyOrderRequest(BaseModel):
    access_token: str
    order_id: str
    order_type: Optional[str] = None
    leg_name: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    disclosed_quantity: Optional[int] = None
    validity: Optional[str] = None


class MarketQuoteRequest(BaseModel):
    access_token: str
    securities: dict


class OptionChainRequest(BaseModel):
    access_token: str
    under_security_id: int
    under_exchange_segment: str
    expiry: str


class HistoricalDataRequest(BaseModel):
    access_token: str
    security_id: int
    exchange_segment: str
    instrument_type: str
    from_date: str
    to_date: str
    interval: str = "daily"


# Health check
@app.get("/")
async def root():
    return {"status": "ok", "message": "DevAgent API is running"}


# Projects endpoints
@app.post("/api/projects", response_model=dict)
async def create_project(project: ProjectCreate):
    try:
        project_data = {
            "name": project.name,
            "description": project.description,
            "created_at": None,
            "updated_at": None
        }
        project_id = await db.create_project(project_data)
        # Fetch the created project to get properly serialized data
        created_project = await db.get_project(project_id)
        if not created_project:
            raise HTTPException(status_code=500, detail="Failed to retrieve created project")
        return created_project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects", response_model=List[dict])
async def list_projects():
    try:
        projects = await db.get_all_projects()
        return projects
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/{project_id}", response_model=dict)
async def get_project(project_id: str):
    try:
        project = await db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    try:
        result = await db.delete_project(project_id)
        if not result:
            raise HTTPException(status_code=404, detail="Project not found")
        # Also delete all files in the project
        await db.delete_files_by_project(project_id)
        return {"message": "Project deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Files endpoints
@app.post("/api/files", response_model=dict)
async def save_file(file: FileCreate):
    try:
        file_data = {
            "project_id": file.project_id,
            "path": file.path,
            "content": file.content,
            "updated_at": None
        }
        file_id = await db.save_file(file_data)
        # Fetch the saved file to get properly serialized data
        saved_file = await db.get_file(file.project_id, file.path)
        if not saved_file:
            raise HTTPException(status_code=500, detail="Failed to retrieve saved file")
        return saved_file
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files/{project_id}", response_model=List[dict])
async def get_files(project_id: str):
    try:
        files = await db.get_files_by_project(project_id)
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/files")
async def delete_file(file: FileDelete):
    try:
        result = await db.delete_file(file.project_id, file.path)
        if not result:
            raise HTTPException(status_code=404, detail="File not found")
        return {"message": "File deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# AI Chat endpoints
async def generate_openai_response_stream(prompt: str):
    """Generate streaming response from OpenAI-compatible API"""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            url = f"{OPENAI_API_BASE}/chat/completions"
            payload = {
                "model": OPENAI_API_MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": True
            }

            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    error_msg = f"⚠️ Error: {error_text.decode()}"
                    yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"
                    return

                async for line in response.aiter_lines():
                    if line:
                        if line.strip() == "data: [DONE]":
                            yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                            break
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])  # Remove "data: " prefix
                                if "choices" in data and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    content = delta.get("content", "")

                                    # Check for error patterns in content
                                    if content:
                                        error_patterns = [
                                            "[router error:",
                                            "router error:",
                                            "RuntimeError",
                                            "error:",
                                        ]
                                        is_error = any(pattern.lower() in content.lower() for pattern in error_patterns)

                                        if is_error:
                                            error_msg = f"⚠️ API Error: {content.strip()}"
                                            yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"
                                            return
                                        else:
                                            yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"

                                    # Check if finished
                                    finish_reason = data["choices"][0].get("finish_reason")
                                    if finish_reason:
                                        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                                        break
                            except json.JSONDecodeError:
                                continue
    except httpx.ConnectError:
        error_msg = f"⚠️ OpenAI-compatible API is not reachable at {OPENAI_API_BASE}"
        yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"


async def generate_ollama_router_response(prompt: str, task: Optional[str] = None, model: Optional[str] = None):
    """Generate non-streaming response from Ollama Router native endpoint"""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            url = f"{OLLAMA_ROUTER_BASE}/api/chat"
            payload = {
                "model": model or OPENAI_API_MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }

            headers = {}
            if task:
                headers["X-Task"] = task

            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            data = response.json()
            # Ollama Router native format
            if "message" in data:
                return {"response": data["message"]["content"]}
            elif "response" in data:
                return {"response": data["response"]}
            return {"response": ""}
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Ollama Router is not reachable at {OLLAMA_ROUTER_BASE}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def generate_openai_response(prompt: str):
    """Generate non-streaming response from OpenAI-compatible API"""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            url = f"{OPENAI_API_BASE}/chat/completions"
            payload = {
                "model": OPENAI_API_MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }

            response = await client.post(url, json=payload)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            data = response.json()
            # Extract content from OpenAI format
            if "choices" in data and len(data["choices"]) > 0:
                return {"response": data["choices"][0]["message"]["content"]}
            return {"response": ""}
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"OpenAI-compatible API is not reachable at {OPENAI_API_BASE}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def generate_ollama_response_stream(prompt: str):
    """Generate streaming response from Ollama"""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            url = f"{OLLAMA_BASE_URL}/api/generate"
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": True
            }

            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    error_msg = f"⚠️ Error: {error_text.decode()}"
                    yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"
                    return

                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield f"data: {json.dumps({'content': data['response'], 'done': data.get('done', False)})}\n\n"
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
    except httpx.ConnectError:
        # Send error through stream instead of raising exception
        error_msg = "⚠️ Ollama is not running. Please start Ollama: `ollama serve`"
        yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"
    except Exception as e:
        # Send error through stream instead of raising exception
        error_msg = f"❌ Error: {str(e)}"
        yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"


async def generate_ollama_response(prompt: str):
    """Generate non-streaming response from Ollama"""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            url = f"{OLLAMA_BASE_URL}/api/generate"
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }

            response = await client.post(url, json=payload)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Ollama is not running. Please start Ollama: ollama serve")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Non-streaming chat endpoint"""
    try:
        # Build context-aware prompt
        context_parts = []
        if request.context:
            context_parts.append("Context from project files:")
            context_parts.extend(request.context[:3])  # Limit context

        prompt = f"""You are an AI coding assistant. Help the user with their coding questions.

{f"Context: {' '.join(context_parts)}" if context_parts else ""}

User question: {request.message}

Provide a helpful, concise response with code examples when relevant."""

        if USE_OLLAMA_ROUTER and OLLAMA_ROUTER_BASE:
            # Use Ollama Router native endpoint with X-Task header support
            response = await generate_ollama_router_response(prompt, task=request.task)
            return {"response": response.get("response", "")}
        elif USE_OPENAI_API and OPENAI_API_BASE:
            response = await generate_openai_response(prompt)
            return {"response": response.get("response", "")}
        else:
            response = await generate_ollama_response(prompt)
            return {"response": response.get("response", "")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint"""
    try:
        # Build context-aware prompt
        context_parts = []
        if request.context:
            context_parts.append("Context from project files:")
            context_parts.extend(request.context[:3])

        prompt = f"""You are an AI coding assistant. Help the user with their coding questions.

{f"Context: {' '.join(context_parts)}" if context_parts else ""}

User question: {request.message}

Provide a helpful, concise response with code examples when relevant."""

        if USE_OLLAMA_ROUTER and OLLAMA_ROUTER_BASE:
            # Ollama Router native endpoint - use non-streaming and simulate streaming
            async def ollama_router_wrapper():
                try:
                    response = await generate_ollama_router_response(prompt, task=request.task)
                    content = response.get("response", "")
                    # Send content in chunks to simulate streaming
                    chunk_size = 10
                    for i in range(0, len(content), chunk_size):
                        chunk = content[i:i + chunk_size]
                        yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
                    yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                except Exception as e:
                    error_msg = f"⚠️ Error: {str(e)}"
                    yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"

            return StreamingResponse(
                ollama_router_wrapper(),
                media_type="text/event-stream"
            )
        elif USE_OPENAI_API and OPENAI_API_BASE:
            # OpenAI-compatible APIs often have issues with streaming (router errors)
            # Use non-streaming and send as a single chunk for better reliability
            async def non_streaming_wrapper():
                try:
                    response = await generate_openai_response(prompt)
                    content = response.get("response", "")
                    # Send content in chunks to simulate streaming
                    chunk_size = 10
                    for i in range(0, len(content), chunk_size):
                        chunk = content[i:i + chunk_size]
                        yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
                    yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                except Exception as e:
                    error_msg = f"⚠️ Error: {str(e)}"
                    yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"

            return StreamingResponse(
                non_streaming_wrapper(),
                media_type="text/event-stream"
            )
        else:
            return StreamingResponse(
                generate_ollama_response_stream(prompt),
                media_type="text/event-stream"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/component")
async def generate_component(request: ComponentGenerateRequest):
    """Generate UI component from description"""
    try:
        prompt = f"""Generate a React component based on this description: {request.description}

Requirements:
- Use modern React with functional components and hooks
- Include TypeScript types
- Use Tailwind CSS for styling
- Make it responsive and accessible
- Include proper prop types
- Add comments for clarity

Return ONLY the component code, no explanations."""

        if USE_OPENAI_API and OPENAI_API_BASE:
            response = await generate_openai_response(prompt)
            component_code = response.get("response", "")
        else:
            response = await generate_ollama_response(prompt)
            component_code = response.get("response", "")

        return {
            "component": component_code,
            "description": request.description,
            "framework": request.framework
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/design-system")
async def generate_design_system(request: DesignSystemRequest):
    """Generate design system from description"""
    try:
        prompt = f"""Generate a design system configuration based on this description: {request.description}

Include:
- Color palette (primary, secondary, accent colors)
- Typography scale (font families, sizes, weights)
- Spacing system (margins, paddings)
- Border radius values
- Shadow definitions
- Animation/transition settings

Return a JSON object with all these properties. Use a dark theme with violet/blue accents as default."""

        if USE_OPENAI_API and OPENAI_API_BASE:
            response = await generate_openai_response(prompt)
            design_system = response.get("response", "")
        else:
            response = await generate_ollama_response(prompt)
            design_system = response.get("response", "")

        # Try to extract JSON from response
        try:
            # Look for JSON in the response
            import re
            json_match = re.search(r'\{.*\}', design_system, re.DOTALL)
            if json_match:
                design_system = json.loads(json_match.group())
        except:
            pass

        return {
            "design_system": design_system,
            "description": request.description,
            "style": request.style
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Trading endpoints
@app.post("/api/trading/auth/pin")
async def trading_auth_pin(request: TradingAuthRequest):
    """Authenticate with PIN and TOTP"""
    if not request.pin or not request.totp:
        raise HTTPException(status_code=400, detail="PIN and TOTP are required")
    result = trading_service.authenticate_with_pin(request.pin, request.totp)
    if not result.get("success"):
        raise HTTPException(status_code=401, detail=result.get("error", "Authentication failed"))
    return result


@app.post("/api/trading/auth/oauth")
async def trading_auth_oauth():
    """Generate OAuth consent URL"""
    result = trading_service.authenticate_oauth(
        trading_service.app_id or "",
        trading_service.app_secret or ""
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "OAuth initialization failed"))
    return result


@app.post("/api/trading/auth/consume")
async def trading_auth_consume(request: TradingAuthRequest):
    """Consume token ID from OAuth redirect"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Token ID is required")
    result = trading_service.consume_token_id(
        request.token_id,
        trading_service.app_id or "",
        trading_service.app_secret or ""
    )
    if not result.get("success"):
        raise HTTPException(status_code=401, detail=result.get("error", "Token consumption failed"))
    return result


@app.post("/api/trading/profile")
async def trading_profile(request: TradingAuthRequest):
    """Get user profile"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.get_user_profile(request.token_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get profile"))
    return result


@app.post("/api/trading/orders/place")
async def place_order(request: PlaceOrderRequest):
    """Place a trading order"""
    result = trading_service.place_order(request.access_token, request.dict())
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to place order"))
    return result


@app.post("/api/trading/orders")
async def get_orders(request: TradingAuthRequest):
    """Get all orders"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.get_orders(request.token_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get orders"))
    return result


@app.get("/api/trading/orders/{order_id}")
async def get_order(order_id: str, access_token: str):
    """Get order by ID"""
    result = trading_service.get_order_by_id(access_token, order_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get order"))
    return result


@app.post("/api/trading/orders/{order_id}/cancel")
async def cancel_order(order_id: str, request: TradingAuthRequest):
    """Cancel an order"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.cancel_order(request.token_id, order_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to cancel order"))
    return result


@app.post("/api/trading/orders/{order_id}/modify")
async def modify_order(order_id: str, request: ModifyOrderRequest):
    """Modify an order"""
    result = trading_service.modify_order(request.access_token, order_id, request.dict())
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to modify order"))
    return result


@app.post("/api/trading/positions")
async def get_positions(request: TradingAuthRequest):
    """Get current positions"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.get_positions(request.token_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get positions"))
    return result


@app.post("/api/trading/holdings")
async def get_holdings(request: TradingAuthRequest):
    """Get current holdings"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.get_holdings(request.token_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get holdings"))
    return result


@app.post("/api/trading/funds")
async def get_funds(request: TradingAuthRequest):
    """Get fund limits and margin details"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.get_fund_limits(request.token_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get funds"))
    return result


@app.post("/api/trading/market/quote")
async def get_market_quote(request: MarketQuoteRequest):
    """Get market quote data"""
    result = trading_service.get_market_quote(request.access_token, request.securities)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get market quote"))
    return result


@app.post("/api/trading/market/option-chain")
async def get_option_chain(request: OptionChainRequest):
    """Get option chain data"""
    result = trading_service.get_option_chain(
        request.access_token,
        request.under_security_id,
        request.under_exchange_segment,
        request.expiry
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get option chain"))
    return result


@app.post("/api/trading/market/historical")
async def get_historical_data(request: HistoricalDataRequest):
    """Get historical data"""
    result = trading_service.get_historical_data(
        request.access_token,
        request.security_id,
        request.exchange_segment,
        request.instrument_type,
        request.from_date,
        request.to_date,
        request.interval
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get historical data"))
    return result


@app.post("/api/trading/securities")
async def get_securities(request: TradingAuthRequest):
    """Get security/instrument list"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.get_security_list(request.token_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get securities"))
    return result


@app.post("/api/trading/expiry-list")
async def get_expiry_list(request: OptionChainRequest):
    """Get expiry list for underlying"""
    result = trading_service.get_expiry_list(
        request.access_token,
        request.under_security_id,
        request.under_exchange_segment
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get expiry list"))
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

