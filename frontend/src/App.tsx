import { useEffect, useRef, useState } from "react";
import type { A2UIEnvelope } from "./types/a2ui";
import { ComponentRenderer } from "./components/registry";
import { BankChrome } from "./components/BankChrome";
import { loadDefaultOverview, newConversationId, sendAction, sendMessage, usingMock } from "./lib/api";

// Nombre del usuario demo — mismo que en los datos sintéticos de backend.
// Cuando exista sesión real, esto viene del backend.
const DEMO_USER_NAME = "Santiago";

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return `Buenos días, ${DEMO_USER_NAME}`;
  if (hour < 19) return `Buenas tardes, ${DEMO_USER_NAME}`;
  return `Buenas noches, ${DEMO_USER_NAME}`;
}

// Varias opciones de tono para el subtítulo del hero — sale una al azar
// cada vez que se abre la app en vez de repetir siempre la misma frase.
const HERO_SUBTITLES = [
  "Pregúntame en qué se te fue el dinero este mes.",
  "¿En qué se te fue el dinero? Vamos a verlo.",
  "Cuéntame qué te preocupa de tus gastos.",
  "Cualquier duda sobre tus gastos, aquí la resolvemos.",
  "Cuéntame qué quieres saber de tus gastos.",
];

function randomHeroSubtitle(): string {
  return HERO_SUBTITLES[Math.floor(Math.random() * HERO_SUBTITLES.length)];
}

function ChevronIcon({ up }: { up: boolean }) {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" fill="none" style={{ transform: up ? "rotate(180deg)" : "none" }}>
      <path d="M4 6.5 8 10.5 12 6.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SkeletonCard() {
  return (
    <div className="skeleton-card" aria-hidden="true">
      <div className="skeleton-line skeleton-line--sm" />
      <div className="skeleton-body">
        <div className="skeleton-circle" />
        <div className="skeleton-lines">
          <div className="skeleton-line" />
          <div className="skeleton-line" />
          <div className="skeleton-line" />
          <div className="skeleton-line" />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const conversationId = useRef(newConversationId());

  // Una sola pantalla activa a la vez: cada respuesta del agente la
  // REEMPLAZA (clic en categoría, "volver al resumen", nueva pregunta),
  // nunca se apila. `viewKey` solo sirve para retriggerear la animación
  // de entrada cuando cambia el contenido.
  const [heroSubtitle] = useState(randomHeroSubtitle);
  const [view, setView] = useState<A2UIEnvelope | null>(null);
  const [viewKey, setViewKey] = useState(0);
  const [lastQuestion, setLastQuestion] = useState<string | null>(null);
  // Preferencia del usuario, no del mensaje — se mantiene igual aunque
  // cambien las sugerencias con cada respuesta nueva.
  const [suggestionsExpanded, setSuggestionsExpanded] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  function showView(envelope: A2UIEnvelope) {
    setView(envelope);
    setViewKey((k) => k + 1);
    setError(null);
  }

  // Al abrir la app ya se ve el resumen (pie chart) sin tener que
  // preguntar nada primero.
  useEffect(() => {
    let cancelled = false;
    loadDefaultOverview(conversationId.current)
      .then((envelope) => {
        if (!cancelled) showView(envelope);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "No se pudo cargar el resumen.");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function ask(text: string) {
    if (!text || isLoading) return;
    setInput("");
    setLastQuestion(text);
    setIsLoading(true);
    setError(null);
    try {
      const envelope = await sendMessage(text, conversationId.current);
      showView(envelope);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo enviar la pregunta.");
      setInput(text); // no perder lo que ya había escrito si falla
    } finally {
      setIsLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    ask(input.trim());
  }

  async function handleAction(componentId: string, actionId: string, params?: Record<string, unknown>) {
    if (isLoading) return;
    setIsLoading(true);
    setError(null);
    try {
      const envelope = await sendAction(conversationId.current, componentId, actionId, params);
      showView(envelope);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }

  async function reloadOverview() {
    if (isLoading) return;
    setIsLoading(true);
    setError(null);
    try {
      showView(await loadDefaultOverview(conversationId.current));
      setLastQuestion(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar el resumen.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <BankChrome />

      <div className="sheet">
        <main className="screen">
          <div className="screen-inner">
            <div className="hero">
              <div className="hero-inner">
                <p className="hero-eyebrow">{greeting()}</p>
                <h1 className="hero-title">Entiende tus finanzas</h1>
                <p className="hero-subtitle">{heroSubtitle}</p>
              </div>
            </div>
            {usingMock && (
              <p className="demo-notice">Datos de ejemplo · prueba "barras", "resumen" o "despensa".</p>
            )}

            {lastQuestion && (
              <div className="chat-row chat-row--user">
                <div className="chat-bubble">{lastQuestion}</div>
              </div>
            )}

            {isLoading && <SkeletonCard />}

            {view && !isLoading && view.components.length > 0 && (
              <div key={viewKey} className="screen-content">
                {view.components.map((component) => (
                  <ComponentRenderer
                    key={component.id}
                    component={component}
                    onAction={(actionId, params) => handleAction(component.id, actionId, params)}
                  />
                ))}
              </div>
            )}

            {view && !isLoading && view.components.length === 0 && (
              <div className="unknown-card" role="status">
                No hay resultados para esta consulta.
                <button className="breakdown-action" onClick={reloadOverview}>
                  Volver al resumen
                </button>
              </div>
            )}

            {error && (
              <div className="screen-error" role="alert">
                {error}
                <button className="breakdown-action" onClick={reloadOverview} disabled={isLoading}>
                  Cargar resumen
                </button>
              </div>
            )}
          </div>
        </main>

        {view?.suggested_prompts && view.suggested_prompts.length > 0 && (
          <div className="suggestions">
            <button
              type="button"
              className="suggestions-toggle"
              onClick={() => setSuggestionsExpanded((v) => !v)}
              aria-expanded={suggestionsExpanded}
            >
              Preguntas sugeridas
              <ChevronIcon up={suggestionsExpanded} />
            </button>

            {suggestionsExpanded && (
              <div className="suggestions-inner">
                {view.suggested_prompts.map((prompt) => (
                  <button key={prompt} className="suggestion-chip" onClick={() => ask(prompt)} disabled={isLoading}>
                    {prompt}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <form className="chat-input" onSubmit={handleSubmit}>
          <div className="chat-input-inner">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Escribe tu pregunta…"
              disabled={isLoading}
            />
            <button type="submit" disabled={isLoading || !input.trim()}>
              Enviar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
