function getEventIcon(event) {
    if (event.status === "failed") {
        return "✕";
    }

    if (event.stage === "repair") {
        return "↻";
    }

    if (event.status === "started") {
        return "●";
    }

    return "✓";
}

function getEventClassName(event) {
    const classes = ["trace-event"];

    if (event.status === "failed") {
        classes.push("trace-event-failed");
    } else if (event.stage === "repair") {
        classes.push("trace-event-repair");
    } else if (event.status === "started") {
        classes.push("trace-event-started");
    } else if (event.status === "success") {
        classes.push("trace-event-success");
    }

    return classes.join(" ");
}

function getEventLabel(event) {
    if (event.stage === "repair") {
        return "Repair";
    }

    if (event.status === "failed") {
        return "Validation Failed";
    }

    if (event.status === "started") {
        return "Running";
    }

    return "Completed";
}

function ExecutionTrace({ executionTrace }) {
    if (!executionTrace || executionTrace.length === 0) {
        return null;
    }

    const totalDuration = executionTrace.reduce(
        (total, event) => {
            return total + (event.duration_ms || 0);
        },
        0
    );

    const repairEvents = executionTrace.filter(
        (event) =>
            event.stage === "repair" ||
            event.metadata?.repair_strategy
    ).length;

    const failedEvents = executionTrace.filter(
        (event) => event.status === "failed"
    ).length;

    return (
        <section className="trace-section">
            <h2>Agent Execution</h2>

            <div className="execution-summary">
                <div className="summary-item">
                    <span className="summary-label">
                        Events
                    </span>

                    <strong>{executionTrace.length}</strong>
                </div>

                <div className="summary-item">
                    <span className="summary-label">
                        Repairs
                    </span>

                    <strong>{repairEvents}</strong>
                </div>

                <div className="summary-item">
                    <span className="summary-label">
                        Failed Steps
                    </span>

                    <strong>{failedEvents}</strong>
                </div>

                <div className="summary-item">
                    <span className="summary-label">
                        Processing Time
                    </span>

                    <strong>
                        {totalDuration >= 1000
                            ? `${(totalDuration / 1000).toFixed(2)} s`
                            : `${totalDuration.toFixed(2)} ms`}
                    </strong>
                </div>
            </div>

            <div className="trace-list">
                {executionTrace.map((event, index) => (
                    <div
                        className={getEventClassName(event)}
                        key={`${event.stage}-${index}`}
                    >
                        <div className="trace-icon">
                            {getEventIcon(event)}
                        </div>

                        <div className="trace-event-content">
                            <div className="trace-event-header">
                                <div>
                                    <strong>{event.stage}</strong>

                                    <span className="trace-event-label">
                                        {getEventLabel(event)}
                                    </span>
                                </div>

                                {event.duration_ms !== undefined && (
                                    <span className="trace-duration">
                                        {event.duration_ms.toFixed(2)} ms
                                    </span>
                                )}
                            </div>

                            {event.message && (
                                <p>{event.message}</p>
                            )}

                            {event.error_type && (
                                <div className="trace-error-type">
                                    Error: {event.error_type}
                                </div>
                            )}

                            {event.metadata &&
                                Object.keys(event.metadata).length > 0 && (
                                    <details className="trace-metadata">
                                        <summary>
                                            View metadata
                                        </summary>

                                        <pre>
                                            {JSON.stringify(
                                                event.metadata,
                                                null,
                                                2
                                            )}
                                        </pre>
                                    </details>
                                )}
                        </div>
                    </div>
                ))}
            </div>
        </section>
    );
}

export default ExecutionTrace;