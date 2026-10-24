const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const conversation = document.querySelector("#conversation");
const sendButton = document.querySelector("#send-button");
const clearButton = document.querySelector("#clear-chat");
const suggestions = document.querySelector(".suggestions");

const messages = [];

function addMessage(role, content, label) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}-message`;

  const text = document.createElement("p");
  text.textContent = content;
  wrapper.append(text);

  const caption = document.createElement("span");
  caption.className = "message-time";
  caption.textContent = label;
  wrapper.append(caption);

  conversation.append(wrapper);
  conversation.scrollTop = conversation.scrollHeight;
}

function setBusy(busy) {
  sendButton.disabled = busy;
  input.disabled = busy;
  sendButton.setAttribute("aria-label", busy ? "Waiting for reply" : "Send message");
}

async function sendMessage(message) {
  if (messages.length >= 19) {
    messages.splice(0, messages.length - 18);
  }
  messages.push({ role: "user", content: message });
  addMessage("user", message, "You");
  suggestions.hidden = true;
  input.value = "";
  setBusy(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "The chat request failed.");
    }

    messages.push({ role: "assistant", content: result.reply });
    addMessage("assistant", result.reply, "Sarvam assistant");
  } catch (error) {
    messages.pop();
    addMessage("assistant", error.message, "Could not send");
  } finally {
    setBusy(false);
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (message && !sendButton.disabled) {
    sendMessage(message);
  }
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

suggestions.addEventListener("click", (event) => {
  const button = event.target.closest("[data-prompt]");
  if (button && !sendButton.disabled) {
    input.value = button.dataset.prompt;
    form.requestSubmit();
  }
});

clearButton.addEventListener("click", () => {
  messages.length = 0;
  conversation.replaceChildren();
  addMessage(
    "assistant",
    "Hi there. I can help you explore general appointment preparation and care coordination using fictional examples. What would you like to try?",
    "Sarvam assistant",
  );
  suggestions.hidden = false;
  input.value = "";
  input.focus();
});
