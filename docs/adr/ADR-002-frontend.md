# ADR-002: Frontend con Next.js y TypeScript

- **Estado:** Accepted for MVP
- **Fecha:** 2026-07-10
- **Decisores:** Equipo técnico AdegaFlow AI

## Contexto

La demo necesita una interfaz empresarial responsive y una visualización clara del flujo, no una ventana de chat aislada.

## Decisión

Usar Next.js con App Router, TypeScript y Tailwind CSS. Los componentes podrán apoyarse en shadcn/ui cuando reduzca tiempo sin imponer una capa de abstracción propia. El frontend consumirá `/api/v1` y actuará como proxy hacia FastAPI.

## Alternativas consideradas

- **React + Vite:** más ligero, pero requiere resolver proxy y despliegue por separado.
- **Streamlit/Gradio:** más rápidos, pero ofrecen menor control visual y narrativa empresarial.
- **Plantilla HTML simple:** insuficiente para estado y componentes del flujo.

## Consecuencias

**Positivas:** buena UX, tipado, ecosistema, despliegue en contenedor.  
**Negativas:** dos toolchains y mayor coste que Streamlit.  
**Riesgo:** dedicar demasiado tiempo al acabado visual.

## Condición de revisión

Revisar solo si Next.js bloquea el despliegue antes del Gate 3.
