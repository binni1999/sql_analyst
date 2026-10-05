const QUERY_EXAMPLES = [
    "Show the top 5 products by revenue",
    "Which customers placed the most orders?",
    "Show total revenue by product",
    "What are the top 10 products by quantity sold?",
];

function QueryInput({
    question,
    setQuestion,
    onAsk,
    loading,
}) {
    const handleKeyDown = (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            onAsk();
        }
    };

    const handleExampleClick = (example) => {
        setQuestion(example);
    };
    const loadingMessage = loading
        ? "Analyzing your data..."
        : null;

    return (
        <section className="query-section">
            <h2>Ask your data question</h2>

            <div className="query-box">
                <textarea
                    value={question}
                    onChange={(event) =>
                        setQuestion(event.target.value)
                    }
                    onKeyDown={handleKeyDown}
                    placeholder="Example: Show the top 5 products by revenue"
                    rows={4}
                    disabled={loading}
                />

                <button
                    type="button"
                    onClick={onAsk}
                    disabled={loading || !question.trim()}
                >
                    {loading ? "Analyzing..." : "Analyze"}
                </button>

                <div className="query-examples">
                    <span className="query-examples-label">
                        Try an example:
                    </span>

                    <div className="query-example-list">
                        {QUERY_EXAMPLES.map((example) => (
                            <button
                                key={example}
                                type="button"
                                className="query-example"
                                onClick={() => handleExampleClick(example)}
                                disabled={loading}
                            >
                                {example}
                            </button>
                        ))}
                    </div>
                </div>
            </div>
            {loadingMessage && (
                <div className="loading-card">
                    <div className="loading-spinner"></div>

                    <div>
                        <strong>{loadingMessage}</strong>
                        <p>
                            Processing your question and generating the analysis.
                        </p>
                    </div>
                </div>
            )}
        </section>
    );
}

export default QueryInput;