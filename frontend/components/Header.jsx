import React from 'react';

export default function Header() {
  return (
    <header className="header-banner">
      <div className="header-inner">
        <div className="brand-mark">PM</div>
        <div>
          <h1>Modelo de Predicción PM</h1>
          <p>ML Ensemble · RAG Excel · Meta Llama · Ollama</p>
        </div>
        <span className="local-pill">Privado y local</span>
      </div>
    </header>
  );
}
