const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

async function authRequest(path, options = {}) {
    let response;
    try {
        response = await fetch(`${API_BASE_URL}/api/auth${path}`, {
            ...options,
            credentials: "include",
            headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        });
    } catch {
        const error = new Error("Could not connect to DataPilot. Check that the backend is running.");
        error.code = "NETWORK_ERROR";
        throw error;
    }
    let data = null;
    try { data = await response.json(); } catch { /* handled below */ }
    if (!response.ok) {
        const error = new Error(data?.detail || "Authentication request failed.");
        error.status = response.status;
        error.code = response.status === 401 ? "UNAUTHORIZED" : "AUTH_ERROR";
        throw error;
    }
    return data;
}

export const getCurrentUser = () => authRequest("/me");
export const signup = (payload) => authRequest("/signup", { method: "POST", body: JSON.stringify(payload) });
export const login = (payload) => authRequest("/login", { method: "POST", body: JSON.stringify(payload) });
export const logout = () => authRequest("/logout", { method: "POST", body: "{}" });
