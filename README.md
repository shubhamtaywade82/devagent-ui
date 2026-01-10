# DevAgent - AI-Powered Development Editor

A web-based development editor inspired by Cursor AI, featuring AI-powered code assistance, UI component generation, and design system suggestions.

## Features

### 🎯 Core Capabilities
- **AI Code Assistant**: Get intelligent code suggestions powered by Ollama (Llama 3.2)
- **Smart Code Editor**: Multi-file editing with Monaco Editor and syntax highlighting
- **UI Component Generator**: Generate React components from text descriptions
- **Design System Generator**: Create complete design systems with AI
- **File Management**: Full file tree navigation with create/delete operations
- **Real-time Chat**: Interactive AI assistant sidebar for code help

### 🎨 User Interface
- **Dark Theme**: Professional cyber-physical aesthetic with violet/blue accents
- **Responsive Layout**: Three-panel layout (File Tree | Editor | AI Chat)
- **Modern Design**: Glassmorphism effects, smooth animations with Framer Motion
- **Monaco Editor**: VS Code-quality editing experience

## Tech Stack

- **Frontend**: React, Tailwind CSS, Monaco Editor, Framer Motion
- **Backend**: FastAPI, Python 3.11
- **Database**: MongoDB
- **AI**: Ollama (Llama 3.2 model)

## Getting Started

### Prerequisites
- **Ollama** (default): Installed and running on `localhost:11434` with Llama 3.2 model: `ollama pull llama3.2`
- **OR OpenAI-Compatible API**: Any service with `/v1/chat/completions` endpoint (e.g., Open WebUI, vLLM)

  See [AI_PROVIDERS.md](AI_PROVIDERS.md) for detailed configuration.

### Installation

The application is already set up and running in your environment:
- Frontend: Running on port 3000
- Backend: Running on port 8001
- MongoDB: Running on port 27017

### Using the Editor

1. **Create a Project**
   - Click "Create New Project" on the landing page
   - Enter project name and description
   - You'll be redirected to the editor

2. **Manage Files**
   - Click the "+" button in the file tree to create new files
   - Click on any file to open it in the editor
   - Edit your code with full syntax highlighting
   - Click "Save" to persist changes

3. **AI Code Assistant**
   - Use the chat sidebar on the right to ask coding questions
   - Get suggestions, explanations, and code snippets
   - Context-aware responses based on your project

4. **Generate UI Components**
   - Click "UI Generator" in the header
   - Describe the component you want
   - Get generated React code instantly
   - Copy or insert into your project

5. **Design System**
   - Switch to the "Design System" tab in UI Generator
   - Generate color palettes, typography, and spacing recommendations
   - Apply to your project's styling

## API Endpoints

### Projects
- `POST /api/projects` - Create new project
- `GET /api/projects` - List all projects
- `GET /api/projects/{id}` - Get project details
- `DELETE /api/projects/{id}` - Delete project

### Files
- `POST /api/files` - Save file content
- `GET /api/files/{project_id}` - Get all files in project
- `DELETE /api/files` - Delete file

### AI Features
- `POST /api/chat` - Chat with AI assistant
- `POST /api/chat/stream` - Stream AI responses
- `POST /api/generate/component` - Generate UI component
- `POST /api/generate/design-system` - Generate design system

## Important Notes

### Ollama Integration
The application requires Ollama to be running locally at `localhost:11434` with the `llama3.2` model installed. If Ollama is not running:
- Core functionality (projects, files, editor) will work perfectly
- AI features (chat, component generation) will show connection errors
- To enable AI features, start Ollama: `ollama serve`

### Environment Variables
- **Backend**: Uses `MONGO_URL`, `DB_NAME` from `/app/backend/.env`
  - **AI Provider**: Configure `OLLAMA_BASE_URL`, `OLLAMA_MODEL` for Ollama
  - **OR**: Configure `OPENAI_API_BASE`, `OPENAI_API_MODEL`, `USE_OPENAI_API=true` for OpenAI-compatible APIs
- **Frontend**: Uses `VITE_BACKEND_URL` from `/app/frontend/.env`

See [AI_PROVIDERS.md](AI_PROVIDERS.md) for AI provider configuration details.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  File Tree   │  │    Editor    │  │  AI Chat     │      │
│  │              │  │   (Monaco)   │  │  Sidebar     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓ API Calls
┌─────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Project & File Management  │  Ollama Integration    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
           ↓                                    ↓
    ┌──────────────┐                   ┌──────────────┐
    │   MongoDB    │                   │    Ollama    │
    │  (Projects)  │                   │  (llama3.2)  │
    └──────────────┘                   └──────────────┘
```

## Design Guidelines

The UI follows a "Cyber-Physical" design system:
- **Colors**: Dark zinc base (#09090b) with violet (#8b5cf6) and blue accents
- **Typography**: Manrope (headings), Inter (body), JetBrains Mono (code)
- **Effects**: Glassmorphism, subtle gradients, smooth animations
- **Layout**: Control Room grid (File Tree | Editor | AI Chat)

See `/app/design_guidelines.json` for complete design specifications.

## Testing

All core functionality has been tested:
- ✅ Project creation and management
- ✅ File CRUD operations
- ✅ Code editor functionality
- ✅ UI component generation (requires Ollama)
- ✅ AI chat assistant (requires Ollama)
- ✅ Design system generation (requires Ollama)

## Development

The application uses hot reload for both frontend and backend:
- Frontend changes reflect immediately
- Backend changes auto-restart the server
- Only restart supervisor when modifying `.env` or installing dependencies

## Future Enhancements

- **Real-time Collaboration**: Multi-user editing
- **Git Integration**: Commit, push, pull from UI
- **Terminal Integration**: In-browser terminal
- **Component Preview**: Live preview of generated components
- **Plugin System**: Extend functionality with plugins
- **Theme Customization**: Light/dark mode toggle
- **File Upload**: Drag-and-drop file upload
- **Code Snippets Library**: Reusable code templates

