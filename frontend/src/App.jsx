import { useState } from "react";

import { askDataAnalyst } from "./services/api";

import Header from "./components/Header";
import QueryInput from "./components/QueryInput";
import AnswerCard from "./components/AnswerCard";
import ResultTable from "./components/ResultTable";
import SQLViewer from "./components/SQLViewer";
import ExecutionTrace from "./components/ExecutionTrace";

import "./App.css";

function App() {
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAsk = async () => {
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) {
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const data = await askDataAnalyst(trimmedQuestion);
      setResponse(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <Header />

      <main className="app-main">
        <QueryInput
          question={question}
          setQuestion={setQuestion}
          onAsk={handleAsk}
          loading={loading}
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
          <section className="error-section">
            <h2>Request Failed</h2>
            <p>{error}</p>
          </section>
        )}

        {response && (
          <>
            <AnswerCard response={response} />

            <SQLViewer sql={response.sql} />

            <ResultTable result={response.result} />

            <ExecutionTrace
              executionTrace={response.execution_trace}
            />
          </>
        )}
      </main>
    </div>
  );
}

export default App;