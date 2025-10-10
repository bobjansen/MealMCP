// Chat functionality - shared between dashboard and standalone chat page
// Configure marked for safe rendering
if (typeof marked !== 'undefined') {
    marked.setOptions({
        breaks: true,
        gfm: true,
        headerIds: false,
        mangle: false
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderMarkdown(text) {
    if (typeof marked === 'undefined') {
        return escapeHtml(text).replace(/\n/g, '<br>');
    }
    let html = marked.parse(text);
    html = html.replace(/<pre><code[^>]*>([\s\S]*?)<\/code><\/pre>/gi, '$1');
    html = html.replace(/<\/?pre>/gi, '');
    return html;
}

class ChatInterface {
    constructor(containerId, inputId, sendBtnId, thinkingPrefix = '', isAdmin = false) {
        this.container = document.getElementById(containerId);
        this.input = document.getElementById(inputId);
        this.sendBtn = document.getElementById(sendBtnId);
        this.thinkingId = thinkingPrefix + 'Thinking';
        this.isAdmin = isAdmin;

        if (!this.container || !this.input || !this.sendBtn) {
            console.error('Chat interface elements not found');
            return;
        }
    }

    addMessage(content, type = 'user', labels = { user: 'You', assistant: 'AI Assistant' }) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        const icon = type === 'user' ? 'fas fa-user' : 'fas fa-robot';
        const iconColor = 'text-primary';
        const name = type === 'user' ? labels.user : labels.assistant;

        let renderedContent;
        if (type === 'assistant') {
            renderedContent = renderMarkdown(content);
        } else {
            renderedContent = escapeHtml(content);
        }

        messageDiv.innerHTML = `
            <div class="d-flex">
                <div class="me-3">
                    <i class="${icon} ${iconColor} fs-5"></i>
                </div>
                <div class="flex-grow-1">
                    <strong class="${iconColor}">${name}</strong>
                    <div class="mt-2 message-content">${renderedContent}</div>
                </div>
            </div>
        `;

        this.container.appendChild(messageDiv);
    }

    addToolMessage(toolName, labels = { tool: 'Tool', executed: 'Executed successfully' }) {
        // Only show tool messages to admin users
        if (!this.isAdmin) {
            return;
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message tool';
        messageDiv.innerHTML = `
            <div class="d-flex">
                <div class="me-3">
                    <i class="fas fa-tools text-success fs-5"></i>
                </div>
                <div class="flex-grow-1">
                    <strong class="text-success">${labels.tool}: ${toolName}</strong>
                    <div class="mt-1"><small>${labels.executed}</small></div>
                </div>
            </div>
        `;
        this.container.appendChild(messageDiv);
    }

    addThinking(thinkingText = 'Thinking...') {
        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = 'thinking';
        thinkingDiv.id = this.thinkingId;
        thinkingDiv.innerHTML = `<i class="fas fa-brain"></i> ${thinkingText}`;
        this.container.appendChild(thinkingDiv);
    }

    removeThinking() {
        const thinking = document.getElementById(this.thinkingId);
        if (thinking) {
            thinking.remove();
        }
    }

    clearMessages() {
        this.container.innerHTML = '';
    }

    async sendMessage(labels = {}) {
        const message = this.input.value.trim();
        if (!message) return;

        // Add user message
        this.addMessage(message, 'user', labels);

        // Clear input and disable button
        this.input.value = '';
        this.sendBtn.disabled = true;

        // Show thinking
        this.addThinking(labels.thinking || 'Thinking...');

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Chat request failed');
            }

            // Remove thinking
            this.removeThinking();

            // Process responses
            const responses = result.responses || [];
            for (const resp of responses) {
                if (resp.content && resp.content.trim()) {
                    this.addMessage(resp.content, 'assistant', labels);
                }

                const toolCalls = resp.tool_calls || [];
                for (const toolCall of toolCalls) {
                    this.addToolMessage(toolCall.tool_name, labels);
                }
            }

        } catch (error) {
            this.removeThinking();
            this.addMessage((labels.error || 'Error') + ': ' + error.message, 'assistant', labels);
        } finally {
            this.sendBtn.disabled = false;
            this.input.focus();
        }
    }

    async loadHistory(labels = {}) {
        try {
            const response = await fetch('/api/chat/history');
            const data = await response.json();

            console.log('Chat history loaded:', data); // Debug log

            if (data.messages && data.messages.length > 0) {
                this.clearMessages();

                // Reverse for newest-first display (with column-reverse CSS)
                const reversedMessages = [...data.messages].reverse();

                console.log('Loading', reversedMessages.length, 'messages'); // Debug log

                for (const message of reversedMessages) {
                    if (message.role === 'user') {
                        this.addMessage(message.content, 'user', labels);
                    } else if (message.role === 'assistant') {
                        this.addMessage(message.content, 'assistant', labels);
                        const toolCalls = message.tool_calls || [];
                        for (const toolCall of toolCalls) {
                            if (toolCall.function) {
                                this.addToolMessage(toolCall.function.name, labels);
                            }
                        }
                    }
                }
            } else {
                console.log('No chat history found'); // Debug log
            }
        } catch (error) {
            console.error('Failed to load chat history:', error);
        }
    }

    setMessage(text) {
        this.input.value = text;
    }

    handleKeyPress(event) {
        if (event.key === 'Enter') {
            this.sendMessage();
        }
    }
}
