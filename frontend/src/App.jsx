import { useEffect, useState } from "react";

import { askDataAnalyst } from "./services/api";
import { getCurrentUser, logout } from "./services/auth";
import AuthPage from "./components/AuthPage";

import Header from "./components/Header";
import QueryInput from "./components/QueryInput";
import AnswerCard from "./components/AnswerCard";
import ResultTable from "./components/ResultTable";
import SQLViewer from "./components/SQLViewer";
import ExecutionTrace from "./components/ExecutionTrace";

import "./App.css";

const ERROR_COPY = {
  LLM_PROVIDER_UNAVAILABLE: { title: "Our analysis service is temporarily unavailable", message: "Please try again in a moment. If this keeps happening, contact support.", retryable: true },
  SQL_GENERATION_FAILED: { title: "We couldn't build a query for that question", message: "Try rephrasing your question or using a supported table or column name.", retryable: false },
  SCHEMA_VALIDATION_FAILED: { title: "We couldn't find that table or column", message: "Check the name against your database schema, then try again.", retryable: false },
  REQUEST_BLOCKED: { title: "This request couldn't be completed", message: "The request doesn't meet the current data-access or security policy.", retryable: false },
  NETWORK_ERROR: { title: "Couldn't connect to DataPilot", message: "Check that the backend is running and your connection is available.", retryable: true },
  SERVER_ERROR: { title: "DataPilot is having trouble", message: "A temporary server error occurred. Please try again shortly.", retryable: true },
  INVALID_RESPONSE: { title: "We received an unexpected response", message: "Please try again. If the issue continues, contact support.", retryable: true },
  ANALYSIS_FAILED: { title: "We couldn't complete your analysis", message: "Please try again or rephrase your question.", retryable: true },
};

function getErrorDetails(error, fallbackCode = "ANALYSIS_FAILED") {
  const code = error?.error_code || error?.code || fallbackCode;
  const known = ERROR_COPY[code] || ERROR_COPY.ANALYSIS_FAILED;
  return {
    code,
    title: known.title,
    message: known.message,
    retryable: known.retryable,
    reference: error?.error_reference || error?.reference || null,
  };
}

