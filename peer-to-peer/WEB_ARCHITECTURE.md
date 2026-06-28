# Web UI Architecture

Complete technical documentation for the Multi-Agent Orchestrator Web UI.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (Client)                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    index.html                              │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │  │
│  │  │   HTML      │  │     CSS      │  │   JavaScript    │  │  │
│  │  │  Structure  │  │   Styling    │  │   Logic         │  │  │
│  │  └─────────────┘  └──────────────┘  └─────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST API + SSE
┌────────────────────────────┴────────────────────────────────────┐
│                    Flask Server (app_web.py)                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      REST API Routes                       │  │
│  │  /api/agents          /api/agent/<id>/stream              │  │
│  │  /api/agent/<id>      /api/agent/<id>/prompt              │  │
│  │  /api/hierarchy       /api/conversation/start             │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  Agent Orchestrator                        │  │
│  │  - Manages multiple agents                                │  │
│  │  - Handles agent hierarchy                                │  │
│  │  - Routes messages to agents                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Agent Instances                         │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐               │  │
│  │  │ Agent 1  │  │ Agent 2  │  │ Agent 3  │               │  │
│  │  │ (Boss)   │  │ (Worker) │  │ (Worker) │               │  │
│  │  └──────────┘  └──────────┘  └──────────┘               │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ LLM API Calls
┌────────────────────────────┴────────────────────────────────────┐
│                      LLM Backend                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Ollama     │  │   OpenAI     │  │  Anthropic   │         │
│  │   (Local)    │  │   (Cloud)    │  │   (Cloud)    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend (index.html)

**Single-file architecture** containing:

#### HTML Structure
- Sidebar with agent list
- Main content area with tabs
- Chat interface
- Info panels
- Hierarchy visualization
- Statistics dashboard

#### CSS Styling
- Modern gradient design
- Responsive layout
- Smooth animations
- Role-based color coding
- Mobile-friendly

#### JavaScript Logic
- Agent selection
- Message sending/receiving
- Real-time streaming (SSE)
- Tab switching
- History management
- API communication

### 2. Backend (app_web.py)

**Flask REST API** with:

#### Core Components

```python
┌─────────────────────────────────────┐
│         Flask Application           │
├─────────────────────────────────────┤
│  Routes:                            │
│  - GET  /                           │
│  - GET  /api/agents                 │
│  - GET  /api/agent/<id>             │
│  - GET  /api/agent/<id>/history     │
│  - POST /api/agent/<id>/chat        │
│  - POST /api/agent/<id>/stream      │
│  - POST /api/agent/<id>/clear       │
│  - GET  /api/hierarchy              │
│  - GET  /api/stats                  │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│      Agent Orchestrator             │
├─────────────────────────────────────┤
│  - agents: Dict[str, Agent]         │
│  - hierarchy: Dict[str, List[str]]  │
│  - config: AppConfig                │
│                                     │
│  Methods:                           │
│  - get_agent()                      │
│  - get_hierarchy_tree()             │
│  - broadcast_message()              │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│           Agent                     │
├─────────────────────────────────────┤
│  - config: AgentConfig              │
│  - backend: LLMBackend              │
│  - message_history: List[Dict]      │
│                                     │
│  Methods:                           │
│  - chat()                           │
│  - stream_chat()                    │
│  - clear_history()                  │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│        LLM Backend                  │
├─────────────────────────────────────┤
│  - OllamaBackend                    │
│  - OpenAIBackend                    │
│  - AnthropicBackend                 │
│                                     │
│  Methods:                           │
│  - generate()                       │
│  - stream()                         │
└─────────────────────────────────────┘
```

## Data Flow

### 1. Page Load

```
Browser                 Flask                   Orchestrator
   │                      │                          │
   │──── GET / ──────────>│                          │
   │<─── index.html ──────│                          │
   │                      │                          │
   │── GET /api/agents ──>│                          │
   │                      │── get all agents ───────>│
   │                      │<─── agent list ──────────│
   │<─── JSON ────────────│                          │
   │                      │                          │
   │─ GET /api/hierarchy─>│                          │
   │                      │── get_hierarchy_tree() ─>│
   │                      │<─── tree structure ──────│
   │<─── JSON ────────────│                          │
```

