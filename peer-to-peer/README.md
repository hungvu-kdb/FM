# Multi-Agent Orchestrator

A comprehensive multi-agent orchestration system with hierarchical organization and support for multiple LLM backends (Ollama, OpenAI, Anthropic). Available in both Streamlit and Web UI versions.

## 🚀 Quick Start

### Web UI (Recommended for Production)

```bash
# Install dependencies
pip install -r requirements.txt

# Start server
python app_web.py

# Open browser
http://localhost:5000
```

### Streamlit UI (Recommended for Prototyping)

```bash
# Install dependencies
pip install -r requirements.txt

# Start Ollama (if using local LLM)
ollama serve

# Run app
streamlit run app.py
```

## ✨ Key Features

### Core Capabilities
- **🤖 Hierarchical Organization**: super_boss → boss → workers
- **🗣️ Agent-to-Agent Conversations**: Two-agent and group chat modes
- **⚙️ UI-Based Prompt Configuration**: Edit agent prompts in real-time
- **💬 Real-Time Streaming**: Stream responses from LLM backends
- **📊 Visualizations**: Hierarchy tree, statistics dashboard

### LLM Backend Support
- **Ollama** (local, free, private)
- **OpenAI** (GPT-4, GPT-3.5-turbo)
- **Anthropic** (Claude models)
- **Extensible** for custom backends

## 📁 Project Structure

```
peer-to-peer/
├── app.py                  # Streamlit application
├── app_web.py              # Flask web application
├── config.json             # Agent configuration
├── templates/
│   └── index.html          # Web UI (single-file)
├── requirements.txt        # All dependencies
├── README.md               # This file
└── WEB_ARCHITECTURE.md     # Technical architecture
```

## 🔧 Configuration

### Basic Agent Configuration

```json
{
  "app_name": "Multi-Agent Orchestrator",
  "agents": [
    {
      "id": "ceo",
      "name": "CEO Agent",
      "role": "super_boss",
      "description": "Strategic director",
      "model": {
        "type": "ollama",
        "name": "llama2",
        "endpoint": "http://localhost:11434",
        "temperature": 0.7,
        "max_tokens": 2048
      },
      "system_prompt": "You are a strategic CEO...",
      "tools": []
    }
  ]
}
```

### Agent Roles
- **super_boss**: Top-level coordinator
- **boss**: Middle management
- **worker**: Individual contributors

### LLM Backend Examples

**Ollama (Local)**
```json
{
  "type": "ollama",
  "name": "llama2",
  "endpoint": "http://localhost:11434"
}
```

**OpenAI**
```json
{
  "type": "openai",
  "name": "gpt-4",
  "api_key": "sk-..."
}
```

**Anthropic**
```json
{
  "type": "anthropic",
  "name": "claude-3-opus",
  "api_key": "sk-ant-..."
}
```

## 🎯 Use Cases

1. **Team Coordination** - CEO broadcasts strategy to managers
2. **Code Review** - Senior/junior developers collaborate
3. **Sprint Planning** - Team discusses priorities
4. **Architecture Design** - Backend/frontend coordination
5. **Problem Solving** - Escalate issues up hierarchy
6. **Knowledge Sharing** - Expert teaches team members

## 💡 Feature Highlights

### Agent-to-Agent Conversations

**Two-Agent Mode**: Watch two agents have a back-and-forth conversation
```
CEO ↔ Backend Manager
Topic: "Let's discuss the new feature"
Turns: 5
```

**Group Chat Mode**: Multiple agents discuss together
```
CEO + Backend Manager + Frontend Manager
Topic: "Sprint planning meeting"
Turns: 12
```

### Prompt Configuration

Edit agent prompts directly in the UI:
- Define agent behavior and personality
- Set expertise and responsibilities
- Configure communication style
- Test and iterate quickly

### Broadcast Messaging

Send messages to multiple agents:
- **Subordinates**: Message all reports
- **Superiors**: Escalate to management
- **Peers**: Coordinate with same-level agents

## 🆚 Streamlit vs Web UI

| Feature | Streamlit | Web UI |
|---------|-----------|--------|
| **Best For** | Prototyping, internal tools | Production, public apps |
| **Technology** | Python only | Flask + HTML/CSS/JS |
| **Deployment** | `streamlit run app.py` | `python app_web.py` |
| **Customization** | Limited | Full control |
| **Performance** | Good | Excellent |
| **Mobile Support** | Basic | Full responsive |
| **Production Ready** | No | Yes (with gunicorn) |
| **API Access** | No | Yes (REST API) |

### When to Use Each

**Use Streamlit for:**
- ✅ Rapid prototyping
- ✅ Internal tools
- ✅ Data science demos
- ✅ Python-only teams

**Use Web UI for:**
- ✅ Production deployment
- ✅ Public-facing apps
- ✅ Mobile users
- ✅ Custom branding
- ✅ API integrations

## 📊 Web UI Features

### REST API Endpoints

