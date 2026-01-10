from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
import httpx
import json
import asyncio
import threading
from datetime import datetime, timedelta

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

# Background task for weekly instrument updates
async def weekly_instrument_sync():
    """Background task to sync instruments weekly"""
    while True:
        try:
            # Wait 7 days (604800 seconds)
            await asyncio.sleep(604800)

            # Sync instruments
            db_instance = Database()
            result = await trading_service.sync_instruments_to_db(db_instance, "detailed")
            if result.get("success"):
                print(f"Instruments synced successfully: {result['data']['synced_count']} instruments")
            else:
                print(f"Instrument sync failed: {result.get('error')}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in weekly instrument sync: {e}")

# Global variable for sync task
sync_task = None

@app.on_event("startup")
async def startup_event():
    """Initialize instruments on startup"""
    global sync_task
    db_instance = Database()

    # Check if instruments exist, sync if needed
    instruments_exist = await db_instance.instruments_exist("detailed")
    if not instruments_exist:
        print("No instruments in database, performing initial sync...")
        try:
            result = await trading_service.sync_instruments_to_db(db_instance, "detailed")
            if result.get("success"):
                print(f"Initial instrument sync completed: {result['data']['synced_count']} instruments")
            else:
                print(f"Initial instrument sync failed: {result.get('error')}")
        except Exception as e:
            print(f"Error in initial instrument sync: {e}")
    else:
        metadata = await db_instance.get_instruments_metadata()
        if metadata:
            print(f"Instruments in database: {metadata.get('count', 0)} instruments, last updated: {metadata.get('last_updated', 'unknown')}")

    # Start weekly sync task
    sync_task = asyncio.create_task(weekly_instrument_sync())

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global sync_task
    if sync_task:
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass

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


class TradeHistoryRequest(BaseModel):
    access_token: str
    from_date: str
    to_date: str
    page_number: int = 0


class MarginCalculatorRequest(BaseModel):
    access_token: str
    security_id: str
    exchange_segment: str
    transaction_type: str
    quantity: int
    product_type: str
    price: float = 0
    trigger_price: float = 0


class KillSwitchRequest(BaseModel):
    token_id: str
    status: Optional[str] = None  # ACTIVATE or DEACTIVATE, None for get status


class LedgerRequest(BaseModel):
    access_token: str
    from_date: Optional[str] = None
    to_date: Optional[str] = None


class InstrumentListCSVRequest(BaseModel):
    format_type: str = "detailed"  # "compact" or "detailed"


class InstrumentListSegmentwiseRequest(BaseModel):
    exchange_segment: str  # e.g., "NSE_EQ", "BSE_EQ", "MCX_COM"
    access_token: Optional[str] = None  # Optional - not required for this endpoint


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
@app.post("/api/trading/auth/token")
async def trading_auth_token(request: TradingAuthRequest):
    """Authenticate with access token directly"""
    if not request.token_id:  # Using token_id field for access_token
        raise HTTPException(status_code=400, detail="Access token is required")

    # Validate token by getting user profile
    result = trading_service.get_user_profile(request.token_id)
    if not result.get("success"):
        error_detail = result.get("error", "Invalid access token")
        # Log the error for debugging
        import logging
        logging.error(f"Token validation failed: {error_detail}")
        raise HTTPException(status_code=401, detail=error_detail)

    return {
        "success": True,
        "access_token": request.token_id,
        "data": result.get("data")
    }


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


@app.post("/api/trading/instruments/csv")
async def get_instrument_list_csv(request: InstrumentListCSVRequest):
    """Get instrument list from CSV endpoints (compact or detailed) - checks database first"""
    if request.format_type not in ["compact", "detailed"]:
        raise HTTPException(status_code=400, detail="format_type must be 'compact' or 'detailed'")

    # Try database first
    instruments = await db.get_instruments(request.format_type)
    if instruments:
        return {
            "success": True,
            "data": {
                "instruments": instruments,
                "count": len(instruments),
                "format": request.format_type,
                "source": "database"
            }
        }

    # Fallback to CSV API if not in database
    result = trading_service.get_instrument_list_csv(request.format_type)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get instrument list"))
    return result


