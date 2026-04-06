/**
 * 🤖 Chatbot Kinh Tế Việt Nam — Frontend Logic
 *
 * Handles:
 *  - Chat message send/receive via API
 *  - Message rendering with sources
 *  - Session stats tracking
 *  - Sidebar toggle (mobile)
 *  - Health check polling
 */

// ──────────────────────────────────────────────
// Config & State
// ──────────────────────────────────────────────
const API_BASE = window.location.origin;

const state = {
    messages: [],
    isLoading: false,
    totalQuestions: 0,
    totalTime: 0,
    totalDocs: 0,
    llmProvider: "-",
    isOnline: false,
};

// ──────────────────────────────────────────────
// DOM References
// ──────────────────────────────────────────────
const chatMessages = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");
const btnSend = document.getElementById("btnSend");
const welcomeScreen = document.getElementById("welcomeScreen");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");

// Stats elements
const statQuestions = document.getElementById("statQuestions");
const statAvgTime = document.getElementById("statAvgTime");
const statDocs = document.getElementById("statDocs");
const statLLM = document.getElementById("statLLM");
const llmName = document.getElementById("llmName");

// ──────────────────────────────────────────────
// Health Check
// ──────────────────────────────────────────────
async function checkHealth() {
    try {
        const res = await fetch(`${API_BASE}/api/health`);
        const data = await res.json();

        state.isOnline = data.model_loaded;
        state.llmProvider = data.llm_provider || "-";

        statusDot.className = `status-dot ${data.model_loaded ? "online" : ""}`;
        statusText.textContent = data.model_loaded ? "Sẵn sàng" : "Đang khởi tạo...";

        const displayName = {
            openai: "OpenAI",
            gemini: "Gemini",
            groq: "Groq",
        };
        llmName.textContent = displayName[data.llm_provider] || data.llm_provider;
        statLLM.textContent = (displayName[data.llm_provider] || data.llm_provider).slice(0, 7);
    } catch (e) {
        statusDot.className = "status-dot offline";
        statusText.textContent = "Không kết nối";
        state.isOnline = false;
    }
}

// Poll health every 10s
checkHealth();
setInterval(checkHealth, 10000);

// ──────────────────────────────────────────────
// Update Stats
// ──────────────────────────────────────────────
function updateStats() {
    statQuestions.textContent = state.totalQuestions;
    const avg = state.totalQuestions > 0
        ? (state.totalTime / state.totalQuestions).toFixed(1) + "s"
        : "0s";
    statAvgTime.textContent = avg;
    statDocs.textContent = state.totalDocs;
}

// ──────────────────────────────────────────────
// Message Rendering
// ──────────────────────────────────────────────

/**
 * Create a message element and append to chat.
 */
