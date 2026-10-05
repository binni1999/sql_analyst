import { useState } from "react";

function SQLViewer({ sql }) {
    const [copied, setCopied] = useState(false);

    if (!sql) {
        return null;
    }

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(sql);

            setCopied(true);

            setTimeout(() => {
                setCopied(false);
            }, 2000);
        } catch {
            setCopied(false);
        }
    };

    return (
        <section className="sql-section">
            <div className="section-header">
                <h2>Generated SQL</h2>

                <button
                    type="button"
                    className="copy-button"
                    onClick={handleCopy}
                >
                    {copied ? "Copied ✓" : "Copy SQL"}
                </button>
            </div>

            <pre>
                <code>{sql}</code>
            </pre>
        </section>
    );
}

export default SQLViewer;