@app.post("/api/trading/instruments/sync")
async def sync_instruments(background_tasks: BackgroundTasks, format_type: str = "detailed"):
    """Manually trigger instrument sync from CSV to database"""
    if format_type not in ["compact", "detailed"]:
        raise HTTPException(status_code=400, detail="format_type must be 'compact' or 'detailed'")

    # Run sync in background
    async def sync_task():
        result = await trading_service.sync_instruments_to_db(db, format_type)
        if result.get("success"):
            print(f"Instruments synced: {result['data']['synced_count']} instruments")
        else:
            print(f"Sync failed: {result.get('error')}")

    background_tasks.add_task(sync_task)

    return {
        "success": True,
        "message": "Instrument sync started in background",
        "format": format_type
    }


@app.get("/api/trading/instruments/metadata")
async def get_instruments_metadata():
    """Get instruments metadata (last update time, count, etc.)"""
    metadata = await db.get_instruments_metadata()
    if not metadata:
        return {
            "success": False,
            "message": "No instruments metadata found"
        }
    return {
        "success": True,
        "data": metadata
    }


@app.post("/api/trading/instruments/segmentwise")
async def get_instrument_list_segmentwise(request: InstrumentListSegmentwiseRequest):
    """Get detailed instrument list for a particular exchange and segment (no authentication required)"""
    if not request.exchange_segment:
        raise HTTPException(status_code=400, detail="Exchange segment is required")
    result = trading_service.get_instrument_list_segmentwise(request.exchange_segment, request.access_token)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get instrument list"))
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


@app.post("/api/trading/trades")
async def get_trades(request: TradingAuthRequest):
    """Get all trades executed today"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.get_trades(request.token_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get trades"))
    return result


@app.post("/api/trading/trades/{order_id}")
async def get_trade_by_order_id(order_id: str, request: TradingAuthRequest):
    """Get trades by order ID"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.get_trade_by_order_id(request.token_id, order_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get trade"))
    return result