### 2. Chat Message (Streaming)

```
Browser                 Flask                   Agent                LLM
   │                      │                       │                   │
   │─ POST /api/agent/    │                       │                   │
   │   <id>/stream ──────>│                       │                   │
   │  {message: "Hi"}     │                       │                   │
   │                      │── stream_chat() ─────>│                   │
   │                      │                       │── stream() ──────>│
   │                      │                       │                   │
   │<─ SSE: chunk 1 ──────│<──── yield chunk ─────│<─── chunk ────────│
   │<─ SSE: chunk 2 ──────│<──── yield chunk ─────│<─── chunk ────────│
   │<─ SSE: chunk 3 ──────│<──── yield chunk ─────│<─── chunk ────────│
   │<─ SSE: done ─────────│<──── yield done ──────│<─── done ─────────│
   │                      │                       │                   │
   │  [Display message]   │  [Save to history]    │                   │
```

### 3. Agent Selection

```
Browser                 Flask                   Orchestrator
   │                      │                          │
   │─ Click Agent ────────│                          │
   │                      │                          │
   │─ GET /api/agent/     │                          │
   │   <id> ─────────────>│                          │
   │                      │── get_agent(id) ────────>│
   │                      │<─── agent info ──────────│
   │<─── JSON ────────────│                          │
   │                      │                          │
   │─ GET /api/agent/     │                          │
   │   <id>/history ─────>│                          │
   │                      │── agent.get_history() ──>│
   │                      │<─── messages ────────────│
   │<─── JSON ────────────│                          │
   │                      │                          │
   │  [Display chat]      │                          │
```

## Configuration Flow

```
config.json
    │
    ├─> AppConfig
    │     │
    │     ├─> app_name
    │     ├─> max_message_history
    │     ├─> enable_persistence
    │     │
    │     └─> agents[]
    │           │
    │           ├─> AgentConfig
    │           │     │
    │           │     ├─> id
    │           │     ├─> name
    │           │     ├─> role
    │           │     ├─> description
    │           │     ├─> parent_id
    │           │     │
    │           │     └─> ModelConfig
    │           │           │
    │           │           ├─> type (ollama/openai/anthropic)
    │           │           ├─> name (model name)
    │           │           ├─> endpoint
    │           │           ├─> api_key
    │           │           ├─> temperature
    │           │           └─> max_tokens
    │           │
    │           └─> [More agents...]
    │
    └─> AgentOrchestrator
          │
          ├─> agents: {id: Agent}
          └─> hierarchy: {parent_id: [child_ids]}
```

## Technology Stack

### Frontend
- **HTML5**: Structure
- **CSS3**: Styling with gradients, animations, flexbox
- **Vanilla JavaScript**: No frameworks, pure JS
- **Fetch API**: HTTP requests
- **EventSource**: Server-Sent Events for streaming

### Backend
- **Python 3.8+**: Programming language
- **Flask 3.0**: Web framework
- **Requests**: HTTP client for LLM APIs
- **JSON**: Configuration and data exchange

### LLM Backends
- **Ollama**: Local LLM server
- **OpenAI API**: Cloud-based GPT models
- **Anthropic API**: Cloud-based Claude models

## Security Considerations

### Current Implementation (Development)
- ⚠️ No authentication
- ⚠️ No rate limiting
- ⚠️ Debug mode enabled
- ⚠️ CORS not configured
- ⚠️ No input sanitization

### Production Recommendations
- ✅ Add user authentication (JWT, OAuth)
- ✅ Implement rate limiting
- ✅ Use production WSGI server (gunicorn)
- ✅ Enable HTTPS
- ✅ Sanitize all inputs
- ✅ Add CORS headers
- ✅ Use environment variables for secrets
- ✅ Add logging and monitoring
- ✅ Implement session management
- ✅ Add request validation

## Performance Optimization

### Current Features
- ✅ Real-time streaming (reduces perceived latency)
- ✅ Single-page application (no page reloads)
- ✅ Efficient message history management
- ✅ Lazy loading of agent data

### Potential Improvements
- 📈 Add Redis for session caching
- 📈 Implement WebSocket for bidirectional communication
- 📈 Add message pagination
- 📈 Compress responses
- 📈 Add CDN for static assets
- 📈 Implement service workers for offline support
- 📈 Add database for persistent storage
- 📈 Implement connection pooling

