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

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = "llama3.2"


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


class ComponentGenerateRequest(BaseModel):
    description: str
    framework: str = "react"


class DesignSystemRequest(BaseModel):
    description: str
    style: str = "modern"


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

