function Header() {
    return (
        <header className="app-header">
            <div>
                <h1>Data Pilot</h1>
                <p>Multi-Agent SQL Data Analyst</p>
            </div>

            <div className="connection-status">
                <span className="status-dot"></span>
                Backend Connected
            </div>
        </header>
    );
}

export default Header;