- `GET /api/agents` - List all agents
- `GET /api/agent/<id>` - Get agent details
- `POST /api/agent/<id>/stream` - Stream chat (SSE)
- `POST /api/agent/<id>/chat` - Send message
- `GET /api/hierarchy` - Get org tree
- `GET /api/stats` - Get statistics
- `POST /api/agent/<id>/clear` - Clear history
- `GET /api/agent/<id>/prompt` - Get prompt
- `PUT /api/agent/<id>/prompt` - Update prompt
- `POST /api/conversation/start` - Two-agent conversation
- `POST /api/conversation/group` - Group conversation

### UI Tabs

1. **💬 Chat** - Interactive chat with agents
2. **🗣️ Conversation** - Agent-to-agent conversations
3. **ℹ️ Info** - Agent details and configuration
4. **⚙️ Settings** - Edit agent prompts
5. **📊 Hierarchy** - Organization tree view
6. **📈 Stats** - System metrics

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- Ollama (for local LLM) or API keys (OpenAI/Anthropic)

### Step 1: Install Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Or install only what you need:
# For Web UI only:
pip install Flask requests python-dotenv

# For Streamlit UI only:
pip install streamlit requests python-dotenv
```

### Step 2: Configure LLM Backend

**Option A: Ollama (Local)**
```bash
# Install from https://ollama.ai
ollama pull llama2
ollama serve
```

**Option B: OpenAI**
```bash
export OPENAI_API_KEY="sk-..."
```

**Option C: Anthropic**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Step 3: Configure Agents

Edit `config.json` to define your agents and hierarchy.

### Step 4: Run

```bash
# Web UI
python app_web.py

# Streamlit UI
streamlit run app.py
```

## 🔒 Security Notes

⚠️ **Development Mode**: Current setup is for development only.

**For Production:**
- ✅ Use production WSGI server (gunicorn, uwsgi)
- ✅ Add authentication (JWT, OAuth)
- ✅ Enable HTTPS
- ✅ Sanitize all inputs
- ✅ Add rate limiting
- ✅ Use environment variables for secrets
- ✅ Add logging and monitoring

## 🚀 Performance Tips

1. **Model Selection**
   - Fast: llama2, mistral
   - Quality: gpt-4, claude-3

2. **Temperature Settings**
   - Deterministic: 0.0
   - Balanced: 0.5-0.7
   - Creative: 0.9-1.0

3. **Message History**
   - Set `max_message_history` appropriately
   - Clear history for long conversations

4. **Backend Choice**
   - Local: Ollama (free, private)
   - Cloud: OpenAI/Anthropic (better quality)

## 🐛 Troubleshooting

### Ollama Connection Error
```bash
# Make sure Ollama is running
ollama serve
```

### Port Already in Use
```python
# Change port in app_web.py
app.run(debug=True, port=5001)
```

### Model Not Found
```bash
# Pull the model
ollama pull llama2
```

### Streaming Not Working
- Use modern browser (Chrome, Firefox, Edge)
- Check browser console for errors
- Verify Flask is running

## 📚 API Reference

### AgentOrchestrator

```python
# Get agent
agent = orchestrator.get_agent("agent_id")

# Get agents by role
bosses = orchestrator.get_agents_by_role("boss")

# Get subordinates
subs = orchestrator.get_subordinates("agent_id")

# Get hierarchy tree
tree = orchestrator.get_hierarchy_tree()

# Broadcast message
results = orchestrator.broadcast_message(
    from_agent_id="agent_id",
    message="Hello",
    scope="subordinates"
)
```

### Agent

```python
# Chat
response = agent.chat("Hello")

# Stream chat
for chunk in agent.stream_chat("Hello"):
    print(chunk, end="")

# Get history
history = agent.get_history()

# Clear history
agent.clear_history()
```

## 🔧 Extending the System

### Add Custom LLM Backend

```python
class CustomBackend(LLMBackend):
    def generate(self, prompt, system_prompt=None):
        # Implementation
        pass
    
    def stream(self, prompt, system_prompt=None):
        # Implementation
        yield chunk
```

### Add Custom UI Tab

```html
<!-- In templates/index.html -->
<button class="tab" onclick="switchTab('custom')">Custom</button>
<div id="customTab" class="tab-content">
    <!-- Your content -->
</div>
```

### Add API Endpoint

```python
# In app_web.py
@app.route('/api/custom', methods=['POST'])
def custom_endpoint():
    return jsonify({...})
```

## 📈 Scaling for Production

```
Load Balancer (nginx)
    ↓
Multiple Flask Instances (gunicorn)
    ↓
Redis Cache (sessions & messages)
    ↓
PostgreSQL (persistent storage)
```

## 📄 License

MIT

## 🤝 Contributing

Contributions welcome! Please check WEB_ARCHITECTURE.md for technical details.

## 🆘 Support

1. Check WEB_ARCHITECTURE.md for technical details
2. Run `python test_web.py` to verify setup
3. Check browser/Flask console for errors
4. Verify Ollama/LLM backend is running

## 📖 Additional Documentation

See **WEB_ARCHITECTURE.md** for:
- Detailed system architecture
- Data flow diagrams
- Component details
- Extension points
- Scaling strategies