## Scalability

### Current Limitations
- Single-threaded Flask development server
- In-memory message storage
- No load balancing
- No horizontal scaling

### Scaling Strategy
```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                         │
│                     (nginx/HAProxy)                      │
└────────────┬────────────────────────────┬────────────────┘
             │                            │
    ┌────────┴────────┐          ┌───────┴────────┐
    │  Flask App 1    │          │  Flask App 2   │
    │  (gunicorn)     │          │  (gunicorn)    │
    └────────┬────────┘          └───────┬────────┘
             │                            │
    ┌────────┴────────────────────────────┴────────┐
    │              Redis Cache                      │
    │         (Session & Message Store)             │
    └────────┬──────────────────────────────────────┘
             │
    ┌────────┴────────┐
    │   PostgreSQL    │
    │  (Persistent    │
    │    Storage)     │
    └─────────────────┘
```

## File Structure

```
.
├── app_web.py              # Flask backend server
├── config.json             # Agent configuration
├── templates/
│   └── index.html          # Single-file web UI
├── requirements_web.txt    # Python dependencies
├── start_web.bat           # Windows startup script
├── start_web.sh            # Linux/Mac startup script
├── WEB_UI_README.md        # User documentation
├── WEB_ARCHITECTURE.md     # This file
└── QUICK_START.md          # Quick start guide
```

## API Reference

### GET /api/agents
Returns list of all agents

**Response:**
```json
[
  {
    "id": "agent_id",
    "name": "Agent Name",
    "role": "worker",
    "description": "Description",
    "model": "llama2",
    "parent_id": "parent_id"
  }
]
```

### GET /api/agent/<agent_id>
Returns detailed agent information

**Response:**
```json
{
  "id": "agent_id",
  "name": "Agent Name",
  "role": "worker",
  "description": "Description",
  "model": "llama2",
  "parent_id": "parent_id",
  "tools": ["tool1", "tool2"],
  "message_count": 10
}
```

### POST /api/agent/<agent_id>/stream
Stream chat response using Server-Sent Events

**Request:**
```json
{
  "message": "Hello!"
}
```

**Response (SSE):**
```
data: {"chunk": "Hello"}
data: {"chunk": " there"}
data: {"chunk": "!"}
data: {"done": true}
```

### GET /api/hierarchy
Returns organization hierarchy tree

**Response:**
```json
{
  "id": "super_boss",
  "name": "CEO",
  "role": "super_boss",
  "children": [
    {
      "id": "boss_1",
      "name": "Manager",
      "role": "boss",
      "children": [...]
    }
  ]
}
```

## Extension Points

### Adding New Features

1. **New Tab**: Add to `index.html`
   ```html
   <button class="tab" onclick="switchTab('newtab')">New Tab</button>
   <div id="newtabTab" class="tab-content">...</div>
   ```

2. **New API Endpoint**: Add to `app_web.py`
   ```python
   @app.route('/api/new-endpoint', methods=['GET'])
   def new_endpoint():
       return jsonify({...})
   ```

3. **New Agent Type**: Extend `AgentRole` enum
   ```python
   class AgentRole(str, Enum):
       SUPER_BOSS = "super_boss"
       BOSS = "boss"
       WORKER = "worker"
       SPECIALIST = "specialist"  # New role
   ```

4. **New LLM Backend**: Extend `LLMBackend` class
   ```python
   class CustomBackend(LLMBackend):
       def generate(self, prompt, system_prompt=None):
           # Implementation
           pass
   ```

## Troubleshooting Guide

### Issue: Streaming not working
**Cause**: Browser doesn't support SSE or connection blocked
**Solution**: Use modern browser, check network tab

### Issue: Agent not responding
**Cause**: LLM backend not running or misconfigured
**Solution**: Check Ollama/API status, verify config.json

### Issue: Port already in use
**Cause**: Another service using port 5000
**Solution**: Change port in app_web.py or stop other service

### Issue: CORS errors
**Cause**: Accessing from different domain
**Solution**: Add flask-cors and configure CORS headers

## Future Enhancements

