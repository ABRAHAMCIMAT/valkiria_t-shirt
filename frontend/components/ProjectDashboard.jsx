import React from 'react';

const money = (value) => new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', maximumFractionDigits: 0 }).format(value || 0);

export default function ProjectDashboard({ analysis, onAnalyze, busy }) {
  if (!analysis) {
    return (
      <section className="panel empty-state">
        <div className="empty-icon">◫</div>
        <h2>Dashboard de estimación</h2>
        <p>Ejecuta los agentes para analizar épicas, cuestionario, costos y riesgos.</p>
        <button className="primary-btn" onClick={onAnalyze} disabled={busy}>{busy ? 'Analizando…' : 'Generar dashboard'}</button>
      </section>
    );
  }
  const summary = analysis.summary;
  return (
    <div className="dashboard-stack">
      <section className="kpi-grid">
        <article className="kpi"><span>Tiempo E2E</span><strong>{summary.total_weeks} semanas</strong><small>{summary.epics} épicas</small></article>
        <article className="kpi"><span>Costo estimado</span><strong>{money(summary.total_cost)}</strong><small>Roles + Cuestionario</small></article>
        <article className="kpi"><span>Complejidad</span><strong>{summary.complexity}</strong><small>Talla máxima</small></article>
        <article className="kpi"><span>MVPs</span><strong>{summary.mvp_count}</strong><small>{summary.effort_hours} horas</small></article>
      </section>

      <section className="panel">
        <div className="panel-title"><div><span className="eyebrow">EPIC BACKLOG</span><h2>Estimación por épica</h2></div><span className="badge">{analysis.epics.length} elementos</span></div>
        <div className="table-wrap"><table><thead><tr><th>Épica</th><th>MVP</th><th>Talla</th><th>Puntos</th><th>Semanas</th><th>Horas</th><th>Fuente</th></tr></thead>
          <tbody>{analysis.epics.map((epic) => <tr key={`${epic.row}-${epic.name}`}><td><strong>{epic.name}</strong></td><td>{epic.mvp}</td><td><span className={`size size-${epic.size}`}>{epic.size}</span></td><td>{epic.story_points}</td><td>{epic.weeks}</td><td>{epic.effort_hours}</td><td>{epic.estimation_source}</td></tr>)}</tbody>
        </table></div>
      </section>

      <section className="two-columns">
        <article className="panel"><span className="eyebrow">CUESTIONARIO</span><h2>Decisiones sugeridas</h2>
          <div className="decision-list">{analysis.questionnaire.slice(0, 8).map((item) => <div key={item.number}><span className="decision-number">{item.number}</span><div><strong>{item.topic || item.question}</strong><p>{item.size} · {money(item.cost)}</p></div></div>)}</div>
        </article>
        <article className="panel"><span className="eyebrow">CONTROL DE CALIDAD</span><h2>Revisión del agente</h2><p>{summary.executive_summary}</p>
          <ul className="warning-list">{analysis.review.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
          {analysis.review.llama_review && <div className="llama-review">{analysis.review.llama_review}</div>}
        </article>
      </section>
    </div>
  );
}
