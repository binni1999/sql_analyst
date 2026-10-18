const API_BASE_URL = (
    import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "");

export async function askDataAnalyst(
    question,
    conversationId = null,
    humanApproval = null,
) {
    const payload = { question };
    if (conversationId) payload.conversation_id = conversationId;
    if (typeof humanApproval === "boolean") payload.human_approval = humanApproval;

    let response;
    try {
        response = await fetch(`${API_BASE_URL}/api/ask`, {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
    } catch {
        const error = new Error("We couldn't reach DataPilot. Check your connection and try again.");
        error.code = "NETWORK_ERROR";
        error.retryable = true;
        throw error;
    }

    let data;
    try { data = await response.json(); } catch { data = null; }

    if (!response.ok) {
        const error = new Error("DataPilot couldn't process this request. Please try again.");
        error.code = data?.error_code || (response.status >= 500 ? "SERVER_ERROR" : "REQUEST_FAILED");
        error.retryable = response.status === 429 || response.status >= 500;
        error.reference = data?.error_reference;
        throw error;
    }
    if (!data || typeof data !== "object") {
        const error = new Error("DataPilot returned an invalid response. Please try again.");
        error.code = "INVALID_RESPONSE";
        error.retryable = true;
        throw error;
    }
    return data;
} 
