import { useRef, useState } from "react";
import type { A2UIEnvelope } from "./types/a2ui";
import { ComponentRenderer } from "./components/registry";
import { newConversationId, sendAction, sendMessage } from "./lib/api";

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
  const [isLoading, setIsLoading] = useState(false);

  function showView(envelope: A2UIEnvelope) {
    setView(envelope);
    setViewKey((k) => k + 1);
    setError(null);
  }

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
        <span className="brand">BANORTE</span>
        <h1>Entender mis gastos</h1>
      </header>

      {lastQuestion && <div className="last-question">"{lastQuestion}"</div>}

      <main className="screen">
        {!view && !isLoading && (
          <div className="screen-empty">
            Pregunta algo como <em>"¿en qué se me fue el dinero este trimestre?"</em> para empezar.
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
      </main>

      <form className="chat-input" onSubmit={handleSubmit}>
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
      </form>
    </div>
  );
}
