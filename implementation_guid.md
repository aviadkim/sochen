# AI Agent System Implementation Guide

This document provides a detailed guide on how to implement and test the AI agent system for software development.

## Implementation Strategy: Incremental Approach

The best way to build this system is incrementally, testing each component before moving on to the next. This approach reduces complexity and makes debugging easier.

### Phase 1: Set Up the Environment

1. **Create Project Structure**
   ```
   mkdir ai-agent-system
   cd ai-agent-system
   mkdir -p agent_system/agents agent_system/memory agent_system/tools vscode-extension
   ```

2. **Set Up Python Environment**
   ```bash
   python -m venv venv
   # Activate the virtual environment
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Create requirements.txt**
   ```
   langchain>=0.1.0
   langgraph>=0.0.16
   langchain-google-genai>=0.0.3
   websockets>=11.0.3
   fastapi>=0.103.1
   uvicorn>=0.23.2
   pydantic>=2.4.2
   python-dotenv>=1.0.0
   faiss-cpu>=1.7.4
   ```

4. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Create .env File**
   ```
   GEMINI_API_KEY=your_api_key_here
   WEBSOCKET_HOST=localhost
   WEBSOCKET_PORT=8765
   ```

### Phase 2: Implement Core Components

1. **Copy Configuration Module**
   - Create `agent_system/config.py` with the configuration code

2. **Copy State Definitions**
   - Create `agent_system/state.py` with the state model definitions

3. **Implement Basic Tools**
   - Create `agent_system/tools/file_tools.py` with file system operations
   - Create `agent_system/tools/code_analysis.py` with code analysis functions

4. **Implement Memory System**
   - Create `agent_system/memory/vector_store.py` with the memory implementation

### Phase 3: Implement Individual Agents

Start with the most essential agents and add more as you proceed.

1. **Initialize Agents Package**
   - Create `agent_system/agents/__init__.py` with just the core agents you want to start with

2. **Implement Orchestrator Agent**
   - Create `agent_system/agents/orchestrator.py`

3. **Implement Coder Agent**
   - Create `agent_system/agents/coder.py`

4. **Implement Reviewer Agent**
   - Create `agent_system/agents/reviewer.py`

### Phase 4: Create Workflow Graph

1. **Create Simple Graph**
   - Create `agent_system/graph.py` with a simplified workflow involving just a few agents

2. **Implement Basic Server**
   - Create `agent_system/server.py` with the WebSocket server code
   - Create `main.py` as the entry point

### Phase 5: Test Backend Functionality

1. **Create a Simple Test Script**
   ```python
   # test_agents.py
   import asyncio
   from agent_system.server import run_workflow

   async def test():
       initial_state = {
           "task": "Write a simple Python function to calculate factorial",
           "status": "RUNNING",
           "messages": [],
           "workflow_history": [],
           "files": {},
       }
       
       final_state = await run_workflow(initial_state)
       print("Final state:", final_state)

   if __name__ == "__main__":
       asyncio.run(test())
   ```

2. **Run the Test**
   ```bash
   python test_agents.py
   ```

3. **Analyze Results and Debug**
   - Check the output for errors
   - Review the agent logs
   - Make adjustments as needed

### Phase 6: Add More Agents

Once the basic flow works, incrementally add more agents and expand functionality:

1. **Implement Tester Agent**
   - Create `agent_system/agents/tester.py`

2. **Implement Security Agent**
   - Create `agent_system/agents/security.py` 

3. **Update the Workflow Graph**
   - Modify `agent_system/graph.py` to incorporate the new agents

4. **Test After Each Addition**
   - Run the test script to ensure everything still works

### Phase 7: Implement VS Code Extension

1. **Create Basic Extension Files**
   - Create `vscode-extension/extension.js`
   - Create `vscode-extension/package.json`

2. **Install Extension Dependencies**
   ```bash
   cd vscode-extension
   npm install
   ```

3. **Package the Extension**
   ```bash
   npm run package
   ```

4. **Install in VS Code**
   - Install the .vsix file in VS Code

### Phase 8: End-to-End Testing

1. **Start the Backend Server**
   ```bash
   python main.py
   ```

2. **Connect From VS Code**
   - Open VS Code and ensure the extension connects to the server

3. **Test Simple Workflow**
   - Start with a simple task like "Review this file"
   - Check that the whole process works end-to-end

## Useful Testing Strategies

### Isolated Agent Testing

To test a single agent in isolation:

```python
from agent_system.agents.coder import coder_agent
from agent_system.config import get_llm