function App() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastQuestion, setLastQuestion] = useState("");
  const [approvalModalOpen, setApprovalModalOpen] = useState(false);

  useEffect(() => {
    let active = true;
    getCurrentUser()
      .then(({ user: current }) => { if (active) setUser(current); })
      .catch(() => { if (active) setUser(null); })
      .finally(() => { if (active) setAuthLoading(false); });
    return () => { active = false; };
  }, []);

  const handleLogout = async () => {
    try { await logout(); } catch { /* Clear the local view even if the session has expired. */ }
    setUser(null);
    setQuestion("");
    setResponse(null);
    setConversationId(null);
    setError(null);
    setLastQuestion("");
    setApprovalModalOpen(false);
  };

  useEffect(() => {
    if (!approvalModalOpen) return undefined;
    const handleKeyDown = (event) => {
      if (event.key === "Escape" && !loading) setApprovalModalOpen(false);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [approvalModalOpen, loading]);

  if (authLoading) {
    return <main className="auth-loading" role="status">Loading your DataPilot workspace…</main>;
  }
  if (!user) {
    return <AuthPage onAuthenticated={setUser} />;
  }

  const applyResponse = (data) => {
    setResponse(data);
    if (data.conversation_id) {
      setConversationId(data.conversation_id);
    }

    setApprovalModalOpen(Boolean(data.needs_human_approval));

    if (data.success === false) {
      setError(getErrorDetails(data));
      setResponse({ ...data, answer: null, result: null, sql: null, execution_trace: [] });
    } else {
      setError(null);
    }
  };

  const handleAsk = async (questionOverride = null) => {
    const trimmedQuestion = String(questionOverride ?? question).trim();

    if (!trimmedQuestion || loading || response?.needs_human_approval) {
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);
    setLastQuestion(trimmedQuestion);
    setApprovalModalOpen(false);

    try {
      const data = await askDataAnalyst(trimmedQuestion, conversationId);
      applyResponse(data);
    } catch (err) {
      setResponse(null);
      setError(getErrorDetails(err));
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = () => {
    if (error?.retryable && lastQuestion && !loading) {
      setQuestion(lastQuestion);
      handleAsk(lastQuestion);
    }
  };

  const handleApproval = async (approved) => {
    if (!conversationId || loading || !response?.needs_human_approval) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await askDataAnalyst(
        approved ? "Approve" : "Reject",
        conversationId,
        approved,
      );
      applyResponse(data);
    } catch (err) {
      setError(getErrorDetails(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <Header user={user} onLogout={handleLogout} />

      <main className="app-main">
        <QueryInput
          question={question}
          setQuestion={setQuestion}
          onAsk={handleAsk}
          loading={loading || Boolean(response?.needs_human_approval)}
        />

        {!response && !error && !loading && (
          <section className="empty-state">
            <div className="empty-state-icon">✦</div>

            <h2>Ask your data anything</h2>

            <p>
              Query your database using natural language and let
              Data Pilot generate, validate, and execute the SQL
              for you.
            </p>

            <div className="empty-state-features">
              <div className="empty-state-feature">
                <strong>Natural Language</strong>
                <span>Ask questions in plain English</span>
              </div>

              <div className="empty-state-feature">
                <strong>SQL Validation</strong>
                <span>Generated SQL is validated before execution</span>
              </div>

              <div className="empty-state-feature">
                <strong>Agentic Analysis</strong>
                <span>Multiple agents collaborate on your question</span>
              </div>
            </div>
          </section>
        )}

        {error && (
          <section className="error-section" role="alert" aria-live="polite">
            <div className="error-icon" aria-hidden="true">!</div>
            <div className="error-content">
              <h2>{error.title}</h2>
              <p>{error.message}</p>
              {error.reference && <p className="error-reference">Reference: {error.reference}</p>}
              <div className="error-actions">
                {error.retryable && lastQuestion && (
                  <button type="button" className="error-retry-button" onClick={handleRetry} disabled={loading}>
                    {loading ? "Trying again…" : "Try again"}
                  </button>
                )}
                <button type="button" className="error-secondary-button" onClick={() => { setError(null); setResponse(null); }}>
                  Dismiss
                </button>
              </div>
            </div>
          </section>
        )}

        {response?.success === true && !response.needs_human_approval && (
          <>
            <AnswerCard response={response} />
            <SQLViewer sql={response.sql} />
            <ResultTable result={response.result} />
            <ExecutionTrace executionTrace={response.execution_trace} />
          </>
        )}

        {approvalModalOpen && response?.needs_human_approval && (
          <div className="approval-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !loading) setApprovalModalOpen(false); }}>
            <section
              className="approval-modal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="approval-heading"
              aria-describedby="approval-description"
            >
              <div className="approval-modal-header">
                <div>
                  <h2 id="approval-heading">Human approval required</h2>
                  <p id="approval-description">
                    {response.human_approval_question ||
                      "Review the generated SQL and risk assessment before allowing execution."}
                  </p>
                </div>
                <span className="approval-modal-icon" aria-hidden="true">!</span>
              </div>

              {response.risk_assessment?.risk_level && (
                <p className="approval-risk">
                  Risk level: <strong>{response.risk_assessment.risk_level}</strong>
                </p>
              )}

              {Array.isArray(response.risk_assessment?.reasons) &&
                response.risk_assessment.reasons.length > 0 && (
                  <ul className="approval-reasons">
                    {response.risk_assessment.reasons.map((reason, index) => (
                      <li key={`${reason}-${index}`}>{reason}</li>
                    ))}
                  </ul>
                )}

              <div className="approval-modal-sql">
                <SQLViewer sql={response.sql} />
              </div>

              <div className="approval-actions">
                <button
                  type="button"
                  className="approval-button approval-button-approve"
                  onClick={() => handleApproval(true)}
                  disabled={loading}
                >
                  {loading ? "Processing..." : "Approve & Execute"}
                </button>
                <button
                  type="button"
                  className="approval-button approval-button-reject"
                  onClick={() => handleApproval(false)}
                  disabled={loading}
                >
                  {loading ? "Processing..." : "Reject"}
                </button>
              </div>

              <p className="approval-note">
                Approval resumes this conversation. Review the generated SQL before proceeding.
              </p>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
