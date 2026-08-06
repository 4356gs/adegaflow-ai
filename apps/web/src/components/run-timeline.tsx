import type { PublicEvent } from "@/lib/api/types";
import {
  eventPresentation,
  formatRunTime,
  groupConsecutiveEvents,
} from "@/lib/run-observability";

function EventContext({ event }: { event: PublicEvent }) {
  const presentation = eventPresentation(event);
  if (presentation.tool) {
    return (
      <p className="event-context">
        <strong>Tool</strong> · {presentation.tool.label}
        {!presentation.tool.known ? <> <code>{presentation.tool.code}</code></> : null}
      </p>
    );
  }
  if (presentation.action) {
    return (
      <p className="event-context">
        <strong>Acción interna</strong> · {presentation.action.label}
        {!presentation.action.known ? <> <code>{presentation.action.code}</code></> : null}
      </p>
    );
  }
  return null;
}

export function RunTimeline({ events }: { events: PublicEvent[] }) {
  if (events.length === 0) {
    return (
      <section className="timeline-panel" aria-labelledby="timeline-title">
        <div className="section-heading">
          <div><p className="eyebrow">Actividad</p><h2 id="timeline-title">Timeline de ejecución</h2></div>
        </div>
        <p className="state-card">Todavía no hay actividad registrada. Esta vista se actualizará automáticamente.</p>
      </section>
    );
  }

  return (
    <section className="timeline-panel" aria-labelledby="timeline-title">
      <div className="section-heading">
        <div><p className="eyebrow">Actividad</p><h2 id="timeline-title">Timeline de ejecución</h2></div>
        <span className="muted">{events.length} {events.length === 1 ? "evento" : "eventos"}</span>
      </div>
      <ol className="timeline-groups">
        {groupConsecutiveEvents(events).map((group, groupIndex) => (
          <li className="timeline-group" key={`${group.step}-${group.events[0]?.sequence ?? groupIndex}`}>
            <div className="timeline-step-heading">
              <span className="timeline-marker" aria-hidden="true">{groupIndex + 1}</span>
              <div>
                <h3>{group.label}</h3>
                {!group.events.every((event) => event.step in KNOWN_STEPS) ? <code>{group.step}</code> : null}
              </div>
            </div>
            <ol className="timeline-events">
              {group.events.map((event) => {
                const presentation = eventPresentation(event);
                return (
                  <li className="timeline-event" key={event.sequence}>
                    <div className="event-heading">
                      <div>
                        <span className={`event-icon event-${presentation.category.toLowerCase().replaceAll(" ", "-")}`} aria-hidden="true">●</span>
                        <strong>{presentation.label}</strong>
                        <span className="event-category">{presentation.category}</span>
                      </div>
                      <time dateTime={event.created_at}>{formatRunTime(event.created_at)}</time>
                    </div>
                    <EventContext event={event} />
                    <details className="technical-details">
                      <summary>Detalles técnicos</summary>
                      <dl>
                        <div><dt>Tipo</dt><dd><code>{event.event_type}</code></dd></div>
                        <div><dt>Secuencia</dt><dd>{event.sequence}</dd></div>
                        {presentation.errorCode ? <div><dt>Código de error</dt><dd><code>{presentation.errorCode}</code></dd></div> : null}
                      </dl>
                    </details>
                  </li>
                );
              })}
            </ol>
          </li>
        ))}
      </ol>
    </section>
  );
}

const KNOWN_STEPS: Record<string, true> = {
  queued: true,
  analyzing: true,
  retrieving_memory: true,
  selecting_products: true,
  checking_stock: true,
  validating_recommendation: true,
  calculating_quote: true,
  generating_artifacts: true,
  persisting_actions: true,
  completed: true,
  needs_review: true,
  failed: true,
};
