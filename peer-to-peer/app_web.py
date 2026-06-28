#!/usr/bin/env python3
"""
Multi-Agent Orchestration Web App with Flask + HTML UI

Supports:
- Multiple LLM backends (Ollama, OpenAI, Anthropic, etc.)
- Hierarchical agent organization (super_boss -> boss -> workers)
- Real-time message streaming via SSE
- Agent state persistence
- Configuration via JSON

Usage:
    python app_web.py --config config.json
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import requests

# Import all the classes from the original app.py
# (ModelType, AgentRole, ModelConfig, AgentConfig, AppConfig, LLMBackend, etc.)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Models (same as original)
# ============================================================================

class ModelType(str, Enum):
    """Supported model types"""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class AgentRole(str, Enum):
    """Agent roles in hierarchy"""
    SUPER_BOSS = "super_boss"
    BOSS = "boss"
    WORKER = "worker"


@dataclass
class ModelConfig:
    """Model configuration"""
    type: str
    name: str
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class AgentConfig:
    """Agent configuration"""
    id: str
    name: str
    role: str
    description: str
    model: ModelConfig
    parent_id: Optional[str] = None
    system_prompt: Optional[str] = None
    tools: List[str] = None

    def __post_init__(self):
        if self.tools is None:
            self.tools = []
        if isinstance(self.model, dict):
            self.model = ModelConfig.from_dict(self.model)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class AppConfig:
    """Application configuration"""
    app_name: str = "Multi-Agent Orchestrator"
    agents: List[AgentConfig] = None
    default_model: ModelConfig = None
    max_message_history: int = 100
    enable_persistence: bool = True
    persistence_dir: str = ".agent_state"

    def __post_init__(self):
        if self.agents is None:
            self.agents = []
        if isinstance(self.default_model, dict):
            self.default_model = ModelConfig.from_dict(self.default_model)

    @classmethod
    def from_file(cls, config_path: str) -> "AppConfig":
        with open(config_path, "r") as f:
            data = json.load(f)
        
        agents = [AgentConfig.from_dict(agent_data) for agent_data in data.get("agents", [])]
        default_model = ModelConfig.from_dict(data["default_model"]) if "default_model" in data else None
        
        return cls(
            app_name=data.get("app_name", "Multi-Agent Orchestrator"),
            agents=agents,
            default_model=default_model,
            max_message_history=data.get("max_message_history", 100),
            enable_persistence=data.get("enable_persistence", True),
            persistence_dir=data.get("persistence_dir", ".agent_state"),
        )


# ============================================================================
# LLM Backends (same as original)
# ============================================================================

class LLMBackend:
    def __init__(self, config: ModelConfig):
        self.config = config

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        raise NotImplementedError

    def stream(self, prompt: str, system_prompt: Optional[str] = None):
        raise NotImplementedError


class OllamaBackend(LLMBackend):
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.endpoint = config.endpoint or "http://localhost:11434"

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = requests.post(
                f"{self.endpoint}/api/chat",
                json={
                    "model": self.config.name,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": self.config.temperature,
                        "num_predict": self.config.max_tokens,
                    },
                },
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            return response.json()["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return f"Error: {str(e)}"

    def stream(self, prompt: str, system_prompt: Optional[str] = None):
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = requests.post(
                f"{self.endpoint}/api/chat",
                json={
                    "model": self.config.name,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": self.config.temperature,
                        "num_predict": self.config.max_tokens,
                    },
                },
                timeout=self.config.timeout,
                stream=True,
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if "message" in data:
                        yield data["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            yield f"Error: {str(e)}"


def get_backend(config: ModelConfig) -> LLMBackend:
    if config.type == ModelType.OLLAMA:
        return OllamaBackend(config)
    else:
        raise ValueError(f"Unknown model type: {config.type}")


# ============================================================================
# Agent Management (same as original)
# ============================================================================

class Agent:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.backend = get_backend(config.model)
        self.message_history: List[Dict[str, str]] = []

    def chat(self, message: str) -> str:
        self.message_history.append({"role": "user", "content": message})
        context = self._build_context()
        response = self.backend.generate(prompt=message, system_prompt=self.config.system_prompt or context)
        self.message_history.append({"role": "assistant", "content": response})
        return response

    def stream_chat(self, message: str):
        self.message_history.append({"role": "user", "content": message})
        context = self._build_context()
        
        full_response = ""
        for chunk in self.backend.stream(prompt=message, system_prompt=self.config.system_prompt or context):
            full_response += chunk
            yield chunk
        
        self.message_history.append({"role": "assistant", "content": full_response})

    def _build_context(self) -> str:
        context = f"You are {self.config.name}, a {self.config.role} agent.\n"
        context += f"Description: {self.config.description}\n"
        if self.config.parent_id:
            context += f"You report to: {self.config.parent_id}\n"
        if self.config.tools:
            context += f"Available tools: {', '.join(self.config.tools)}\n"
        return context

    def clear_history(self):
        self.message_history = []

    def get_history(self) -> List[Dict[str, str]]:
        return self.message_history


class AgentOrchestrator:
    def __init__(self, config: AppConfig):
        self.config = config
        self.agents: Dict[str, Agent] = {}
        self.hierarchy: Dict[str, List[str]] = {}
        
        for agent_config in config.agents:
            self.agents[agent_config.id] = Agent(agent_config)
            
            if agent_config.parent_id:
                if agent_config.parent_id not in self.hierarchy:
                    self.hierarchy[agent_config.parent_id] = []
                self.hierarchy[agent_config.parent_id].append(agent_config.id)

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self.agents.get(agent_id)

    def get_hierarchy_tree(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        if agent_id is None:
            for agent in self.agents.values():
                if agent.config.role == AgentRole.SUPER_BOSS:
                    agent_id = agent.config.id
                    break
        
        if agent_id is None:
            return {}
        
        agent = self.agents[agent_id]
        tree = {
            "id": agent.config.id,
            "name": agent.config.name,
            "role": agent.config.role,
            "children": [],
        }
        
        if agent_id in self.hierarchy:
            for child_id in self.hierarchy[agent_id]:
                tree["children"].append(self.get_hierarchy_tree(child_id))
        
        return tree


# ============================================================================
# Flask Web App
# ============================================================================

app = Flask(__name__)
orchestrator = None


@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template('index.html')


@app.route('/api/agents', methods=['GET'])
def get_agents():
    """Get list of all agents"""
    agents_data = []
    for agent_id, agent in orchestrator.agents.items():
        agents_data.append({
            'id': agent.config.id,
            'name': agent.config.name,
            'role': agent.config.role,
            'description': agent.config.description,
            'model': agent.config.model.name,
            'parent_id': agent.config.parent_id,
        })
    return jsonify(agents_data)


@app.route('/api/agent/<agent_id>', methods=['GET'])
def get_agent_info(agent_id):
    """Get detailed info about an agent"""
    agent = orchestrator.get_agent(agent_id)
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    return jsonify({
        'id': agent.config.id,
        'name': agent.config.name,
        'role': agent.config.role,
        'description': agent.config.description,
        'model': agent.config.model.name,
        'parent_id': agent.config.parent_id,
        'tools': agent.config.tools,
        'message_count': len(agent.message_history),
    })


@app.route('/api/agent/<agent_id>/history', methods=['GET'])
def get_agent_history(agent_id):
    """Get message history for an agent"""
    agent = orchestrator.get_agent(agent_id)
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    return jsonify(agent.get_history())


@app.route('/api/agent/<agent_id>/chat', methods=['POST'])
def chat_with_agent(agent_id):
    """Send message to agent (non-streaming)"""
    agent = orchestrator.get_agent(agent_id)
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    data = request.json
    message = data.get('message', '')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    response = agent.chat(message)
    return jsonify({'response': response})


@app.route('/api/agent/<agent_id>/stream', methods=['POST'])
def stream_chat_with_agent(agent_id):
    """Stream response from agent"""
    agent = orchestrator.get_agent(agent_id)
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    data = request.json
    message = data.get('message', '')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    def generate():
        for chunk in agent.stream_chat(message):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/api/agent/<agent_id>/clear', methods=['POST'])
def clear_agent_history(agent_id):
    """Clear agent message history"""
    agent = orchestrator.get_agent(agent_id)
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    agent.clear_history()
    return jsonify({'success': True})


@app.route('/api/hierarchy', methods=['GET'])
def get_hierarchy():
    """Get organization hierarchy tree"""
    tree = orchestrator.get_hierarchy_tree()
    return jsonify(tree)


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get overall statistics"""
    total_agents = len(orchestrator.agents)
    total_messages = sum(len(agent.message_history) for agent in orchestrator.agents.values())
    
    role_counts = {}
    for agent in orchestrator.agents.values():
        role = agent.config.role
        role_counts[role] = role_counts.get(role, 0) + 1
    
    return jsonify({
        'total_agents': total_agents,
        'total_messages': total_messages,
        'role_counts': role_counts,
        'app_name': orchestrator.config.app_name,
    })