# Create a simple test state
test_state = {
    "task": "Write a Python function to calculate the factorial of a number",
    "focused_file_path": "factorial.py",
    "files": {},
    "messages": [],
    "workflow_history": []
}

# Run the agent
result_state = coder_agent(test_state)
print("Generated code:", result_state.get("files", {}).get("factorial.py", {}).get("content", ""))
```

### Testing Agent Chains

To test a specific agent sequence without the full Orchestrator logic:

```python
from agent_system.agents.coder import coder_agent
from agent_system.agents.reviewer import reviewer_agent

# Create initial state
test_state = {
    "task": "Write a Python function to calculate the factorial of a number",
    "focused_file_path": "factorial.py",
    "files": {},
    "messages": [],
    "workflow_history": []
}

# Run the chain
coder_result = coder_agent(test_state)
reviewer_result = reviewer_agent(coder_result)

print("Code issues found:", len(reviewer_result.get("code_issues", [])))
```

### Testing WebSocket Server

You can test the WebSocket server with a simple client:

```python
import asyncio
import websockets
import json

async def test_client():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        message = {
            "type": "run_workflow",
            "task": "Write a Python function to calculate factorial",
            "workflow_id": "test_workflow"
        }
        await websocket.send(json.dumps(message))
        print(f"Sent: {message}")
        
        # Wait for response
        response = await websocket.recv()
        print(f"Received: {response}")
        
        # Wait for results
        while True:
            response = await websocket.recv()
            data = json.loads(response)
            print(f"Received: {data['type']}")
            
            if data.get("type") == "status" and data.get("data", {}).get("status") == "COMPLETED":
                # Request final results
                await websocket.send(json.dumps({
                    "type": "get_workflow_results",
                    "workflow_id": "test_workflow"
                }))
            
            if data.get("type") == "workflow_results":
                print("Final results:", data.get("state"))
                break

asyncio.run(test_client())
```

## Advanced Customization

### Adding Domain-Specific Knowledge

You can enhance agent capabilities by:

1. **Customizing Prompts**: Modify agent prompts to include domain-specific instructions
2. **Adding Reference Materials**: Load domain knowledge into the memory system
3. **Implementing Custom Tools**: Create specialized tools for your domain

### Fine-tuning the LLM

For optimal results, consider fine-tuning Gemini on examples specific to your codebase or domain:

1. Create a dataset of code examples and desired outputs
2. Use Google's fine-tuning capabilities for Gemini
3. Update the `get_llm` function in `config.py` to use your fine-tuned model

### Scaling the System

As you add more agents and complexity:

1. Implement better error handling and recovery mechanisms
2. Consider using a database for persistent storage instead of in-memory
3. Add monitoring and analytics to track agent performance
4. Optimize token usage for cost efficiency

## Troubleshooting Common Issues

### Agent Communication Problems

If agents aren't properly sharing information:
- Check the state passing between agents
- Ensure the state schema is consistent
- Verify that all agents are correctly updating the shared state

### WebSocket Connection Issues

If the VS Code extension can't connect:
- Confirm the server is running on the correct port
- Check for firewall restrictions
- Verify the WebSocket URL configuration

### LLM API Errors

If you're getting API errors:
- Validate your API key
- Check your API quota and limits
- Ensure your prompt lengths aren't exceeding model limits

### Performance Optimization

If the system is running slowly:
- Reduce the context size for LLM calls
- Implement caching for frequent operations
- Consider using faster model variants for simpler tasks

## Best Practices for Production

1. **Error Handling**: Implement robust error handling and recovery
2. **Logging**: Set up comprehensive logging for debugging
3. **Rate Limiting**: Implement rate limiting for API calls
4. **Security**: Secure API keys and sensitive information
5. **Testing**: Create automated tests for regression testing
6. **Documentation**: Keep documentation updated as the system evolves

By following this incremental approach, you'll build a functional AI agent system while maintaining the ability to debug and improve each component along the way.