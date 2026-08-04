import type { Metadata } from "next";

import { InquiryForm } from "@/components/inquiry-form";

export const metadata: Metadata = { title: "Nueva consulta" };

export default function NewInquiryPage() {
  return <section className="narrow-page" aria-labelledby="new-inquiry-title"><p className="eyebrow">Nueva ejecución</p><h1 id="new-inquiry-title">Crear una consulta</h1><p className="lede">Introduce una necesidad comercial o carga la entrada canónica del escenario UC-001.</p><InquiryForm /></section>;
}
