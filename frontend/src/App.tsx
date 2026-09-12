import { useEffect, useRef, useState } from "react";
import type { A2UIEnvelope } from "./types/a2ui";
import { ComponentRenderer } from "./components/registry";
import { loadDefaultOverview, newConversationId, sendAction, sendMessage } from "./lib/api";

export default function App() {
  const conversationId = useRef(newConversationId());

  // Una sola pantalla activa a la vez: cada respuesta del agente la
  // REEMPLAZA (clic en categoría, "volver al resumen", nueva pregunta),
  // nunca se apila. `viewKey` solo sirve para retriggerear la animación
  // de entrada cuando cambia el contenido.
  const [view, setView] = useState<A2UIEnvelope | null>(null);
  const [viewKey, setViewKey] = useState(0);
  const [lastQuestion, setLastQuestion] = useState<string | null>(null);
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
    loadDefaultOverview(conversationId.current).then((envelope) => {
      if (!cancelled) {
        showView(envelope);
        setIsLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || isLoading) return;

    setInput("");
    setLastQuestion(text);
    setIsLoading(true);
    try {
      const envelope = await sendMessage(text, conversationId.current);
      showView(envelope);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleAction(actionId: string, params?: Record<string, unknown>) {
    if (isLoading) return;
    setIsLoading(true);
    try {
      const envelope = await sendAction(conversationId.current, actionId, params);
      showView(envelope);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <div className="app-topbar" />

      <header className="app-header">
        <div className="app-header-inner">
          <span className="brand">BANORTE</span>
          <h1>Entender mis gastos</h1>
        </div>
      </header>

      <main className="screen">
        <div className="screen-inner">
          {lastQuestion && (
            <div className="chat-row chat-row--user">
              <div className="chat-bubble">{lastQuestion}</div>
            </div>
          )}

          {isLoading && <div className="screen-loading">Pensando…</div>}

          {view && !isLoading && (
            <div key={viewKey} className="screen-content">
              {view.components.map((component) => (
                <ComponentRenderer
                  key={component.id}
                  component={component}
                  onAction={(actionId, params) => handleAction(actionId, params)}
                />
              ))}
            </div>
          )}

          {error && <div className="screen-error">{error}</div>}
        </div>
      </main>

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
  );
}
