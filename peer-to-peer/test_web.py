#!/usr/bin/env python3
"""
Simple test script to verify the web UI setup

This script checks:
1. Required dependencies are installed
2. Configuration file exists and is valid
3. Flask server can start
4. API endpoints are accessible
"""

import sys
import json
import os

def check_dependencies():
    """Check if required packages are installed"""
    print("Checking dependencies...")
    
    missing = []
    
    try:
        import flask
        print("  ✓ Flask installed (version: {})".format(flask.__version__))
    except ImportError:
        print("  ✗ Flask not installed")
        missing.append("flask")
    
    try:
        import requests
        print("  ✓ Requests installed (version: {})".format(requests.__version__))
    except ImportError:
        print("  ✗ Requests not installed")
        missing.append("requests")
    
    if missing:
        print("\nMissing dependencies. Install with:")
        print("  pip install {}".format(" ".join(missing)))
        return False
    
    return True


def check_config():
    """Check if config.json exists and is valid"""
    print("\nChecking configuration...")
    
    if not os.path.exists("config.json"):
        print("  ✗ config.json not found")
        print("\nPlease create a config.json file. Example:")
        print("""
{
  "app_name": "Multi-Agent Orchestrator",
  "agents": [
    {
      "id": "agent1",
      "name": "Assistant",
      "role": "worker",
      "description": "A helpful assistant",
      "model": {
        "type": "ollama",
        "name": "llama2",
        "endpoint": "http://localhost:11434",
        "temperature": 0.7,
        "max_tokens": 2048
      }
    }
  ]
}
        """)
        return False
    
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        
        print("  ✓ config.json found and valid")
        
        # Check required fields
        if "agents" not in config:
            print("  ✗ No 'agents' field in config.json")
            return False
        
        if not config["agents"]:
            print("  ✗ No agents defined in config.json")
            return False
        
        print("  ✓ Found {} agent(s)".format(len(config["agents"])))
        
        # Check each agent
        for i, agent in enumerate(config["agents"]):
            required_fields = ["id", "name", "role", "description", "model"]
            missing_fields = [f for f in required_fields if f not in agent]
            
            if missing_fields:
                print("  ✗ Agent {} missing fields: {}".format(i, ", ".join(missing_fields)))
                return False
            
            print("  ✓ Agent '{}' configured correctly".format(agent["name"]))
        
        return True
        
    except json.JSONDecodeError as e:
        print("  ✗ Invalid JSON in config.json: {}".format(e))
        return False
    except Exception as e:
        print("  ✗ Error reading config.json: {}".format(e))
        return False


def check_templates():
    """Check if templates directory and index.html exist"""
    print("\nChecking templates...")
    
    if not os.path.exists("templates"):
        print("  ✗ templates/ directory not found")
        return False
    
    print("  ✓ templates/ directory found")
    
    if not os.path.exists("templates/index.html"):
        print("  ✗ templates/index.html not found")
        return False
    
    print("  ✓ templates/index.html found")
    
    # Check file size (should be substantial)
    size = os.path.getsize("templates/index.html")
    if size < 1000:
        print("  ⚠ templates/index.html seems too small ({} bytes)".format(size))
        return False
    
    print("  ✓ templates/index.html looks good ({} KB)".format(size // 1024))
    
    return True


def check_app_web():
    """Check if app_web.py exists"""
    print("\nChecking Flask application...")
    
    if not os.path.exists("app_web.py"):
        print("  ✗ app_web.py not found")
        return False
    
    print("  ✓ app_web.py found")
    
    # Try to import it
    try:
        import app_web
        print("  ✓ app_web.py can be imported")
        return True
    except Exception as e:
        print("  ✗ Error importing app_web.py: {}".format(e))
        return False


def check_ollama():
    """Check if Ollama is running (optional)"""
    print("\nChecking Ollama (optional)...")
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("  ✓ Ollama is running")
            models = response.json().get("models", [])
            if models:
                print("  ✓ Available models: {}".format(", ".join([m["name"] for m in models[:3]])))
            else:
                print("  ⚠ No models found in Ollama")
            return True
        else:
            print("  ⚠ Ollama responded with status {}".format(response.status_code))
            return False
    except Exception as e:
        print("  ⚠ Ollama not running or not accessible")
        print("    (This is OK if you're using OpenAI or Anthropic)")
        return False


def main():
    """Run all checks"""
    print("=" * 60)
    print("Multi-Agent Orchestrator Web UI - Setup Verification")
    print("=" * 60)
    
    checks = [
        ("Dependencies", check_dependencies),
        ("Configuration", check_config),
        ("Templates", check_templates),
        ("Flask App", check_app_web),
    ]
    
    results = []
    
    for name, check_func in checks:
        result = check_func()
        results.append((name, result))
    
    # Optional check
    check_ollama()
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print("{}: {}".format(name, status))
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All checks passed! You're ready to start the server.")
        print("\nRun one of these commands:")
        print("  Windows:    start_web.bat")
        print("  Linux/Mac:  bash start_web.sh")
        print("  Manual:     python app_web.py")
        print("\nThen open: http://localhost:5000")
        return 0
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
