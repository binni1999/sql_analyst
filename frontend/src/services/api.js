const API_BASE_URL = "http://localhost:8000";

export async function askDataAnalyst(question, conversationId = null) {
    const payload = {
        question,
    };

    if (conversationId) {
        payload.conversation_id = conversationId;
    }

    const response = await fetch(`${API_BASE_URL}/api/ask`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        throw new Error(
            `API request failed with status ${response.status}`
        );
    }

    return response.json();
}