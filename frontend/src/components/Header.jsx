import { useEffect, useState } from "react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

function Header() {
    const [health, setHealth] = useState("checking");

    useEffect(() => {
        let active = true;
        const checkHealth = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/health/ready`, { cache: "no-store" });
                const data = await response.json();
                if (!active) return;
                const dependencies = data?.dependencies;
                const healthy = response.ok && data?.status === "ready" &&
                    (!dependencies || Object.values(dependencies).every((value) => value === true));
                setHealth(healthy ? "connected" : "degraded");
            } catch {
                if (active) setHealth("disconnected");
            }
        };
        checkHealth();
        const intervalId = window.setInterval(checkHealth, 30000);
        return () => {
            active = false;
            window.clearInterval(intervalId);
        };
    }, []);

    const statusLabels = {
        checking: "Checking backend…",
        connected: "Backend Connected",
        degraded: "Backend Degraded",
        disconnected: "Backend Disconnected",
    };

    return (
        <header className="app-header">
            <div>
                <h1>Data Pilot</h1>
                <p>Multi-Agent SQL Data Analyst</p>
            </div>
            <div className={`connection-status connection-status-${health}`} role="status" aria-live="polite">
                <span className="status-dot" />
                {statusLabels[health]}
            </div>
        </header>
    );
}

export default Header;
