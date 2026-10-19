import React, { useState } from 'react';

const blankRole = { name: '', area: '', required: true, collaborators: 1, cost_hourly: 0, source_cost: 0, source_basis: 'hora' };

export default function RolesEditor({ api, roles, onChange, onError }) {
  const [draft, setDraft] = useState(blankRole);
  const [editing, setEditing] = useState(null);

  const save = async (role, originalName = null) => {
    const response = await fetch(`${api}/roles${originalName ? `/${encodeURIComponent(originalName)}` : ''}`, {
      method: originalName ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(role),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'No fue posible guardar el rol');
    onChange(data.roles);
  };

  const add = async (event) => {
    event.preventDefault();
    try { await save(draft); setDraft(blankRole); } catch (err) { onError(err.message); }
  };

  return (
    <section className="panel">
      <div className="panel-title"><div><span className="eyebrow">MODELO DE COSTOS</span><h2>Roles y costo por hora</h2></div><span className="badge">{roles.length} roles</span></div>
      <p className="hint">Los costos unitarios del ejemplo se convierten a costo/hora usando 160 horas por mes. Edita la tarifa para recalcular futuras estimaciones.</p>
      <div className="table-wrap"><table><thead><tr><th>Rol</th><th>Área</th><th>Colaboradores</th><th>Costo/hora MXN</th><th /></tr></thead><tbody>
        {roles.map((role) => editing?.original === role.name ? (
          <tr key={role.name}><td><input value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} /></td><td><input value={editing.area} onChange={(e) => setEditing({ ...editing, area: e.target.value })} /></td><td><input type="number" min="0" value={editing.collaborators} onChange={(e) => setEditing({ ...editing, collaborators: Number(e.target.value) })} /></td><td><input type="number" min="0" value={editing.cost_hourly} onChange={(e) => setEditing({ ...editing, cost_hourly: Number(e.target.value) })} /></td><td><button className="link-btn" onClick={async () => { try { await save(editing, editing.original); setEditing(null); } catch (err) { onError(err.message); } }}>Guardar</button></td></tr>
        ) : (
          <tr key={role.name}><td><strong>{role.name}</strong></td><td>{role.area || '—'}</td><td>{role.collaborators}</td><td>${Number(role.cost_hourly).toFixed(2)}</td><td><button className="link-btn" onClick={() => setEditing({ ...role, original: role.name })}>Editar</button></td></tr>
        ))}
      </tbody></table></div>
      <form className="role-form" onSubmit={add}><h3>Agregar nuevo rol</h3><input required placeholder="Nombre del rol" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} /><input placeholder="Área" value={draft.area} onChange={(e) => setDraft({ ...draft, area: e.target.value })} /><input type="number" min="0" step="0.01" placeholder="Costo/hora" value={draft.cost_hourly} onChange={(e) => setDraft({ ...draft, cost_hourly: Number(e.target.value) })} /><button className="primary-btn">Agregar rol</button></form>
    </section>
  );
}