- [ ] WebSocket support for bidirectional communication
- [ ] Database integration for persistent storage
- [ ] User authentication and authorization
- [ ] Multi-user support with sessions
- [ ] Agent collaboration features
- [ ] File upload/download capabilities
- [ ] Voice input/output
- [ ] Mobile app (React Native/Flutter)
- [ ] Docker containerization
- [ ] Kubernetes deployment configs
- [ ] Monitoring and analytics dashboard
- [ ] Plugin system for extensions


## Component Architecture

### Frontend (templates/index.html)

Single-file HTML/CSS/JavaScript application with:

**HTML Structure:**
- Sidebar with agent list and controls
- Main content area with 6 tabs
- Chat interface with message history
- Info panels for agent details
- Hierarchy visualization
- Statistics dashboard
- Conversation interface (two-agent & group)
- Settings panel for prompt configuration

**CSS Styling:**
- Modern gradient design (purple/blue)
- Responsive layout (desktop, tablet, mobile)
- Smooth animations and transitions
- Role-based color coding (gold/blue/green)
- Mobile-friendly touch targets

**JavaScript Logic:**
- Agent selection and switching
- Real-time message streaming (SSE)
- Tab navigation
- API communication (Fetch API)
- History management
- Conversation orchestration
- Prompt editing

### Backend (app_web.py)

Flask REST API with:

**Core Classes:**
```python
AgentOrchestrator
├── agents: Dict[str, Agent]
├── hierarchy: Dict[str, List[str]]
└── config: AppConfig

Agent
├── config: AgentConfig
├── backend: LLMBackend
├── message_history: List[Dict]
└── Methods: chat(), stream_chat(), clear_history()

LLMBackend (Abstract)
├── OllamaBackend
├── OpenAIBackend
└── AnthropicBackend
```

**API Endpoints:**
- `GET /` - Serve index.html
- `GET /api/agents` - List all agents
- `GET /api/agent/<id>` - Get agent details
- `GET /api/agent/<id>/history` - Get message history
- `POST /api/agent/<id>/chat` - Send message (non-streaming)
- `POST /api/agent/<id>/stream` - Stream response (SSE)
- `POST /api/agent/<id>/clear` - Clear history
- `GET /api/agent/<id>/prompt` - Get agent prompt
- `PUT /api/agent/<id>/prompt` - Update agent prompt
- `POST /api/conversation/start` - Two-agent conversation
- `POST /api/conversation/group` - Group conversation
- `GET /api/hierarchy` - Get org tree
- `GET /api/stats` - Get statistics

## Data Flow

### Chat Message Flow (Streaming)

```
1. User types message in browser
2. JavaScript sends POST to /api/agent/<id>/stream
3. Flask receives request
4. AgentOrchestrator routes to Agent
5. Agent calls LLMBackend.stream()
6. LLM generates response chunks
7. Flask yields chunks via SSE
8. JavaScript receives chunks in real-time
9. Browser displays chunks as they arrive
10. Message saved to history
```

### Agent-to-Agent Conversation Flow

```
1. User selects agents and clicks "Start Conversation"
2. JavaScript sends POST to /api/conversation/start
3. Flask creates SSE stream
4. For each turn:
   a. Agent 1 generates response (streaming)
   b. Flask yields chunks to browser
   c. Browser displays Agent 1's message
   d. Agent 2 receives Agent 1's message
   e. Agent 2 generates response (streaming)
   f. Flask yields chunks to browser
   g. Browser displays Agent 2's message
5. Repeat until max turns reached
6. Flask sends "done" event
7. Browser shows "Conversation completed"
```

### Prompt Configuration Flow

```
1. User selects agent
2. JavaScript fetches GET /api/agent/<id>/prompt
3. Flask returns current prompt
4. Browser displays prompt in textarea
5. User edits prompt
6. User clicks "Save Changes"
7. JavaScript sends PUT /api/agent/<id>/prompt
8. Flask updates agent config in memory
9. Flask returns success response
10. Browser shows success message
11. Agent uses new prompt in future conversations
```

## Configuration System

### config.json Structure

