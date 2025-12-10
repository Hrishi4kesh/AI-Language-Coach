let selectedLanguage = "spanish";

function changeLanguage() {
    selectedLanguage = document.getElementById("lang").value;
    addMessage(`Language changed to ${selectedLanguage.toUpperCase()}.`, "bot");
}

async function sendMessage() {
    const inputField = document.getElementById("user-input");
    const message = inputField.value.trim();
    if (!message) return;

    addMessage(message, "user");
    inputField.value = "";

    const response = await fetch("http://127.0.0.1:5000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
            message: text,
            language: selectedLanguage })
    });

    const data = await response.json();
    addMessage(data.reply, "bot");
}

function addMessage(text, sender) {
    const box = document.getElementById("chat-box");
    const msg = document.createElement("div");
    msg.classList.add("message", sender);
    msg.innerText = text;
    box.appendChild(msg);
    box.scrollTop = box.scrollHeight;
}

async function getSummary() {
    const response = await fetch("http://127.0.0.1:5000/summary");
    const data = await response.json();

    let summaryText = "📝 Mistakes Summary:\n\n";

    if (data.mistakes.length === 0) {
        summaryText += "No mistakes recorded yet!";
    } else {
        data.mistakes.forEach((item, index) => {
            summaryText += `${index + 1}. You said: "${item.user_input}"\n`;
            summaryText += `   Correction: "${item.correction}"\n\n`;
        });
    }

    addMessage(summaryText, "bot");
}
