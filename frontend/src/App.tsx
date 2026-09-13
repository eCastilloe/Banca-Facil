import { useEffect, useRef, useState } from "react";
import type { A2UIEnvelope } from "./types/a2ui";
import { ComponentRenderer } from "./components/registry";
import { BankChrome } from "./components/BankChrome";
import { loadDefaultOverview, newConversationId, sendAction, sendMessage, usingMock } from "./lib/api";

// Placeholder mientras no exista sesión real -- el backend no tiene ningún
// concepto de usuario nombrado (los datos sintéticos no traen nombre), así
// que este valor no debe leerse como un dato real. Cuando exista sesión de
// verdad, esto viene del backend.
const DEMO_USER_NAME = "Usuario";

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

type ChatEntry = { id: number; role: "user"; text: string } | { id: number; role: "assistant"; envelope: A2UIEnvelope };

export default function App() {
  const conversationId = useRef(newConversationId());

  const [heroSubtitle] = useState(randomHeroSubtitle);
  const [view, setView] = useState<A2UIEnvelope | null>(null);
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const nextMessageId = useRef(0);
  const latestMessage = useRef<HTMLDivElement>(null);
  // Preferencia del usuario, no del mensaje — se mantiene igual aunque
  // cambien las sugerencias con cada respuesta nueva.
  const [suggestionsExpanded, setSuggestionsExpanded] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (messages.length > 1 || isLoading) {
      latestMessage.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [messages, isLoading]);

  function showView(envelope: A2UIEnvelope) {
    setView(envelope);
    const id = nextMessageId.current++;
    setMessages((previous) => [...previous, { id, role: "assistant", envelope }]);
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
    const id = nextMessageId.current++;
    setMessages((previous) => [...previous, { id, role: "user", text }]);
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
                <h1 className="hero-title">Hablemos de tu dinero<span className="hero-spark"> ✦</span></h1>
                <p className="hero-subtitle">{heroSubtitle}</p>
              </div>
            </div>
            {usingMock && (
              <p className="demo-notice">Datos de ejemplo · prueba "barras", "resumen" o "despensa".</p>
            )}

            <div className="conversation-divider"><span>Tu espacio para hablar de dinero</span></div>
            <div className="chat-timeline" role="log" aria-label="Conversación">
              {messages.map((entry, index) => (
                <div key={entry.id} ref={index === messages.length - 1 ? latestMessage : undefined}
                  className={`chat-entry chat-entry--${entry.role}`}>
                  {entry.role === "user" ? (
                    <div className="chat-row chat-row--user">
                      <div className="message-stack"><span className="message-author">Tú</span>
                        <div className="chat-bubble">{entry.text}</div>
                      </div>
                    </div>
                  ) : (
                    <div className="assistant-message">
                      <div className="assistant-avatar" aria-hidden="true">✦</div>
                      <div className="assistant-body">
                        <span className="message-author">Banca Fácil <span className="assistant-tag">Tu asistente</span></span>
                        <div className="screen-content">
                          {entry.envelope.components.map((component) => (
                            <ComponentRenderer key={component.id} component={component}
                              onAction={(actionId, params) => handleAction(component.id, actionId, params)} />
                          ))}
                          {entry.envelope.components.length === 0 && <div className="text-block">No encontré resultados para esta consulta.</div>}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
            {isLoading && <div className="typing-indicator" role="status"><span /><span /><span /><p>Revisando tus números</p></div>}

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
              aria-label="Tu mensaje"
              placeholder="¿Qué tienes en mente?"
              disabled={isLoading}
            />
            <button type="submit" disabled={isLoading || !input.trim()}>
              Enviar <span aria-hidden="true">↗</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
