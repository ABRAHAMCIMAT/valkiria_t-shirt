import React, { useEffect, useState } from 'react';
import Header from '../components/Header';
import ExcelUpload from '../components/ExcelUpload';
import ProjectDashboard from '../components/ProjectDashboard';
import RolesEditor from '../components/RolesEditor';
import AgentChat from '../components/AgentChat';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Home() {
  const [tab, setTab] = useState('dashboard');
  const [status, setStatus] = useState(null);
  const [roles, setRoles] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const jsonRequest = async (path, options = {}) => {
    const response = await fetch(`${API}${path}`, options);
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || 'No fue posible completar la operación');
    }
    return response.json();
  };

  const refreshRoles = async () => {
    const data = await jsonRequest('/roles');
    setRoles(data.roles || []);
  };

  useEffect(() => {
    Promise.all([jsonRequest('/knowledge/status'), jsonRequest('/roles')])
      .then(([knowledge, roleData]) => {
        setStatus(knowledge);
        setRoles(roleData.roles || []);
      })
      .catch(() => {});
  }, []);

  const upload = async (file) => {
    setBusy(true);
    setError('');
    try {
      const form = new FormData();
      form.append('file', file);
      const data = await jsonRequest('/knowledge/upload', { method: 'POST', body: form });
      setStatus({ loaded: true, chunks: data.chunks, template: true });
      setAnalysis(null);
      await refreshRoles();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const analyze = async () => {
    setBusy(true);
    setError('');
    try {
      setAnalysis(await jsonRequest('/project/analyze', { method: 'POST' }));
      setTab('dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const exportExcel = async () => {
    setError('');
    const response = await fetch(`${API}/export/excel`, { method: 'POST' });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      setError(data.detail || 'No fue posible exportar');
      return;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'estimacion_epicas_completa.xlsx';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="page-container">
      <Header />
      <main className="main-content">
        <section className="workspace-bar">
          <div>
            <span className={`status-dot ${status?.loaded ? 'ready' : ''}`} />
            {status?.loaded ? `RAG listo · ${status.chunks} fragmentos` : 'Carga el template T-Shirt'}
          </div>
          <div className="workspace-actions">
            <button className="secondary-btn" onClick={() => document.getElementById('upload-panel')?.scrollIntoView()}>Cambiar Excel</button>
            <button className="primary-btn" disabled={busy || !status?.loaded} onClick={analyze}>
              {busy ? 'Procesando…' : 'Ejecutar multiagente'}
            </button>
            <button className="dark-btn" disabled={!analysis} onClick={exportExcel}>Exportar Excel completo</button>
          </div>
        </section>

        {error && <div className="error-message">{error}</div>}

        <nav className="tabs">
          {[
            ['dashboard', 'Dashboard'],
            ['roles', 'Roles y costos'],
            ['chat', 'Agente conversacional'],
            ['knowledge', 'Base de conocimiento'],
          ].map(([id, label]) => (
            <button key={id} className={tab === id ? 'active' : ''} onClick={() => setTab(id)}>{label}</button>
          ))}
        </nav>

        {tab === 'dashboard' && <ProjectDashboard analysis={analysis} onAnalyze={analyze} busy={busy} />}
        {tab === 'roles' && <RolesEditor api={API} roles={roles} onChange={setRoles} onError={setError} />}
        {tab === 'chat' && <AgentChat api={API} />}
        {tab === 'knowledge' && (
          <section id="upload-panel" className="panel compact-upload">
            <ExcelUpload onUpload={upload} loading={busy} />
            <p className="hint">Se indexan todas las pestañas. Roles, Cuestionario, Epic Backlog y Resultado se interpretan de forma estructurada.</p>
          </section>
        )}
      </main>
    </div>
  );
}
