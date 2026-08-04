const checks = [
  "Proxy same-origin hacia FastAPI",
  "Contratos HTTP centralizados y tipados",
  "Ejecución en un entorno demo controlado",
];

export default function HomePage() {
  return (
    <section className="foundation-page" aria-labelledby="foundation-title">
      <div className="eyebrow">Sprint 3 · Fundación web</div>
      <div className="hero-grid">
        <div>
          <h1 id="foundation-title">La base para convertir consultas en trabajo comercial trazable.</h1>
          <p className="lede">
            AdegaFlow AI prepara una experiencia asistida para analizar consultas,
            consultar contexto y dejar resultados listos para revisión humana.
          </p>
          <div className="notice" role="status">
            La fundación técnica está activa. Las pantallas del flujo comercial se
            incorporarán en los siguientes bloques aprobados.
          </div>
        </div>
        <aside className="check-card" aria-label="Comprobaciones de la fundación">
          <span className="card-label">Base verificada</span>
          <ul>
            {checks.map((check) => (
              <li key={check}><span aria-hidden="true">✓</span>{check}</li>
            ))}
          </ul>
          <a className="health-link" href="/api/health">Comprobar servicio API</a>
        </aside>
      </div>
    </section>
  );
}