@app.route('/api/agent/<agent_id>/prompt', methods=['GET'])
def get_agent_prompt(agent_id):
    """Get agent's system prompt"""
    agent = orchestrator.get_agent(agent_id)
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    return jsonify({
        'system_prompt': agent.config.system_prompt or '',
        'description': agent.config.description,
    })


@app.route('/api/agent/<agent_id>/prompt', methods=['PUT'])
def update_agent_prompt(agent_id):
    """Update agent's system prompt"""
    agent = orchestrator.get_agent(agent_id)
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    data = request.json
    new_prompt = data.get('system_prompt', '')
    
    # Update the agent's system prompt
    agent.config.system_prompt = new_prompt
    
    # Optionally update description
    if 'description' in data:
        agent.config.description = data['description']
    
    return jsonify({
        'success': True,
        'system_prompt': agent.config.system_prompt,
        'description': agent.config.description,
    })


@app.route('/api/conversation/start', methods=['POST'])
def start_conversation():
    """Start a conversation between two agents"""
    data = request.json
    agent1_id = data.get('agent1_id')
    agent2_id = data.get('agent2_id')
    initial_message = data.get('initial_message', 'Hello!')
    max_turns = data.get('max_turns', 5)
    
    if not agent1_id or not agent2_id:
        return jsonify({'error': 'Both agent IDs are required'}), 400
    
    agent1 = orchestrator.get_agent(agent1_id)
    agent2 = orchestrator.get_agent(agent2_id)
    
    if not agent1 or not agent2:
        return jsonify({'error': 'One or both agents not found'}), 404
    
    def generate():
        """Generate conversation stream"""
        current_message = initial_message
        current_agent = agent1
        other_agent = agent2
        
        for turn in range(max_turns):
            # Send message from current agent's perspective
            agent_name = current_agent.config.name
            other_name = other_agent.config.name
            
            # Yield turn start
            yield f"data: {json.dumps({'type': 'turn_start', 'turn': turn + 1, 'speaker': agent_name, 'listener': other_name})}\n\n"
            
            # Get response from current agent
            full_response = ""
            for chunk in other_agent.stream_chat(f"{agent_name} says: {current_message}"):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'speaker': other_name, 'chunk': chunk})}\n\n"
            
            # Yield turn end
            yield f"data: {json.dumps({'type': 'turn_end', 'speaker': other_name, 'message': full_response})}\n\n"
            
            # Swap agents for next turn
            current_message = full_response
            current_agent, other_agent = other_agent, current_agent
        
        # Conversation done
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/api/conversation/group', methods=['POST'])
def start_group_conversation():
    """Start a group conversation with multiple agents"""
    data = request.json
    agent_ids = data.get('agent_ids', [])
    initial_message = data.get('initial_message', 'Hello everyone!')
    max_turns = data.get('max_turns', 10)
    
    if len(agent_ids) < 2:
        return jsonify({'error': 'At least 2 agents required'}), 400
    
    agents = []
    for agent_id in agent_ids:
        agent = orchestrator.get_agent(agent_id)
        if not agent:
            return jsonify({'error': f'Agent {agent_id} not found'}), 404
        agents.append(agent)
    
    def generate():
        """Generate group conversation stream"""
        current_message = initial_message
        current_speaker = "User"
        
        for turn in range(max_turns):
            # Round-robin through agents
            current_agent = agents[turn % len(agents)]
            agent_name = current_agent.config.name
            
            # Yield turn start
            yield f"data: {json.dumps({'type': 'turn_start', 'turn': turn + 1, 'speaker': agent_name, 'previous_speaker': current_speaker})}\n\n"
            
            # Build context with previous speaker
            context_message = f"{current_speaker} says: {current_message}"
            
            # Get response from current agent
            full_response = ""
            for chunk in current_agent.stream_chat(context_message):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'speaker': agent_name, 'chunk': chunk})}\n\n"
            
            # Yield turn end
            yield f"data: {json.dumps({'type': 'turn_end', 'speaker': agent_name, 'message': full_response})}\n\n"
            
            # Update for next turn
            current_message = full_response
            current_speaker = agent_name
        
        # Conversation done
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')


def main():
    """Main entry point"""
    global orchestrator
    
    # Load configuration
    config_path = "config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    if not os.path.exists(config_path):
        print(f"Configuration file not found: {config_path}")
        sys.exit(1)
    
    try:
        config = AppConfig.from_file(config_path)
        orchestrator = AgentOrchestrator(config)
        print(f"Loaded {len(orchestrator.agents)} agents from {config_path}")
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)
    
    # Run Flask app
    print("Starting Multi-Agent Orchestrator Web App...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, host='0.0.0.0', port=5000)


if __name__ == "__main__":
    main()
