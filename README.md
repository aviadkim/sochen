# AI Agent System for Software Development

This project implements a team of AI agents that collaborate to analyze, improve, and iterate upon your code. The agents use the Google Gemini 2.5 API and work together to handle tasks like code generation, review, testing, refactoring, and strategic planning.

## System Architecture

The system consists of two main components:

1. **Python Backend Server**: Contains the agent logic, Gemini API integration, and workflow orchestration
2. **VS Code Extension**: Provides the user interface within VS Code to trigger agent tasks and view results

The agents communicate with each other through a shared state, and the backend communicates with the VS Code extension via WebSockets.

## Agent Team

The system includes the following specialized agents:

- **Orchestrator**: Coordinates the workflow and decides which agent to invoke next
- **Architect**: Analyzes project structure and makes high-level design recommendations
- **Coder**: Writes new code based on requirements or modifies existing code
- **Reviewer**: Examines code for quality, style, and potential issues
- **Tester**: Creates and runs tests to verify code functionality
- **Refactorer**: Improves code structure without changing functionality
- **Security**: Identifies security vulnerabilities and recommends fixes
- **Documentation**: Creates or improves code documentation

Each agent has specific expertise, and they work together to create a complete development workflow.

## Setup Instructions

### Prerequisites

- Python 3.8+ installed
- Node.js and npm installed (for VS Code extension development)
- VS Code installed
- Google Gemini API key ([Get one here](https://aistudio.google.com/app/apikey))

### Setting Up the Python Backend

1. Clone this repository:
```bash
git clone https://github.com/yourusername/ai-agent-system.git
cd ai-agent-system
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3. Install required Python packages:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with your Gemini API key:
```
GEMINI_API_KEY=your_api_key_here
WEBSOCKET_HOST=localhost
WEBSOCKET_PORT=8765
```

### Setting Up the VS Code Extension

1. Navigate to the VS Code extension directory:
```bash
cd vscode-extension
```

2. Install dependencies:
```bash
npm install
```

3. Package the extension:
```bash
npm run package
```

4. Install the extension in VS Code:
   - Open VS Code
   - Go to Extensions (Ctrl+Shift+X)
   - Click the "..." menu and select "Install from VSIX..."
   - Browse to the `.vsix` file in the extension directory and install it

### Running the System

1. Start the Python backend server:
```bash
# From the project root
python main.py
```

2. Open VS Code with your project folder
3. Ensure the extension is active (check the status bar for "AI Agents")
4. Use the command palette (Ctrl+Shift+P) and type "AI Agents: Start New Task"
5. Enter your task description (e.g., "Review this file for bugs" or "Add unit tests")
6. The agents will analyze your code and provide results in the editor

## Incremental Testing Approach

To test the system incrementally:

1. **Start with a Single Agent Test**:
   - Modify `graph.py` to only use a specific agent (e.g., the Coder)
   - Test with simple tasks to verify the agent works properly

2. **Test Agent Pairs**:
   - Once individual agents work, test pairs that should work together (e.g., Coder → Reviewer)
   - Verify that the first agent's output is correctly passed to the second agent

3. **Add Agents Gradually**:
   - Add more agents to the workflow as each pair is verified
   - Test more complex chains (e.g., Architect → Coder → Tester → Reviewer)

4. **Full System Testing**:
   - Finally, test the complete system with all agents and the Orchestrator

## Development Notes

### Project Structure

The Python backend is organized as follows:

```
ai-agent-system/
├── agent_system/
│   ├── agents/             # Individual agent implementations
│   ├── memory/             # Vector store for agent memory
│   ├── tools/              # Utility tools for file and code operations
│   ├── config.py           # Configuration and initialization
│   ├── graph.py            # LangGraph workflow definition
│   ├── server.py           # WebSocket server
│   └── state.py            # State definitions
├── vscode-extension/       # VS Code extension
├── main.py                 # Main entry point
└── requirements.txt        # Python dependencies
```

### Adding New Agents

To add a new agent:

1. Create a new agent file in the `agents/` directory
2. Define the agent function that takes and returns an `AgentState`
3. Add the agent to `agents/__init__.py`
4. Update `graph.py` if needed to incorporate the agent into the workflow

### Customizing Agent Behavior

Each agent can be customized by modifying its prompt templates in the respective agent file. You can add domain-specific knowledge, change the tone or style, or adjust the types of suggestions it provides.

## Troubleshooting

- **Connection Issues**: Ensure the WebSocket server is running and the port (8765) is not blocked by a firewall
- **API Key Errors**: Verify your Gemini API key is correctly set in the `.env` file
- **Agent Errors**: Check the logs in the "AI Agents" output channel in VS Code for detailed error messages
- **Extension Not Loading**: Try reinstalling the extension or checking the VS Code Developer Tools for errors

## License

[MIT License](LICENSE)

---

Happy coding with your AI agent team! For questions or issues, please open an issue on GitHub.