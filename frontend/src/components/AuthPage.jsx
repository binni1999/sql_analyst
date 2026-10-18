import { useState } from "react";
import { login, signup } from "../services/auth";

function AuthPage({ onAuthenticated }) {
    const [mode, setMode] = useState("login");
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const isSignup = mode === "signup";

    async function handleSubmit(event) {
        event.preventDefault();
        if (busy) return;
        setBusy(true);
        setError("");
        try {
            const result = isSignup
                ? await signup({ name: name.trim(), email: email.trim(), password })
                : await login({ email: email.trim(), password });
            onAuthenticated(result.user);
        } catch (err) {
            setError(err.message || "Unable to authenticate. Please try again.");
        } finally {
            setBusy(false);
        }
    }

    return (
        <main className="auth-page">
            <section className="auth-card">
                <div className="auth-brand">
                    <img src="/datapilot.png" alt="DataPilot" />
                    <div><h1>Data Pilot</h1><p>Multi-Agent SQL Data Analyst</p></div>
                </div>
                <div className="auth-heading">
                    <h2>{isSignup ? "Create your account" : "Welcome back"}</h2>
                    <p>{isSignup ? "Sign up to start analyzing your data." : "Log in to continue to your workspace."}</p>
                </div>
                <form onSubmit={handleSubmit} className="auth-form">
                    {isSignup && (
                        <label>Full name
                            <input autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} maxLength={100} required />
                        </label>
                    )}
                    <label>Email address
                        <input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} maxLength={320} required />
                    </label>
                    <label>Password
                        <input type="password" autoComplete={isSignup ? "new-password" : "current-password"} value={password} onChange={(e) => setPassword(e.target.value)} minLength={isSignup ? 8 : 1} maxLength={128} required />
                    </label>
                    {isSignup && <p className="auth-hint">Use at least 8 characters, including a letter and a number.</p>}
                    {error && <div className="auth-error" role="alert">{error}</div>}
                    <button className="auth-submit" type="submit" disabled={busy}>
                        {busy ? "Please wait…" : isSignup ? "Create account" : "Log in"}
                    </button>
                </form>
                <p className="auth-switch">
                    {isSignup ? "Already have an account?" : "New to DataPilot?"}{" "}
                    <button type="button" onClick={() => { setMode(isSignup ? "login" : "signup"); setError(""); }}>
                        {isSignup ? "Log in" : "Create an account"}
                    </button>
                </p>
            </section>
        </main>
    );
}

export default AuthPage;