```json
{
  "app_name": "Multi-Agent Orchestrator",
  "default_model": {
    "type": "ollama",
    "name": "llama2",
    "endpoint": "http://localhost:11434",
    "temperature": 0.7,
    "max_tokens": 2048,
    "timeout": 30
  },
  "agents": [
    {
      "id": "agent_001",
      "name": "Agent Name",
      "role": "super_boss|boss|worker",
      "description": "Agent description",
      "parent_id": "parent_agent_id",
      "model": {
        "type": "ollama|openai|anthropic",
        "name": "model_name",
        "endpoint": "http://...",
        "api_key": "optional_key",
        "temperature": 0.7,
        "max_tokens": 2048
      },
      "system_prompt": "Custom system prompt",
      "tools": ["tool1", "tool2"]
    }
  ],
  "max_message_history": 100,
  "enable_persistence": true,
  "persistence_dir": ".agent_state"
}
```

### Agent Roles

- **super_boss** (Level 0): Top-level coordinator, strategic decisions
- **boss** (Level 1): Middle management, team coordination
- **worker** (Level 2+): Individual contributors, task execution

### Model Configuration

**Ollama (Local LLM)**
```json
{
  "type": "ollama",
  "name": "llama2",
  "endpoint": "http://localhost:11434",
  "temperature": 0.7,
  "max_tokens": 2048
}
```

**OpenAI (Cloud)**
```json
{
  "type": "openai",
  "name": "gpt-4",
  "api_key": "sk-...",
  "temperature": 0.7,
  "max_tokens": 2048
}
```

**Anthropic (Cloud)**
```json
{
  "type": "anthropic",
  "name": "claude-3-opus-20240229",
  "api_key": "sk-ant-...",
  "temperature": 0.7,
  "max_tokens": 2048
}
```

## Technology Stack

### Frontend
- **HTML5**: Semantic structure
- **CSS3**: Gradients, animations, flexbox, grid
- **Vanilla JavaScript**: No frameworks, pure JS
- **Fetch API**: HTTP requests
- **EventSource**: Server-Sent Events for streaming
- **LocalStorage**: Client-side state (optional)

### Backend
- **Python 3.8+**: Programming language
- **Flask 3.0**: Lightweight web framework
- **Requests**: HTTP client for LLM APIs
- **JSON**: Configuration and data exchange

### LLM Backends
- **Ollama**: Local LLM server (free, private)
- **OpenAI API**: GPT-4, GPT-3.5-turbo (cloud)
- **Anthropic API**: Claude models (cloud)

## Security Considerations

### Current Implementation (Development)
- ⚠️ No authentication
- ⚠️ No rate limiting
- ⚠️ Debug mode enabled
- ⚠️ CORS not configured
- ⚠️ No input sanitization
- ⚠️ API keys in config files

### Production Recommendations

**Authentication & Authorization:**
```python
from flask_jwt_extended import JWTManager, jwt_required

app.config['JWT_SECRET_KEY'] = os.environ['JWT_SECRET']
jwt = JWTManager(app)

@app.route('/api/agent/<id>/chat', methods=['POST'])
@jwt_required()
def chat(id):
    # Protected endpoint
    pass
```

**Rate Limiting:**
```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=get_remote_address)

@app.route('/api/agent/<id>/stream')
@limiter.limit("10 per minute")
def stream_chat(id):
    pass
```

**Input Sanitization:**
```python
from bleach import clean

message = clean(request.json['message'], strip=True)
```

**HTTPS:**
```python
# Use gunicorn with SSL
gunicorn --certfile=cert.pem --keyfile=key.pem app_web:app
```

**Environment Variables:**
```python
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get('OPENAI_API_KEY')
```

## Performance Optimization

### Current Features
- ✅ Real-time streaming (reduces perceived latency)
- ✅ Single-page application (no page reloads)
- ✅ Efficient message history management
- ✅ Lazy loading of agent data
- ✅ SSE for efficient streaming

### Optimization Strategies

**1. Caching with Redis:**
```python
import redis

cache = redis.Redis(host='localhost', port=6379)

@app.route('/api/agents')
def get_agents():
    cached = cache.get('agents')
    if cached:
        return cached
    
    agents = orchestrator.get_all_agents()
    cache.setex('agents', 300, json.dumps(agents))
    return agents
```