@app.post("/api/trading/trades/history")
async def get_trade_history(request: TradeHistoryRequest):
    """Get trade history for date range"""
    result = trading_service.get_trade_history(
        request.access_token,
        request.from_date,
        request.to_date,
        request.page_number
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get trade history"))
    return result


@app.post("/api/trading/margin/calculator")
async def calculate_margin(request: MarginCalculatorRequest):
    """Calculate margin for an order"""
    result = trading_service.calculate_margin(request.access_token, request.dict())
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to calculate margin"))
    return result


@app.post("/api/trading/killswitch")
async def manage_kill_switch(request: KillSwitchRequest):
    """Get or manage kill switch status"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")

    if request.status:
        # Manage kill switch
        result = trading_service.manage_kill_switch(request.token_id, request.status)
    else:
        # Get status
        result = trading_service.get_kill_switch_status(request.token_id)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to manage kill switch"))
    return result


@app.post("/api/trading/ledger")
async def get_ledger(request: LedgerRequest):
    """Get ledger report"""
    result = trading_service.get_ledger(
        request.access_token,
        request.from_date,
        request.to_date
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get ledger"))
    return result


# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.market_feeds: Dict[str, Any] = {}
        self.order_updates: Dict[str, Any] = {}
        self.full_depths: Dict[str, Any] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"Error sending message: {e}")
            self.disconnect(websocket)

manager = ConnectionManager()


@app.websocket("/ws/trading/market-feed/{access_token}")
async def market_feed_websocket(websocket: WebSocket, access_token: str):
    """WebSocket endpoint for real-time market feed using DhanHQ MarketFeed"""
    await manager.connect(websocket)
    market_feed = None
    feed_thread = None

    try:
        # Receive subscription request
        data = await websocket.receive_json()
        instruments = data.get("instruments", [])
        version = data.get("version", "v1")  # Default to v1 as per MarketFeed API

        # Validate instruments format
        if not instruments:
            await manager.send_personal_message({
                "type": "error",
                "message": "No instruments provided for subscription"
            }, websocket)
            return

        # Convert instruments to tuples if needed
        # Expected format: [(exchange_code, security_id, feed_request_code), ...]
        # exchange_code: 1=NSE, 2=BSE
        # security_id: Security ID (must be int)
        # feed_request_code: 1=Ticker, 2=Quote, 3=Full, 4=Market Depth, 5=OI, 6=Previous Day
        instrument_tuples = []
        for inst in instruments:
            if isinstance(inst, (list, tuple)) and len(inst) >= 2:
                # Ensure we have 3 elements (exchange_code, security_id, feed_request_code)
                exchange_code = int(inst[0])
                security_id = int(inst[1]) if isinstance(inst[1], (int, str)) else int(str(inst[1]))
                feed_code = int(inst[2]) if len(inst) >= 3 else 2  # Default to Quote mode
                instrument_tuples.append((exchange_code, security_id, feed_code))
            else:
                await manager.send_personal_message({
                    "type": "error",
                    "message": f"Invalid instrument format: {inst}. Expected [exchange_code, security_id, feed_request_code]"
                }, websocket)
                return

        print(f"Subscribing to {len(instrument_tuples)} instruments: {instrument_tuples}")

        # Create market feed instance
        try:
            market_feed = trading_service.create_market_feed(access_token, instrument_tuples, version)
            manager.market_feeds[access_token] = market_feed

            # Send connection success message
            await manager.send_personal_message({
                "type": "connected",
                "message": "Market feed connected successfully",
                "instruments_count": len(instrument_tuples)
            }, websocket)

            # Initialize and authorize market feed connection
            # MarketFeed requires async initialization
            async def initialize_market_feed():
                try:
                    # Authorize the connection (async method)
                    await market_feed.authorize()
                    # Connect to WebSocket (async method)
                    await market_feed.connect()
                    # Subscribe to instruments (async method)
                    await market_feed.subscribe_instruments()
                except Exception as e:
                    print(f"Market feed initialization error: {e}")
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"Failed to initialize market feed: {str(e)}"
                    }, websocket)
                    raise

            # Initialize market feed
            await initialize_market_feed()

            # Start market feed in background thread
            # MarketFeed.run_forever() is a blocking call that runs the event loop
            def run_market_feed():
                try:
                    # Run the market feed event loop (blocking)
                    market_feed.run_forever()
                except Exception as e:
                    print(f"Market feed error: {e}")

            feed_thread = threading.Thread(target=run_market_feed, daemon=True)
            feed_thread.start()

            # Wait a bit for connection to establish and data to start flowing
            await asyncio.sleep(2)

            # Send data to client as it arrives
            while True:
                try:
                    # get_data() returns data from the market feed queue
                    response = market_feed.get_data()
                    if response:
                        # MarketFeed returns data in various formats - normalize it
                        # It could be a dict, list, or nested structure
                        processed_data = response

                        # If it's a dict with nested data, extract it
                        if isinstance(response, dict):
                            # Check for common MarketFeed response structures
                            if 'data' in response:
                                processed_data = response['data']
                            elif 'instruments' in response:
                                processed_data = response['instruments']
                            elif 'quote' in response:
                                processed_data = response['quote']
                            elif 'ticker' in response:
                                processed_data = response['ticker']

                        # Ensure security_id is a string for consistent matching
                        if isinstance(processed_data, dict):
                            # Normalize security_id field
                            if 'security_id' in processed_data:
                                processed_data['security_id'] = str(processed_data['security_id'])
                            if 'securityId' in processed_data:
                                processed_data['securityId'] = str(processed_data['securityId'])
                            if 'SECURITY_ID' in processed_data:
                                processed_data['SECURITY_ID'] = str(processed_data['SECURITY_ID'])

                        # Process and send data to client
                        await manager.send_personal_message({
                            "type": "market_feed",
                            "data": processed_data
                        }, websocket)
                    await asyncio.sleep(0.05)  # Small delay to prevent CPU spinning
                except Exception as e:
                    print(f"Error processing market feed data: {e}")
                    await manager.send_personal_message({
                        "type": "error",
                        "message": str(e)
                    }, websocket)
                    break

        except (ImportError, AttributeError) as e:
            await manager.send_personal_message({
                "type": "error",
                "message": f"Market Feed not available: {str(e)}"
            }, websocket)
        except Exception as e:
            await manager.send_personal_message({
                "type": "error",
                "message": f"Failed to create market feed: {str(e)}"
            }, websocket)

    except WebSocketDisconnect:
        pass  # Client disconnected
    except Exception as e:
        await manager.send_personal_message({
            "type": "error",
            "message": f"WebSocket error: {str(e)}"
        }, websocket)
    finally:
        # Cleanup
        manager.disconnect(websocket)
        if market_feed and access_token in manager.market_feeds:
            try:
                # Disconnect the market feed
                if hasattr(market_feed, 'disconnect'):
                    market_feed.disconnect()
                elif hasattr(market_feed, 'close_connection'):
                    market_feed.close_connection()
            except Exception as e:
                print(f"Error disconnecting market feed: {e}")
            finally:
                del manager.market_feeds[access_token]


@app.websocket("/ws/trading/order-updates/{access_token}")
async def order_updates_websocket(websocket: WebSocket, access_token: str):
    """WebSocket endpoint for real-time order updates"""
    await manager.connect(websocket)
    try:
        # Create order update instance
        try:
            order_update = trading_service.create_order_update(access_token)
            manager.order_updates[access_token] = order_update

            # Callback for order updates
            def on_order_update(order_data: dict):
                asyncio.create_task(manager.send_personal_message({
                    "type": "order_update",
                    "data": order_data
                }, websocket))

            order_update.on_update = on_order_update

            # Start order update in background thread
            def run_order_update():
                while True:
                    try:
                        order_update.connect_to_dhan_websocket_sync()
                    except Exception as e:
                        print(f"Order update error: {e}")
                        import time
                        time.sleep(5)

            update_thread = threading.Thread(target=run_order_update, daemon=True)
            update_thread.start()

            # Keep connection alive
            while True:
                try:
                    await websocket.receive_text()
                except WebSocketDisconnect:
                    break
        except (ImportError, AttributeError) as e:
            await manager.send_personal_message({
                "type": "error",
                "message": f"Order Updates not available: {str(e)}"
            }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if access_token in manager.order_updates:
            del manager.order_updates[access_token]


@app.websocket("/ws/trading/full-depth/{access_token}")
async def full_depth_websocket(websocket: WebSocket, access_token: str):
    """WebSocket endpoint for 20-level market depth"""
    await manager.connect(websocket)
    try:
        # Receive subscription request
        data = await websocket.receive_json()
        instruments = data.get("instruments", [])

        # Create full depth instance
        try:
            full_depth = trading_service.create_full_depth(access_token, instruments)
            manager.full_depths[access_token] = full_depth

            # Start full depth in background thread
            def run_full_depth():
                try:
                    full_depth.run_forever()
                except Exception as e:
                    print(f"Full depth error: {e}")

            depth_thread = threading.Thread(target=run_full_depth, daemon=True)
            depth_thread.start()

            # Send data to client
            while True:
                try:
                    response = full_depth.get_data()
                    if response:
                        await manager.send_personal_message({
                            "type": "full_depth",
                            "data": response
                        }, websocket)
                    await asyncio.sleep(0.1)
                except Exception as e:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": str(e)
                    }, websocket)
                    break
        except (ImportError, AttributeError) as e:
            await manager.send_personal_message({
                "type": "error",
                "message": f"Full Depth not available: {str(e)}"
            }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if access_token in manager.full_depths:
            try:
                if hasattr(manager.full_depths[access_token], 'disconnect'):
                    manager.full_depths[access_token].disconnect()
            except:
                pass
            del manager.full_depths[access_token]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

