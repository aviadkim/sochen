const vscode = require('vscode');
const axios = require('axios');
const path = require('path');
const fs = require('fs');
const WebSocket = require('ws');

let socket;

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  console.log('Sochen extension is now active!');

  // Server URL from settings
  const getServerUrl = () => {
    const config = vscode.workspace.getConfiguration('sochen');
    return config.get('serverUrl') || 'http://localhost:3000';
  };

  // Check connection to Sochen server
  async function checkConnection() {
    try {
      const response = await axios.get(`${getServerUrl()}/status`);
      return response.data.status === 'operational';
    } catch (error) {
      console.error('Error connecting to Sochen server:', error.message);
      return false;
    }
  }

  // Register commands
  const disposables = [
    // Generate architecture plan
    vscode.commands.registerCommand('sochen.generateArchitecturePlan', async () => {
      const isConnected = await checkConnection();
      if (!isConnected) {
        vscode.window.showErrorMessage('Cannot connect to Sochen server. Make sure it is running.');
        return;
      }

      // Get requirements from the user
      const requirements = await vscode.window.showInputBox({
        prompt: 'Enter project requirements',
        placeHolder: 'Example: Create a REST API for a blog with users, posts, and comments'
      });

      if (!requirements) return;

      try {
        vscode.window.withProgress({
          location: vscode.ProgressLocation.Notification,
          title: 'Generating architecture plan...',
          cancellable: false
        }, async (progress) => {
          const response = await axios.post(`${getServerUrl()}/architect/plan`, {
            requirements
          });

          if (response.data.success) {
            // Create a new file with the architecture plan
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (!workspaceFolders) {
              vscode.window.showErrorMessage('No workspace folder is open.');
              return;
            }

            const filePath = path.join(workspaceFolders[0].uri.fsPath, 'architecture_plan.md');
            const content = `# Architecture Plan\n\n## Requirements\n\n${requirements}\n\n## Components\n\n${JSON.stringify(response.data.plan.components, null, 2)}\n\n## Data Flow\n\n${JSON.stringify(response.data.plan.data_flow, null, 2)}\n\n## Technology Stack\n\n${JSON.stringify(response.data.plan.technology_stack, null, 2)}`;

            fs.writeFileSync(filePath, content);
            
            const doc = await vscode.workspace.openTextDocument(filePath);
            await vscode.window.showTextDocument(doc);

            vscode.window.showInformationMessage('Architecture plan generated!');
          } else {
            vscode.window.showErrorMessage('Failed to generate architecture plan.');
          }
        });
      } catch (error) {
        console.error('Error generating architecture plan:', error);
        vscode.window.showErrorMessage(`Error: ${error.message}`);
      }
    }),

    // Implement component
    vscode.commands.registerCommand('sochen.implementComponent', async () => {
      const isConnected = await checkConnection();
      if (!isConnected) {
        vscode.window.showErrorMessage('Cannot connect to Sochen server. Make sure it is running.');
        return;
      }

      // Get specification and path
      const componentName = await vscode.window.showInputBox({
        prompt: 'Enter component name',
        placeHolder: 'Example: UserController'
      });

      if (!componentName) return;

      const componentSpec = await vscode.window.showInputBox({
        prompt: 'Enter component specification',
        placeHolder: 'Example: Controller that handles user registration, login, and profile management'
      });

      if (!componentSpec) return;

      // Choose file path
      const workspaceFolders = vscode.workspace.workspaceFolders;
      if (!workspaceFolders) {
        vscode.window.showErrorMessage('No workspace folder is open.');
        return;
      }

      const basePath = workspaceFolders[0].uri.fsPath;
      const relativePath = await vscode.window.showInputBox({
        prompt: 'Enter relative file path',
        placeHolder: 'Example: src/controllers/user_controller.py',
        value: `src/controllers/${componentName.toLowerCase()}.py`
      });

      if (!relativePath) return;

      const fullPath = path.join(basePath, relativePath);

      try {
        vscode.window.withProgress({
          location: vscode.ProgressLocation.Notification,
          title: `Implementing ${componentName}...`,
          cancellable: false
        }, async (progress) => {
          const response = await axios.post(`${getServerUrl()}/coder/implement`, {
            spec: {
              name: componentName,
              description: componentSpec,
              type: path.extname(fullPath).slice(1) // Get file extension
            },
            path: fullPath
          });

          if (response.data.success) {
            const doc = await vscode.workspace.openTextDocument(fullPath);
            await vscode.window.showTextDocument(doc);
            vscode.window.showInformationMessage(`Component ${componentName} implemented!`);
          } else {
            vscode.window.showErrorMessage(`Failed to implement ${componentName}.`);
          }
        });
      } catch (error) {
        console.error('Error implementing component:', error);
        vscode.window.showErrorMessage(`Error: ${error.message}`);
      }
    }),

    // Review code
    vscode.commands.registerCommand('sochen.reviewCode', async () => {
      const isConnected = await checkConnection();
      if (!isConnected) {
        vscode.window.showErrorMessage('Cannot connect to Sochen server. Make sure it is running.');
        return;
      }

      // Get active editor
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showErrorMessage('No active editor.');
        return;
      }

      const filePath = editor.document.uri.fsPath;

      try {
        vscode.window.withProgress({
          location: vscode.ProgressLocation.Notification,
          title: 'Reviewing code...',
          cancellable: false
        }, async (progress) => {
          const response = await axios.post(`${getServerUrl()}/reviewer/review`, {
            path: filePath
          });

          if (response.data.success) {
            // Create a new file with the review results
            const reviewPath = `${filePath}.review.md`;
            
            let content = `# Code Review: ${path.basename(filePath)}\n\n`;
            content += `## Quality Score: ${response.data.review.quality_score * 100}%\n\n`;
            
            if (response.data.review.issues.length > 0) {
              content += '## Issues\n\n';
              response.data.review.issues.forEach(issue => {
                content += `- **${issue.type}** (${issue.severity}): ${issue.message}\n`;
                if (issue.line) {
                  content += `  Line: ${issue.line}\n`;
                }
                content += '\n';
              });
            }
            
            if (response.data.review.suggestions.length > 0) {
              content += '## Suggestions\n\n';
              response.data.review.suggestions.forEach(suggestion => {
                content += `- ${suggestion}\n`;
              });
            }

            fs.writeFileSync(reviewPath, content);
            
            const doc = await vscode.workspace.openTextDocument(reviewPath);
            await vscode.window.showTextDocument(doc, { viewColumn: vscode.ViewColumn.Beside });

            vscode.window.showInformationMessage('Code review completed!');
          } else {
            vscode.window.showErrorMessage('Failed to review code.');
          }
        });
      } catch (error) {
        console.error('Error reviewing code:', error);
        vscode.window.showErrorMessage(`Error: ${error.message}`);
      }
    }),

    // Status bar item
    (() => {
      const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
      statusBarItem.text = '$(robot) Sochen';
      statusBarItem.tooltip = 'Sochen AI Agent System';
      statusBarItem.command = 'sochen.showMenu';
      statusBarItem.show();

      // Update status bar item
      setInterval(async () => {
        try {
          const isConnected = await checkConnection();
          statusBarItem.text = isConnected 
            ? '$(robot) Sochen: Connected' 
            : '$(robot) Sochen: Disconnected';
        } catch (error) {
          statusBarItem.text = '$(robot) Sochen: Error';
        }
      }, 30000); // Check every 30 seconds

      return statusBarItem;
    })(),

    // Show menu
    vscode.commands.registerCommand('sochen.showMenu', async () => {
      const isConnected = await checkConnection();
      const prefix = isConnected ? '' : 'Disconnected - ';

      const selection = await vscode.window.showQuickPick([
        {
          label: `${prefix}Generate Architecture Plan`,
          description: 'Create a system architecture based on requirements',
          command: 'sochen.generateArchitecturePlan',
          disabled: !isConnected
        },
        {
          label: `${prefix}Implement Component`,
          description: 'Generate code for a new component',
          command: 'sochen.implementComponent',
          disabled: !isConnected
        },
        {
          label: `${prefix}Review Code`,
          description: 'Review the current file for issues and suggestions',
          command: 'sochen.reviewCode',
          disabled: !isConnected
        },
        {
          label: 'Settings',
          description: 'Configure Sochen extension',
          command: 'sochen.openSettings'
        }
      ], {
        placeHolder: 'Select an action'
      });

      if (selection && !selection.disabled) {
        if (selection.command === 'sochen.openSettings') {
          vscode.commands.executeCommand('workbench.action.openSettings', 'sochen');
        } else {
          vscode.commands.executeCommand(selection.command);
        }
      }
    }),

    // Start task command
    vscode.commands.registerCommand('ai-agent-system.startTask', async () => {
      const taskDescription = await vscode.window.showInputBox({
        prompt: 'Enter task description for AI Agents'
      });

      if (taskDescription) {
        vscode.window.showInformationMessage(`Starting task: ${taskDescription}`);
        startWebSocket(taskDescription);
      }
    })
  ];

  context.subscriptions.push(...disposables);
}

function startWebSocket(taskDescription) {
  const websocketHost = vscode.workspace.getConfiguration('ai-agent-system').get('websocketHost') || 'localhost';
  const websocketPort = vscode.workspace.getConfiguration('ai-agent-system').get('websocketPort') || 8765;
  const websocketUrl = `ws://${websocketHost}:${websocketPort}`;

  socket = new WebSocket(websocketUrl);

  socket.onopen = () => {
    console.log('Connected to WebSocket server');
    socket.send(JSON.stringify({ task: taskDescription }));
  };

  socket.onmessage = (event) => {
    console.log('Received message:', event.data);
    vscode.window.showInformationMessage(`Agent response: ${event.data}`);
  };

  socket.onclose = () => {
    console.log('Disconnected from WebSocket server');
    vscode.window.showInformationMessage('AI Agents task completed or disconnected.');
  };

  socket.onerror = (error) => {
    console.error('WebSocket error:', error);
    vscode.window.showErrorMessage(`AI Agents WebSocket error: ${error}`);
  };
}

function deactivate() {
  if (socket) {
    socket.close();
  }
  console.log('Agent System extension deactivated');
}

module.exports = {
  activate,
  deactivate
};