**2. Database for Persistence:**
```python
from sqlalchemy import create_engine

engine = create_engine('postgresql://user:pass@localhost/db')

# Store message history in database
# Store agent configurations
# Store user sessions
```

**3. Message Pagination:**
```python
@app.route('/api/agent/<id>/history')
def get_history(id):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    history = agent.get_history()
    start = (page - 1) * per_page
    end = start + per_page
    
    return jsonify({
        'messages': history[start:end],
        'total': len(history),
        'page': page,
        'per_page': per_page
    })
```

**4. Compression:**
```python
from flask_compress import Compress

Compress(app)
```

## Scalability

### Current Limitations
- Single-threaded Flask development server
- In-memory message storage
- No load balancing
- No horizontal scaling
- No session persistence

### Production Scaling Strategy

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                         │
│                     (nginx/HAProxy)                      │
│                                                          │
│  - SSL termination                                       │
│  - Request routing                                       │
│  - Health checks                                         │
└────────────┬────────────────────────────┬────────────────┘
             │                            │
    ┌────────┴────────┐          ┌───────┴────────┐
    │  Flask App 1    │          │  Flask App 2   │
    │  (gunicorn)     │          │  (gunicorn)    │
    │  4 workers      │          │  4 workers     │
    └────────┬────────┘          └───────┬────────┘
             │                            │
    ┌────────┴────────────────────────────┴────────┐
    │              Redis Cache                      │
    │         (Session & Message Store)             │
    │                                               │
    │  - Session management                         │
    │  - Message queue                              │
    │  - Pub/Sub for real-time updates              │
    └────────┬──────────────────────────────────────┘
             │
    ┌────────┴────────┐
    │   PostgreSQL    │
    │  (Persistent    │
    │    Storage)     │
    │                 │
    │  - User data    │
    │  - Agent config │
    │  - Message logs │
    └─────────────────┘
```

### Deployment Configuration

**Gunicorn (Production WSGI Server):**
```bash
gunicorn -w 4 -b 0.0.0.0:5000 \
  --worker-class gevent \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  app_web:app
```

**Nginx (Reverse Proxy):**
```nginx
upstream flask_app {
    server 127.0.0.1:5000;
    server 127.0.0.1:5001;
}

server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass http://flask_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # SSE support
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

**Docker Compose:**
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://user:pass@db:5432/dbname
    depends_on:
      - redis
      - db

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

  db:
    image: postgres:14
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: dbname
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Extension Points

### 1. Adding New LLM Backend

```python
class CustomBackend(LLMBackend):
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.api_url = config.endpoint
        self.api_key = config.api_key
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        # Implement generation logic
        response = requests.post(
            self.api_url,
            json={
                'prompt': prompt,
                'system': system_prompt,
                'temperature': self.config.temperature,
                'max_tokens': self.config.max_tokens
            },
            headers={'Authorization': f'Bearer {self.api_key}'}
        )
        return response.json()['text']
    
    def stream(self, prompt: str, system_prompt: Optional[str] = None):
        # Implement streaming logic
        response = requests.post(
            self.api_url,
            json={'prompt': prompt, 'system': system_prompt, 'stream': True},
            headers={'Authorization': f'Bearer {self.api_key}'},
            stream=True
        )
        for line in response.iter_lines():
            if line:
                yield json.loads(line)['chunk']

# Register in get_backend()
def get_backend(config: ModelConfig) -> LLMBackend:
    if config.type == "custom":
        return CustomBackend(config)
    elif config.type == "ollama":
        return OllamaBackend(config)
    # ...
```

### 2. Adding New API Endpoint

```python
@app.route('/api/custom-feature', methods=['POST'])
def custom_feature():
    data = request.json
    
    # Your logic here
    result = process_custom_feature(data)
    
    return jsonify({
        'success': True,
        'result': result
    })
```

### 3. Adding New UI Tab

```html
<!-- In templates/index.html -->

<!-- Add tab button -->
<button class="tab" onclick="switchTab('custom')">
    🔧 Custom
</button>

<!-- Add tab content -->
<div id="customTab" class="tab-content" style="display: none;">
    <h2>Custom Feature</h2>
    <div id="customContent">
        <!-- Your custom UI here -->
    </div>
</div>

<script>
// Add JavaScript logic
async function loadCustomFeature() {
    const response = await fetch('/api/custom-feature');
    const data = await response.json();
    document.getElementById('customContent').innerHTML = renderCustom(data);
}
</script>
```