function addMessage(role, content, meta = {}) {
    // Hide welcome screen
    if (welcomeScreen) {
        welcomeScreen.style.display = "none";
    }

    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = role === "user" ? "👤" : "🤖";

    const body = document.createElement("div");
    body.className = "message-body";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = content;

    body.appendChild(bubble);

    // Meta info (time, docs count)
    if (meta.time !== undefined) {
        const metaDiv = document.createElement("div");
        metaDiv.className = "message-meta";
        metaDiv.innerHTML = `⏱️ ${meta.time}s`;
        if (meta.docsCount !== undefined) {
            metaDiv.innerHTML += ` &nbsp;·&nbsp; 📄 ${meta.docsCount} tài liệu`;
        }
        body.appendChild(metaDiv);
    }

    // Source documents
    if (meta.sources && meta.sources.length > 0) {
        const toggleBtn = document.createElement("button");
        toggleBtn.className = "sources-toggle";
        toggleBtn.innerHTML = `📄 Xem ${meta.sources.length} tài liệu nguồn <span class="arrow">▼</span>`;

        const panel = document.createElement("div");
        panel.className = "sources-panel";

        meta.sources.forEach((src, i) => {
            const card = document.createElement("div");
            card.className = "source-card";

            const sourceName = src.source || "Không rõ nguồn";
            const fileName = sourceName.split("/").pop();

            card.innerHTML = `
                <div class="source-card-title">📑 Tài liệu ${i + 1} — ${fileName}</div>
                ${src.content}
            `;
            panel.appendChild(card);
        });

        toggleBtn.addEventListener("click", () => {
            toggleBtn.classList.toggle("open");
            panel.classList.toggle("open");
        });

        body.appendChild(toggleBtn);
        body.appendChild(panel);
    }

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(body);
    chatMessages.appendChild(msgDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return msgDiv;
}

/**
 * Show typing indicator while waiting for response.
 */
function showTyping() {
    const msgDiv = document.createElement("div");
    msgDiv.className = "message bot";
    msgDiv.id = "typingMsg";

    msgDiv.innerHTML = `
        <div class="avatar">🤖</div>
        <div class="message-body">
            <div class="bubble">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        </div>
    `;

    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTyping() {
    const el = document.getElementById("typingMsg");
    if (el) el.remove();
}

// ──────────────────────────────────────────────
// Send Message
// ──────────────────────────────────────────────
async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || state.isLoading) return;

    // Add user message
    addMessage("user", text);
    chatInput.value = "";
    autoResize(chatInput);

    // Disable input
    state.isLoading = true;
    btnSend.disabled = true;
    chatInput.disabled = true;

    // Show typing
    showTyping();

    try {
        const res = await fetch(`${API_BASE}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: text }),
        });

        hideTyping();

        if (!res.ok) {
            const err = await res.json();
            addMessage("bot", `❌ Lỗi: ${err.detail || "Không thể xử lý câu hỏi."}`);
            return;
        }

        const data = await res.json();

        // Add bot response
        addMessage("bot", data.answer, {
            time: data.response_time,
            docsCount: data.num_docs_graded,
            sources: data.sources || [],
        });

        // Update stats
        state.totalQuestions++;
        state.totalTime += data.response_time;
        state.totalDocs += data.num_docs_graded;
        updateStats();

    } catch (e) {
        hideTyping();
        addMessage("bot", "❌ Không thể kết nối đến server. Vui lòng kiểm tra server đang chạy.");
    } finally {
        state.isLoading = false;
        btnSend.disabled = false;
        chatInput.disabled = false;
        chatInput.focus();
    }
}

// ──────────────────────────────────────────────
// Input Handlers
// ──────────────────────────────────────────────
function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoResize(el) {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

// ──────────────────────────────────────────────
// Suggestion Chips
// ──────────────────────────────────────────────
function askSuggestion(chipEl) {
    chatInput.value = chipEl.textContent;
    sendMessage();
}

// ──────────────────────────────────────────────
// Clear Chat
// ──────────────────────────────────────────────
function clearChat() {
    // Remove all messages except welcome
    const messages = chatMessages.querySelectorAll(".message");
    messages.forEach((m) => m.remove());

    // Show welcome again
    if (welcomeScreen) {
        welcomeScreen.style.display = "flex";
    }

    // Reset stats
    state.totalQuestions = 0;
    state.totalTime = 0;
    state.totalDocs = 0;
    updateStats();
}

// ──────────────────────────────────────────────
// Sidebar Toggle (Mobile)
// ──────────────────────────────────────────────
function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    sidebar.classList.toggle("open");

    // Overlay
    let overlay = document.querySelector(".sidebar-overlay");
    if (!overlay) {
        overlay = document.createElement("div");
        overlay.className = "sidebar-overlay";
        overlay.addEventListener("click", toggleSidebar);
        document.body.appendChild(overlay);
    }
    overlay.classList.toggle("active");
}

// ──────────────────────────────────────────────
// Focus input on load
// ──────────────────────────────────────────────
window.addEventListener("load", () => {
    chatInput.focus();
});
