const state = {
  leadId: null,
  name: "",
  email: "",
  company: "",
  messages: [],
  assessment: null,
  loading: false,
};

const elements = {
  leadForm: document.querySelector("#leadForm"),
  leadFormCard: document.querySelector("#leadFormCard"),
  formError: document.querySelector("#formError"),
  emptyState: document.querySelector("#emptyState"),
  messages: document.querySelector("#messages"),
  chatScroll: document.querySelector("#chatScroll"),
  messageForm: document.querySelector("#messageForm"),
  messageInput: document.querySelector("#messageInput"),
  sendButton: document.querySelector("#sendButton"),
  thinking: document.querySelector("#thinking"),
  newConversation: document.querySelector("#newConversation"),
  sessionChip: document.querySelector("#sessionChip"),
};

function generateLeadId() {
  return `lead-${Date.now()}`;
}

function setText(selector, value, empty = "—") {
  const node = document.querySelector(selector);
  node.textContent = value === null || value === undefined || value === "" ? empty : String(value);
}

function startConversation(event) {
  event.preventDefault();
  if (!elements.leadForm.reportValidity()) {
    elements.formError.hidden = false;
    return;
  }

  const data = new FormData(elements.leadForm);
  const name = String(data.get("name") || "").trim();
  const email = String(data.get("email") || "").trim();
  const company = String(data.get("company") || "").trim();
  if (!name || !email || !company) {
    elements.formError.hidden = false;
    return;
  }
  state.leadId = generateLeadId();
  state.name = name;
  state.email = email;
  state.company = company;
  state.messages = [];
  state.assessment = null;

  elements.formError.hidden = true;
  elements.leadFormCard.hidden = true;
  elements.emptyState.hidden = false;
  elements.sessionChip.hidden = false;
  elements.newConversation.disabled = false;
  elements.messageInput.disabled = false;
  elements.messageInput.focus();
  renderLeadDetails();
  renderAssessment(null);
  renderToolCalls([]);
}

function renderMessage(message) {
  const row = document.createElement("article");
  row.className = `message-row ${message.role}${message.isError ? " error" : ""}`;

  const avatar = document.createElement("span");
  avatar.className = "message-avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = message.role === "user" ? "Y" : "A";

  const content = document.createElement("div");
  content.className = "message-content";
  const label = document.createElement("span");
  label.className = "message-label";
  label.textContent = message.role === "user" ? "You" : "AI agent";
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = message.text;
  content.append(label, bubble);
  row.append(avatar, content);
  elements.messages.append(row);
}

function renderMessages() {
  elements.messages.replaceChildren();
  for (const message of state.messages) renderMessage(message);
  elements.emptyState.hidden = !state.leadId || state.messages.length > 0;
  scrollToBottom();
}

function renderLeadDetails() {
  setText("#detailName", state.name);
  setText("#detailEmail", state.email);
  setText("#detailCompany", state.company);
  setText("#detailLeadId", state.leadId, "Not started");
}

function renderAssessment(assessment) {
  state.assessment = assessment || null;
  const status = document.querySelector("#assessmentStatus");
  const allowedStatuses = ["new", "qualifying", "qualified", "handoff", "unqualified"];
  const statusValue = assessment?.lead_status;
  status.textContent = statusValue || "Not assessed";
  status.className = `status-badge ${allowedStatuses.includes(statusValue) ? `status-${statusValue}` : "status-neutral"}`;

  setText("#assessmentIntent", assessment?.intent);
  setText("#assessmentRequirements", assessment?.requirements);
  setText("#assessmentSolution", assessment?.current_solution);
  setText("#assessmentAction", assessment?.next_action?.replaceAll("_", " "));
  setText("#assessmentReason", assessment?.qualification_reason, "An assessment will appear after your first message.");

  const sizeRow = document.querySelector("#companySizeRow");
  sizeRow.hidden = assessment?.company_size === null || assessment?.company_size === undefined || assessment?.company_size === "";
  setText("#detailCompanySize", assessment?.company_size);

  const confidence = Number(assessment?.confidence);
  const validConfidence = Number.isFinite(confidence) && confidence >= 0;
  const percent = validConfidence ? Math.round(Math.min(confidence, 1) * 100) : null;
  setText("#assessmentConfidence", percent === null ? null : `${percent}%`);
  document.querySelector("#confidenceBar").style.width = `${percent ?? 0}%`;
}