### 4. Adding New Agent Role

```python
class AgentRole(str, Enum):
    SUPER_BOSS = "super_boss"
    BOSS = "boss"
    WORKER = "worker"
    SPECIALIST = "specialist"  # New role
    CONSULTANT = "consultant"  # New role
```

## Troubleshooting

### Common Issues

**1. Streaming Not Working**
- **Cause**: Browser doesn't support SSE or connection blocked
- **Solution**: Use modern browser (Chrome, Firefox, Edge), check network tab

**2. Agent Not Responding**
- **Cause**: LLM backend not running or misconfigured
- **Solution**: Check Ollama status (`ollama serve`), verify config.json

**3. Port Already in Use**
- **Cause**: Another service using port 5000
- **Solution**: Change port in app_web.py or stop other service

**4. CORS Errors**
- **Cause**: Accessing from different domain
- **Solution**: Add flask-cors: `pip install flask-cors`

```python
from flask_cors import CORS
CORS(app)
```

**5. Slow Responses**
- **Cause**: Large model, slow network, or high temperature
- **Solution**: Use smaller model, reduce max_tokens, lower temperature

**6. Memory Issues**
- **Cause**: Large message history accumulation
- **Solution**: Set max_message_history, implement pagination

## Monitoring & Logging

### Application Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@app.route('/api/agent/<id>/chat', methods=['POST'])
def chat(id):
    logger.info(f"Chat request for agent {id}")
    try:
        # Process request
        logger.info(f"Chat completed for agent {id}")
    except Exception as e:
        logger.error(f"Chat error for agent {id}: {str(e)}")
        raise
```

### Performance Monitoring

```python
import time
from functools import wraps

def timing_decorator(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"{f.__name__} took {duration:.2f}s")
        return result
    return wrapper

@app.route('/api/agent/<id>/stream')
@timing_decorator
def stream_chat(id):
    # Implementation
    pass
```

### Health Check Endpoint

```python
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'agents': len(orchestrator.agents),
        'version': '1.0.0'
    })
```

## Testing

### Unit Tests

```python
import unittest
from app_web import app, orchestrator

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
    
    def test_get_agents(self):
        response = self.app.get('/api/agents')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
    
    def test_chat(self):
        response = self.app.post('/api/agent/ceo/chat',
            json={'message': 'Hello'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('response', data)

if __name__ == '__main__':
    unittest.main()
```

### Integration Tests

```python
def test_conversation_flow():
    # Test two-agent conversation
    response = client.post('/api/conversation/start', json={
        'agent1_id': 'ceo',
        'agent2_id': 'manager',
        'initial_message': 'Test conversation',
        'max_turns': 3
    })
    
    assert response.status_code == 200
    # Verify conversation completed
```

## Future Enhancements

### Planned Features
- [ ] WebSocket support for bidirectional communication
- [ ] Database integration (PostgreSQL/MongoDB)
- [ ] User authentication and authorization
- [ ] Multi-user support with sessions
- [ ] File upload/download capabilities
- [ ] Voice input/output
- [ ] Mobile app (React Native/Flutter)
- [ ] Docker containerization
- [ ] Kubernetes deployment configs
- [ ] Monitoring dashboard (Grafana)
- [ ] Plugin system for extensions
- [ ] Agent marketplace
- [ ] Conversation templates
- [ ] Export conversations (JSON/Markdown/PDF)
- [ ] Conversation replay/history
- [ ] Agent analytics and insights

### Potential Improvements
- [ ] GraphQL API option
- [ ] gRPC for internal communication
- [ ] Message queue (RabbitMQ/Kafka)
- [ ] Distributed tracing (Jaeger)
- [ ] Service mesh (Istio)
- [ ] API versioning
- [ ] Webhook support
- [ ] Scheduled tasks (Celery)
- [ ] Background jobs
- [ ] Email notifications

## Conclusion

This architecture provides a solid foundation for a production-ready multi-agent orchestration system. The modular design allows for easy extension and customization while maintaining clean separation of concerns.

For questions or contributions, please refer to the main README.md.