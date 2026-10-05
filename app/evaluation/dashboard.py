from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from evaluation.harness import EvaluationSummary


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _status(value: bool) -> str:
    return "PASS" if value else "FAIL"


def _result_status(result: Any) -> str:
    if result is None or not getattr(result, "evaluated", False):
        return "N/A"
    return _status(bool(getattr(result, "match", False)))


def _behavior_status(behavior: dict[str, Any] | None) -> str:
    if not behavior or not behavior.get("evaluated", False):
        return "N/A"
    return _status(bool(behavior.get("passed", False)))


def _case_rows(summary: EvaluationSummary) -> str:
    rows: list[str] = []
    for result in summary.results:
        rows.append(
            "<tr>"
            f"<td>{html.escape(result.case_id)}</td>"
            f"<td>{html.escape(_status(result.passed))}</td>"
            f"<td>{html.escape(_result_status(result.sql))}</td>"
            f"<td>{html.escape(_result_status(result.semantic))}</td>"
            f"<td>{html.escape(_result_status(result.answer))}</td>"
            f"<td>{html.escape(_behavior_status(result.behavior))}</td>"
            f"<td>{result.runtime.total_duration_ms or 0:.1f} ms</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _failure_details(summary: EvaluationSummary) -> str:
    sections: list[str] = []
    for result in summary.results:
        if result.passed:
            continue

        failures: list[str] = []
        for name, evaluation in (
            ("SQL", result.sql),
            ("Semantic", result.semantic),
            ("Answer", result.answer),
        ):
            if evaluation is not None and evaluation.evaluated and not evaluation.match:
                failures.append(f"{name}: {getattr(evaluation, 'reason', 'failed')}")

        behavior = result.behavior or {}
        if behavior.get("evaluated") and not behavior.get("passed", False):
            failures.append(
                "Behavior: "
                + "; ".join(str(item) for item in behavior.get("failures", []))
            )

        if result.runtime.errors:
            failures.extend(f"Runtime: {error}" for error in result.runtime.errors)

        if not failures:
            failures.append("Case did not satisfy the combined evaluation contract.")

        sections.append(
            '<details class="failure-card">'
            f"<summary><strong>{html.escape(result.case_id)}</strong></summary>"
            "<ul>"
            + "".join(f"<li>{html.escape(item)}</li>" for item in failures)
            + "</ul>"
            "</details>"
        )
    return "\n".join(sections) or '<p class="muted">No failed cases.</p>'


def _trace_details(summary: EvaluationSummary) -> str:
    sections: list[str] = []
    for result in summary.results:
        trace = result.runtime.execution_trace
        if not trace:
            continue
        trace_json = html.escape(json.dumps(trace, indent=2, default=str))
        sections.append(
            '<details class="trace-card">'
            f"<summary>{html.escape(result.case_id)} — execution trace</summary>"
            f"<pre>{trace_json}</pre>"
            "</details>"
        )
    return "\n".join(sections) or '<p class="muted">No execution traces captured.</p>'


def render_evaluation_dashboard(summary: EvaluationSummary) -> str:
    """Render a self-contained HTML dashboard from an evaluation summary."""

    data = summary.model_dump(mode="json")
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SQL Analyst Evaluation Dashboard</title>
<style>
:root {{ color-scheme: light; --border:#d9dee7; --muted:#667085; --bg:#f6f8fb; --card:#fff; --text:#182230; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:var(--bg); color:var(--text); }}
.container {{ max-width:1280px; margin:0 auto; padding:32px 20px 48px; }}
h1 {{ margin:0 0 6px; font-size:30px; }}
.subtitle {{ color:var(--muted); margin:0 0 24px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:14px; margin-bottom:24px; }}
.card {{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:18px; box-shadow:0 1px 2px rgba(16,24,40,.04); }}
.metric-label {{ color:var(--muted); font-size:13px; }}
.metric-value {{ font-size:27px; font-weight:700; margin-top:7px; }}
.section {{ margin-top:24px; }}
.section h2 {{ font-size:20px; margin:0 0 12px; }}
.table-wrap {{ overflow:auto; background:var(--card); border:1px solid var(--border); border-radius:12px; }}
table {{ width:100%; border-collapse:collapse; min-width:780px; }}
th,td {{ padding:11px 13px; border-bottom:1px solid var(--border); text-align:left; font-size:14px; }}
th {{ background:#f9fafb; color:#475467; font-weight:600; }}
.badge {{ display:inline-block; padding:3px 8px; border-radius:999px; font-size:12px; font-weight:700; }}
button {{ border:1px solid var(--border); background:#fff; border-radius:8px; padding:8px 12px; cursor:pointer; margin-right:7px; }}
button.active {{ background:#182230; color:#fff; }}
.controls {{ margin:0 0 12px; }}
.failure-card,.trace-card {{ background:var(--card); border:1px solid var(--border); border-radius:10px; padding:12px 14px; margin:8px 0; }}
pre {{ overflow:auto; background:#111827; color:#e5e7eb; padding:14px; border-radius:8px; font-size:12px; }}
.muted {{ color:var(--muted); }}
.pass {{ color:#067647; }} .fail {{ color:#b42318; }} .na {{ color:#667085; }}
footer {{ color:var(--muted); font-size:12px; margin-top:28px; }}
</style>
</head>
<body>
<div class="container">
  <h1>Multi-Agent SQL Analyst — Evaluation Dashboard</h1>
  <p class="subtitle">Dataset: <strong>{html.escape(summary.dataset_id)}</strong> · Version {html.escape(summary.dataset_version)}</p>

  <div class="grid">
    <div class="card"><div class="metric-label">Overall accuracy</div><div class="metric-value">{_pct(summary.accuracy)}</div></div>
    <div class="card"><div class="metric-label">Passed cases</div><div class="metric-value">{summary.passed_cases}/{summary.evaluated_cases}</div></div>
    <div class="card"><div class="metric-label">SQL accuracy</div><div class="metric-value">{_pct(summary.sql_accuracy)}</div></div>
    <div class="card"><div class="metric-label">Semantic accuracy</div><div class="metric-value">{_pct(summary.semantic_accuracy)}</div></div>
    <div class="card"><div class="metric-label">Answer accuracy</div><div class="metric-value">{_pct(summary.answer_accuracy)}</div></div>
    <div class="card"><div class="metric-label">Behavior accuracy</div><div class="metric-value">{_pct(summary.behavior_accuracy)}</div></div>
    <div class="card"><div class="metric-label">Total duration</div><div class="metric-value">{summary.total_duration_ms:.1f} ms</div></div>
  </div>

  <section class="section">
    <h2>Case results</h2>
    <div class="controls">
      <button class="active" data-filter="all">All</button>
      <button data-filter="failed">Failed</button>
      <button data-filter="passed">Passed</button>
    </div>
    <div class="table-wrap">
      <table id="case-table">
        <thead><tr><th>Case</th><th>Overall</th><th>SQL</th><th>Semantic</th><th>Answer</th><th>Behavior</th><th>Duration</th></tr></thead>
        <tbody>{_case_rows(summary)}</tbody>
      </table>
    </div>
  </section>

  <section class="section">
    <h2>Failure analysis</h2>
    {_failure_details(summary)}
  </section>

  <section class="section">
    <h2>Execution traces</h2>
    {_trace_details(summary)}
  </section>

  <footer>Generated from the evaluation harness. Metrics are based only on cases actually evaluated; unevaluated dimensions are shown as N/A at case level.</footer>
</div>
<script>
const rows = [...document.querySelectorAll('#case-table tbody tr')];
const buttons = [...document.querySelectorAll('button[data-filter]')];
buttons.forEach(button => button.addEventListener('click', () => {{
  buttons.forEach(item => item.classList.remove('active'));
  button.classList.add('active');
  const filter = button.dataset.filter;
  rows.forEach(row => {{
    const overall = row.children[1].textContent.trim();
    row.style.display = filter === 'all' || (filter === 'passed' && overall === 'PASS') || (filter === 'failed' && overall === 'FAIL') ? '' : 'none';
  }});
}}));
window.__evaluationData = {data_json};
</script>
</body>
</html>"""


def save_evaluation_dashboard(
    summary: EvaluationSummary,
    output_path: str | Path,
) -> Path:
    """Write the self-contained dashboard HTML and return its path."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_evaluation_dashboard(summary), encoding="utf-8")
    return path
