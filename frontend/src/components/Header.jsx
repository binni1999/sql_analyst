import { useEffect, useState } from "react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

function Header({ user, onLogout }) {
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
            <div className="brand">
                <img
                    src="/datapilot.png"
                    alt="DataPilot"
                    className="brand-logo"
                />
                <div>
                    <h1>Data Pilot</h1>
                    <p>Multi-Agent SQL Data Analyst</p>
                </div>
            </div>

            <div className="header-actions">
                <div className="header-user" title={user?.email}>{user?.name || user?.email}</div>
                <div
                    className={`connection-status connection-status-${health}`}
                    role="status"
                    aria-live="polite"
                >
                    <span className="status-dot" />
                    {statusLabels[health]}
                </div>
                <button type="button" className="logout-button" onClick={onLogout}>Log out</button>
            </div>
        </header>
    );

}

export default Header;
