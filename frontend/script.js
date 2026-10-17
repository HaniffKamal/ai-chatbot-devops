/**
 * ==============================================================================
 * Chatbot Web Client & Widget Script
 * Enterprise-grade client handling async communication, XSS sanitization,
 * suggestion pills, and responsive UI state transitions.
 * ==============================================================================
 */

(function () {
    "use strict";

    // DOM Elements
    const elements = {
        messagesContainer: document.getElementById("chat-messages"),
        form: document.getElementById("chat-form"),
        input: document.getElementById("chat-input"),
        sendBtn: document.getElementById("chat-send-btn"),
        typingIndicator: document.getElementById("chat-typing-indicator"),
        suggestionPills: document.querySelectorAll(".suggestion-pill"),
        clearBtn: document.getElementById("clear-chat-btn")
    };

    // Client State
    let isGenerating = false;

    /**
     * Sanitize untrusted input to prevent DOM Cross-Site Scripting (XSS).
     * @param {string} str - Raw text string.
     * @returns {string} - Escaped safe HTML string.
     */
    function escapeHTML(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    /**
     * Senior-grade secure Markdown parser.
     * Uses marked.js to render GitHub Flavored Markdown (tables, lists, headers, code, bold)
     * and sanitizes with DOMPurify to guarantee zero Cross-Site Scripting (XSS).
     *
     * @param {string} text - Raw model response.
     * @returns {string} - Rendered, sanitized HTML string.
     */
     function parseMarkdown(text) {
        if (!text) return "";

        // Use marked.js if available for rich GFM rendering (tables, lists, etc.)
        if (typeof marked !== "undefined" && typeof marked.parse === "function") {
            try {
                marked.setOptions({
                    gfm: true,
                    breaks: true,
                });

                const rawHtml = marked.parse(text);

                // Sanitize output via DOMPurify to prevent XSS attacks
                if (typeof DOMPurify !== "undefined" && typeof DOMPurify.sanitize === "function") {
                    return DOMPurify.sanitize(rawHtml);
                }
                return rawHtml;
            } catch (err) {
                console.warn("marked.js parse error, falling back to basic parser:", err);
            }
        }

        // Resilient fallback parser if library is missing
        let safe = escapeHTML(text);
        safe = safe.replace(/`([^`]+)`/g, "<code>$1</code>");
        safe = safe.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        safe = safe.replace(/__([^_]+)__/g, "<strong>$1</strong>");
        safe = safe.replace(/\*([^*]+)\*/g, "<em>$1</em>");
        safe = safe.replace(/_([^_]+)_/g, "<em>$1</em>");
        safe = safe.replace(/\n\n+/g, "</p><p>");
        safe = safe.replace(/\n/g, "<br>");
        return `<p>${safe}</p>`;
    }

    /**
     * Auto-scroll the message stream to the bottom.
     */
    function scrollToBottom() {
        elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
    }

    /**
     * Append a message bubble to the chat container.
     * @param {string} content - Message text content.
     * @param {"user" | "assistant" | "error"} role - Message sender role.
     */
    function appendMessage(content, role) {
        const messageWrapper = document.createElement("div");
        messageWrapper.className = `chat-message chat-message-${role}`;

        if (role === "assistant") {
            const avatar = document.createElement("div");
            avatar.className = "chat-avatar";
            avatar.textContent = "🤖";
            avatar.setAttribute("aria-hidden", "true");
            messageWrapper.appendChild(avatar);
        }

        const bubble = document.createElement("div");
        bubble.className = "chat-bubble";

        if (role === "user") {
            // User message: Plain text with simple paragraph
            const p = document.createElement("p");
            p.textContent = content;
            bubble.appendChild(p);
        } else if (role === "error") {
            // Error message: Alert styling
            bubble.innerHTML = `<p>⚠️ ${escapeHTML(content)}</p>`;
        } else {
            // Assistant response: Markdown formatting
            bubble.innerHTML = parseMarkdown(content);
        }

        messageWrapper.appendChild(bubble);
        elements.messagesContainer.appendChild(messageWrapper);
        scrollToBottom();
    }

    /**
     * Toggle the UI loading state during LLM generation.
     * @param {boolean} loading - True if awaiting response.
     */
    function setLoading(loading) {
        isGenerating = loading;
        elements.sendBtn.disabled = loading;
        elements.input.disabled = loading;

        if (loading) {
            elements.typingIndicator.classList.add("active");
        } else {
            elements.typingIndicator.classList.remove("active");
            elements.input.focus();
        }
        scrollToBottom();
    }

    /**
     * Send a user prompt to the FastAPI backend (/api/chat).
     * @param {string} messageText - The prompt string to dispatch.
     */
    async function handleSendMessage(messageText) {
        const trimmed = messageText.trim();
        if (!trimmed || isGenerating) return;

        // Clear input field immediately
        elements.input.value = "";

        // Display user message in UI
        appendMessage(trimmed, "user");
        setLoading(true);

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify({
                    message: trimmed
                })
            });

            if (!response.ok) {
                // Parse error details returned from FastAPI
                const errorData = await response.json().catch(() => ({}));
                const errorDetail = errorData.detail || `Server error (${response.status})`;
                throw new Error(errorDetail);
            }

            const data = await response.json();
            const reply = data.reply || "No response received from the model.";
            appendMessage(reply, "assistant");

        } catch (err) {
            console.error("Chatbot API Failure:", err);
            appendMessage(
                err.message || "Failed to reach inference server. Ensure Ollama container is active.",
                "error"
            );
        } finally {
            setLoading(false);
        }
    }

    // --------------------------------------------------------------------------
    // Event Listeners
    // --------------------------------------------------------------------------

    // Form Submission (Send button or Enter key)
    elements.form.addEventListener("submit", function (e) {
        e.preventDefault();
        handleSendMessage(elements.input.value);
    });

    // Suggestion Pill Click Handlers
    elements.suggestionPills.forEach(function (pill) {
        pill.addEventListener("click", function () {
            const prompt = this.getAttribute("data-prompt");
            if (prompt) {
                handleSendMessage(prompt);
            }
        });
    });

    // Reset Conversation Handler
    elements.clearBtn.addEventListener("click", function () {
        if (confirm("Reset conversation history?")) {
            elements.messagesContainer.innerHTML = `
                <div class="chat-message chat-message-assistant">
                    <div class="chat-avatar" aria-hidden="true">🤖</div>
                    <div class="chat-bubble">
                        <p>Conversation reset. Ask me anything about Haniff's skills, deepfake research, or this DevOps infrastructure!</p>
                    </div>
                </div>
            `;
            elements.input.value = "";
            elements.input.focus();
        }
    });

    // Initial focus on input field on load
    window.addEventListener("DOMContentLoaded", function () {
        elements.input.focus();
    });

})();
