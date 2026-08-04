import { RecentRuns } from "@/components/recent-runs";

export default function HomePage() {
  return (
    <section className="page-stack" aria-labelledby="cockpit-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Cockpit · Entorno demo</p>
          <h1 id="cockpit-title">Ejecuciones comerciales</h1>
          <p className="lede">Inicia una consulta y abre el trabajo reciente generado con datos de demostración.</p>
        </div>
        <a className="button button-primary" href="/inquiries/new">Nueva consulta</a>
      </div>
      <RecentRuns />
    </section>
  );
}