function renderToolCalls(toolCalls) {
  const list = document.querySelector("#toolList");
  list.replaceChildren();
  if (!Array.isArray(toolCalls) || toolCalls.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted-empty";
    empty.textContent = state.messages.length ? "No MCP tools were used in the latest interaction." : "Tools will appear after your first message.";
    list.append(empty);
    return;
  }

  for (const tool of toolCalls) {
    const item = document.createElement("div");
    item.className = "tool-pill";
    const check = document.createElement("span");
    check.className = "tool-check";
    check.textContent = "✓";
    const name = document.createElement("span");
    name.textContent = String(tool);
    item.append(check, name);
    list.append(item);
  }
}

function showLoading(isLoading) {
  state.loading = isLoading;
  elements.thinking.hidden = !isLoading;
  elements.messageInput.disabled = isLoading || !state.leadId;
  elements.sendButton.disabled = isLoading || !state.leadId || !elements.messageInput.value.trim();
  elements.sendButton.querySelector("span:first-child").textContent = isLoading ? "Sending" : "Send";
  elements.newConversation.disabled = isLoading || !state.leadId;
  scrollToBottom();
}

function showError() {
  state.messages.push({
    role: "assistant",
    text: "Sorry, something went wrong while processing your request.",
    isError: true,
  });
  renderMessages();
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    elements.chatScroll.scrollTop = elements.chatScroll.scrollHeight;
  });
}

async function sendMessage(message = elements.messageInput.value) {
  const text = message.trim();
  if (!text || !state.leadId || state.loading) return;

  state.messages.push({ role: "user", text });
  renderMessages();
  elements.messageInput.value = "";
  resizeInput();
  showLoading(true);

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lead_id: state.leadId,
        message: text,
        name: state.name,
        email: state.email,
        company: state.company,
      }),
    });

    if (!response.ok) throw new Error(`Chat request failed with HTTP ${response.status}`);
    const result = await response.json();
    if (!result || typeof result.response !== "string" || !result.assessment || typeof result.assessment !== "object" || !Array.isArray(result.tool_calls)) {
      throw new Error("The chat API returned an invalid response shape");
    }

    state.messages.push({ role: "assistant", text: result.response });
    renderMessages();
    renderAssessment(result.assessment);
    renderToolCalls(result.tool_calls);
    renderLeadDetails();
  } catch (error) {
    console.error("Unable to process chat message:", error);
    showError();
  } finally {
    showLoading(false);
    elements.messageInput.focus();
  }
}

function resetConversation() {
  state.leadId = null;
  state.name = "";
  state.email = "";
  state.company = "";
  state.messages = [];
  state.assessment = null;
  state.loading = false;

  elements.leadForm.reset();
  elements.leadFormCard.hidden = false;
  elements.formError.hidden = true;
  elements.emptyState.hidden = true;
  elements.messages.replaceChildren();
  elements.sessionChip.hidden = true;
  elements.newConversation.disabled = true;
  elements.messageInput.value = "";
  elements.messageInput.disabled = true;
  elements.sendButton.disabled = true;
  elements.thinking.hidden = true;
  document.querySelector("#companySizeRow").hidden = true;
  renderLeadDetails();
  renderAssessment(null);
  renderToolCalls([]);
  elements.chatScroll.scrollTop = 0;
}

function resizeInput() {
  elements.messageInput.style.height = "auto";
  elements.messageInput.style.height = `${Math.min(elements.messageInput.scrollHeight, 125)}px`;
  elements.sendButton.disabled = state.loading || !state.leadId || !elements.messageInput.value.trim();
}

elements.leadForm.addEventListener("submit", startConversation);
elements.messageForm.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage();
});
elements.messageInput.addEventListener("input", resizeInput);
elements.messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    if (!elements.sendButton.disabled) sendMessage();
  }
});
elements.newConversation.addEventListener("click", resetConversation);
document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => sendMessage(button.dataset.prompt));
});

renderLeadDetails();
renderAssessment(null);
renderToolCalls([]);
