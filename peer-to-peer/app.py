#!/usr/bin/env python3
"""
Multi-Agent Orchestration App with Streamlit UI

Supports:
- Multiple LLM backends (Ollama, OpenAI, Anthropic, etc.)
- Hierarchical agent organization (super_boss -> boss -> workers)
- Real-time message streaming
- Agent state persistence
- Configuration via JSON

Usage:
    streamlit run app.py --config config.json
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

import streamlit as st
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Models
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
    type: str  # ollama, openai, anthropic, custom
    name: str  # Model name (e.g., "llama2", "gpt-4")
    endpoint: Optional[str] = None  # API endpoint
    api_key: Optional[str] = None  # API key
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelConfig":
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class AgentConfig:
    """Agent configuration"""
    id: str
    name: str
    role: str  # super_boss, boss, worker
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
        """Create from dictionary"""
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
        """Load configuration from JSON file"""
        with open(config_path, "r") as f:
            data = json.load(f)
        
        # Parse agents
        agents = []
        for agent_data in data.get("agents", []):
            agents.append(AgentConfig.from_dict(agent_data))
        
        # Parse default model
        default_model = None
        if "default_model" in data:
            default_model = ModelConfig.from_dict(data["default_model"])
        
        return cls(
            app_name=data.get("app_name", "Multi-Agent Orchestrator"),
            agents=agents,
            default_model=default_model,
            max_message_history=data.get("max_message_history", 100),
            enable_persistence=data.get("enable_persistence", True),
            persistence_dir=data.get("persistence_dir", ".agent_state"),
        )


# ============================================================================
# LLM Backends
# ============================================================================

class LLMBackend:
    """Base class for LLM backends"""

    def __init__(self, config: ModelConfig):
        self.config = config

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate response from prompt"""
        raise NotImplementedError

    def stream(self, prompt: str, system_prompt: Optional[str] = None):
        """Stream response from prompt"""
        raise NotImplementedError


