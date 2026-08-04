import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "AdegaFlow AI",
    template: "%s · AdegaFlow AI",
  },
  description: "Flujo comercial asistido por IA para bodegas gallegas.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="es">
      <body>
        <a className="skip-link" href="#main-content">
          Saltar al contenido
        </a>
        <header className="site-header">
          <div className="header-inner">
            <Link className="brand" href="/" aria-label="AdegaFlow AI, inicio">
              <span className="brand-mark" aria-hidden="true">AF</span>
              <span>AdegaFlow AI</span>
            </Link>
            <nav aria-label="Navegación principal">
              <Link href="/" aria-current="page">Inicio</Link>
            </nav>
            <span className="demo-badge">Entorno demo</span>
          </div>
        </header>
        <main id="main-content">{children}</main>
        <footer className="site-footer">
          Datos ficticios · Ninguna acción externa se ejecuta sin revisión humana
        </footer>
      </body>
    </html>
  );
}
