import React, { useState } from 'react';

export default function AgentChat({ api }) {
  const [message, setMessage] = useState('¿Cuáles son los principales riesgos y supuestos de esta estimación?');
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const send = async (event) => {
    event.preventDefault();
    if (!message.trim()) return;
    const question = message;
    setMessages((items) => [...items, { role: 'user', text: question }]);
    setMessage(''); setBusy(true);
    try {
      const response = await fetch(`${api}/agent/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: question }) });
      const data = await response.json();
      setMessages((items) => [...items, { role: 'agent', text: data.answer, sources: data.sources, offline: data.offline }]);
    } catch (_) {
      setMessages((items) => [...items, { role: 'agent', text: 'No fue posible conectar con el backend.' }]);
    } finally { setBusy(false); }
  };
  return <section className="panel chat-panel"><div className="panel-title"><div><span className="eyebrow">META LLAMA + RAG</span><h2>Agente conversacional</h2></div><span className="badge">Ollama</span></div>
    <div className="chat-history">{messages.length === 0 && <div className="chat-placeholder">Pregunta por costos, épicas, cuestionario, dependencias o riesgos.</div>}{messages.map((item, index) => <div className={`bubble ${item.role}`} key={index}><p>{item.text}</p>{item.sources?.length > 0 && <small>Fuentes: {item.sources.map((s) => `${s.sheet}:${s.row}`).join(', ')}</small>}</div>)}{busy && <div className="bubble agent">Analizando el contexto…</div>}</div>
    <form className="chat-form" onSubmit={send}><textarea value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Escribe una pregunta…" /><button className="primary-btn" disabled={busy}>Enviar</button></form>
  </section>;
}