class OllamaBackend(LLMBackend):
    """Ollama backend"""

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.endpoint = config.endpoint or "http://localhost:11434"

    def get_available_models(self) -> List[str]:
        """Get list of available models in Ollama"""
        try:
            response = requests.get(
                f"{self.endpoint}/api/tags",
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            data = response.json()
            models = [model["name"] for model in data.get("models", [])]
            return models
        except Exception as e:
            logger.error(f"Error fetching Ollama models: {e}")
            return []

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model"""
        try:
            response = requests.post(
                f"{self.endpoint}/api/show",
                json={"name": model_name},
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching model info: {e}")
            return None

    def is_model_available(self, model_name: str) -> bool:
        """Check if a model is available in Ollama"""
        available_models = self.get_available_models()
        return model_name in available_models

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate response using Ollama"""
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
        """Stream response using Ollama"""
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


class OpenAIBackend(LLMBackend):
    """OpenAI backend"""

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate response using OpenAI"""
        try:
            import openai

            openai.api_key = self.api_key
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = openai.ChatCompletion.create(
                model=self.config.name,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return f"Error: {str(e)}"

    def stream(self, prompt: str, system_prompt: Optional[str] = None):
        """Stream response using OpenAI"""
        try:
            import openai

            openai.api_key = self.api_key
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = openai.ChatCompletion.create(
                model=self.config.name,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=True,
                timeout=self.config.timeout,
            )

            for chunk in response:
                if "choices" in chunk:
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]
        except Exception as e:
            logger.error(f"OpenAI stream error: {e}")
            yield f"Error: {str(e)}"


class AnthropicBackend(LLMBackend):
    """Anthropic backend"""

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate response using Anthropic"""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)
            message = client.messages.create(
                model=self.config.name,
                max_tokens=self.config.max_tokens,
                system=system_prompt or "",
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Anthropic error: {e}")
            return f"Error: {str(e)}"

    def stream(self, prompt: str, system_prompt: Optional[str] = None):
        """Stream response using Anthropic"""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)
            with client.messages.stream(
                model=self.config.name,
                max_tokens=self.config.max_tokens,
                system=system_prompt or "",
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Anthropic stream error: {e}")
            yield f"Error: {str(e)}"


def get_backend(config: ModelConfig) -> LLMBackend:
    """Get LLM backend based on configuration"""
    if config.type == ModelType.OLLAMA:
        return OllamaBackend(config)
    elif config.type == ModelType.OPENAI:
        return OpenAIBackend(config)
    elif config.type == ModelType.ANTHROPIC:
        return AnthropicBackend(config)
    else:
        raise ValueError(f"Unknown model type: {config.type}")


# ============================================================================
# Agent Management
# ============================================================================

class Agent:
    """Agent with LLM backend"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.backend = get_backend(config.model)
        self.message_history: List[Dict[str, str]] = []

    def chat(self, message: str) -> str:
        """Send message and get response"""
        self.message_history.append({"role": "user", "content": message})
        
        # Build context from history
        context = self._build_context()
        
        response = self.backend.generate(
            prompt=message,
            system_prompt=self.config.system_prompt or context,
        )
        
        self.message_history.append({"role": "assistant", "content": response})
        return response

    def stream_chat(self, message: str):
        """Stream response"""
        self.message_history.append({"role": "user", "content": message})
        
        context = self._build_context()
        
        for chunk in self.backend.stream(
            prompt=message,
            system_prompt=self.config.system_prompt or context,
        ):
            yield chunk

    def _build_context(self) -> str:
        """Build context from agent config"""
        context = f"You are {self.config.name}, a {self.config.role} agent.\n"
        context += f"Description: {self.config.description}\n"
        if self.config.parent_id:
            context += f"You report to: {self.config.parent_id}\n"
        if self.config.tools:
            context += f"Available tools: {', '.join(self.config.tools)}\n"
        return context

    def clear_history(self):
        """Clear message history"""
        self.message_history = []

    def get_history(self) -> List[Dict[str, str]]:
        """Get message history"""
        return self.message_history


class AgentOrchestrator:
    """Manages multiple agents and their interactions"""

    def __init__(self, config: AppConfig):
        self.config = config
        self.agents: Dict[str, Agent] = {}
        self.hierarchy: Dict[str, List[str]] = {}  # parent_id -> [child_ids]
        
        # Initialize agents
        for agent_config in config.agents:
            self.agents[agent_config.id] = Agent(agent_config)
            
            # Build hierarchy
            if agent_config.parent_id:
                if agent_config.parent_id not in self.hierarchy:
                    self.hierarchy[agent_config.parent_id] = []
                self.hierarchy[agent_config.parent_id].append(agent_config.id)

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)

    def get_agents_by_role(self, role: str) -> List[Agent]:
        """Get all agents with specific role"""
        return [
            agent for agent in self.agents.values()
            if agent.config.role == role
        ]

    def get_subordinates(self, agent_id: str) -> List[Agent]:
        """Get all subordinates of an agent"""
        subordinates = []
        if agent_id in self.hierarchy:
            for child_id in self.hierarchy[agent_id]:
                subordinates.append(self.agents[child_id])
                subordinates.extend(self.get_subordinates(child_id))
        return subordinates

    def get_hierarchy_tree(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get hierarchy tree starting from agent"""
        if agent_id is None:
            # Find super_boss
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

    def broadcast_message(
        self,
        from_agent_id: str,
        message: str,
        scope: str = "subordinates",  # subordinates, superiors, peers
    ) -> Dict[str, str]:
        """Broadcast message to multiple agents"""
        results = {}
        
        if scope == "subordinates":
            targets = self.get_subordinates(from_agent_id)
        elif scope == "superiors":
            targets = self._get_superiors(from_agent_id)
        elif scope == "peers":
            targets = self._get_peers(from_agent_id)
        else:
            targets = []
        
        for target in targets:
            response = target.chat(message)
            results[target.config.id] = response
        
        return results

    def _get_superiors(self, agent_id: str) -> List[Agent]:
        """Get all superiors of an agent"""
        superiors = []
        agent = self.agents[agent_id]
        
        if agent.config.parent_id:
            parent = self.agents.get(agent.config.parent_id)
            if parent:
                superiors.append(parent)
                superiors.extend(self._get_superiors(parent.config.id))
        
        return superiors

    def _get_peers(self, agent_id: str) -> List[Agent]:
        """Get peers of an agent (same parent)"""
        peers = []
        agent = self.agents[agent_id]
        
        if agent.config.parent_id:
            parent_id = agent.config.parent_id
            if parent_id in self.hierarchy:
                for child_id in self.hierarchy[parent_id]:
                    if child_id != agent_id:
                        peers.append(self.agents[child_id])
        
        return peers


# ============================================================================
# Streamlit UI
# ============================================================================

def load_config(config_path: str = "config.json") -> AppConfig:
    """Load configuration from file"""
    if not os.path.exists(config_path):
        st.error(f"Configuration file not found: {config_path}")
        st.stop()
    
    try:
        return AppConfig.from_file(config_path)
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
        st.stop()


def initialize_session_state(orchestrator: AgentOrchestrator):
    """Initialize Streamlit session state"""
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = orchestrator
    
    if "selected_agent" not in st.session_state:
        # Select first agent
        agent_ids = list(orchestrator.agents.keys())
        st.session_state.selected_agent = agent_ids[0] if agent_ids else None
    
    if "messages" not in st.session_state:
        st.session_state.messages = {}
    
    if "show_hierarchy" not in st.session_state:
        st.session_state.show_hierarchy = False


def render_sidebar(orchestrator: AgentOrchestrator):
    """Render sidebar with agent selection"""
    st.sidebar.title("🤖 Agents")
    
    # Agent selection
    agent_ids = list(orchestrator.agents.keys())
    agent_names = [
        f"{orchestrator.agents[aid].config.name} ({orchestrator.agents[aid].config.role})"
        for aid in agent_ids
    ]
    
    selected_idx = agent_ids.index(st.session_state.selected_agent) if st.session_state.selected_agent in agent_ids else 0
    selected_name = st.sidebar.selectbox(
        "Select Agent",
        agent_names,
        index=selected_idx,
    )
    st.session_state.selected_agent = agent_ids[agent_names.index(selected_name)]
    
    # Agent info
    agent = orchestrator.get_agent(st.session_state.selected_agent)
    if agent:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Agent Info")
        st.sidebar.write(f"**Name:** {agent.config.name}")
        st.sidebar.write(f"**Role:** {agent.config.role}")
        st.sidebar.write(f"**Model:** {agent.config.model.name}")
        st.sidebar.write(f"**Description:** {agent.config.description}")
        
        if agent.config.parent_id:
            parent = orchestrator.get_agent(agent.config.parent_id)
            if parent:
                st.sidebar.write(f"**Reports to:** {parent.config.name}")
        
        subordinates = orchestrator.get_subordinates(agent.config.id)
        if subordinates:
            st.sidebar.write(f"**Manages:** {len(subordinates)} agent(s)")
    
    # Hierarchy view
    st.sidebar.markdown("---")
    if st.sidebar.button("📊 View Hierarchy"):
        st.session_state.show_hierarchy = not st.session_state.show_hierarchy
    
    # Clear history
    if st.sidebar.button("🗑️ Clear History"):
        if agent:
            agent.clear_history()
        st.rerun()


def render_hierarchy(orchestrator: AgentOrchestrator):
    """Render organization hierarchy"""
    st.subheader("📊 Organization Hierarchy")
    
    tree = orchestrator.get_hierarchy_tree()
    
    def render_tree(node, level=0):
        indent = "  " * level
        role_emoji = {
            "super_boss": "👑",
            "boss": "💼",
            "worker": "👤",
        }
        emoji = role_emoji.get(node.get("role"), "")
        
        st.write(f"{indent}{emoji} **{node['name']}** ({node['role']})")
        
        for child in node.get("children", []):
            render_tree(child, level + 1)
    
    if tree:
        render_tree(tree)
    else:
        st.info("No agents configured")


def render_chat(orchestrator: AgentOrchestrator):
    """Render chat interface"""
    agent = orchestrator.get_agent(st.session_state.selected_agent)
    
    if not agent:
        st.error("No agent selected")
        return
    
    st.subheader(f"💬 Chat with {agent.config.name}")
    
    # Display message history
    if agent.config.id not in st.session_state.messages:
        st.session_state.messages[agent.config.id] = []
    
    messages = st.session_state.messages[agent.config.id]
    
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    # Input
    user_input = st.chat_input("Type your message...")
    
    if user_input:
        # Add user message
        messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
        
        # Get response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            
            try:
                for chunk in agent.stream_chat(user_input):
                    full_response += chunk
                    response_placeholder.write(full_response)
            except Exception as e:
                full_response = f"Error: {str(e)}"
                response_placeholder.error(full_response)
        
        # Add assistant message
        messages.append({"role": "assistant", "content": full_response})


def render_broadcast(orchestrator: AgentOrchestrator):
    """Render broadcast message interface"""
    st.subheader("📢 Broadcast Message")
    
    agent = orchestrator.get_agent(st.session_state.selected_agent)
    if not agent:
        st.error("No agent selected")
        return
    
    # Scope selection
    scope = st.selectbox(
        "Broadcast Scope",
        ["subordinates", "superiors", "peers"],
        help="Who to send the message to",
    )
    
    # Message input
    message = st.text_area("Message to broadcast")
    
    if st.button("Send Broadcast"):
        if not message:
            st.warning("Please enter a message")
            return
        
        with st.spinner("Broadcasting..."):
            results = orchestrator.broadcast_message(
                agent.config.id,
                message,
                scope=scope,
            )
        
        st.success(f"Broadcast sent to {len(results)} agent(s)")
        
        # Display results
        for agent_id, response in results.items():
            target_agent = orchestrator.get_agent(agent_id)
            with st.expander(f"Response from {target_agent.config.name}"):
                st.write(response)


def render_agent_stats(orchestrator: AgentOrchestrator):
    """Render agent statistics"""
    st.subheader("📈 Agent Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Agents", len(orchestrator.agents))
    
    with col2:
        bosses = len(orchestrator.get_agents_by_role(AgentRole.BOSS))
        st.metric("Bosses", bosses)
    
    with col3:
        workers = len(orchestrator.get_agents_by_role(AgentRole.WORKER))
        st.metric("Workers", workers)
    
    # Agent details table
    st.subheader("Agent Details")
    
    agent_data = []
    for agent in orchestrator.agents.values():
        subordinates = len(orchestrator.get_subordinates(agent.config.id))
        agent_data.append({
            "Name": agent.config.name,
            "Role": agent.config.role,
            "Model": agent.config.model.name,
            "Subordinates": subordinates,
            "Messages": len(agent.message_history),
        })
    
    st.dataframe(agent_data, use_container_width=True)


def main():
    """Main Streamlit app"""
    st.set_page_config(
        page_title="Multi-Agent Orchestrator",
        page_icon="🤖",
        layout="wide",
    )
    
    # Load configuration
    config_path = "config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    config = load_config(config_path)
    orchestrator = AgentOrchestrator(config)
    
    # Initialize session state
    initialize_session_state(orchestrator)
    
    # Header
    st.title(f"🤖 {config.app_name}")
    st.markdown("Multi-agent orchestration with hierarchical organization")
    
    # Sidebar
    render_sidebar(orchestrator)
    
    # Main content
    if st.session_state.show_hierarchy:
        render_hierarchy(orchestrator)
    else:
        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Chat", "Broadcast", "Statistics", "Settings"])
        
        with tab1:
            render_chat(orchestrator)
        
        with tab2:
            render_broadcast(orchestrator)
        
        with tab3:
            render_agent_stats(orchestrator)
        
        with tab4:
            st.subheader("⚙️ Settings")
            st.write("**Configuration File:** " + config_path)
            st.write(f"**App Name:** {config.app_name}")
            st.write(f"**Total Agents:** {len(config.agents)}")
            st.write(f"**Message History Limit:** {config.max_message_history}")
            st.write(f"**Persistence Enabled:** {config.enable_persistence}")
            
            # Show raw config
            if st.checkbox("Show Raw Configuration"):
                st.json({
                    "app_name": config.app_name,
                    "agents": [
                        {
                            "id": a.id,
                            "name": a.name,
                            "role": a.role,
                            "model": a.model.name,
                        }
                        for a in config.agents
                    ],
                })


if __name__ == "__main__":
    main()
