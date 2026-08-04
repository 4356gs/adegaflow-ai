"use client";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <section className="narrow-page"><p className="eyebrow">Error</p><h1>No pudimos mostrar esta página</h1><p className="lede">Inténtalo de nuevo. Ninguna operación se reenviará desde esta pantalla.</p><button className="button button-primary" type="button" onClick={reset}>Volver a intentar</button></section>;
}
