import { useEffect, useRef, useState } from "react";
import type { A2UIEnvelope } from "./types/a2ui";
import { ComponentRenderer } from "./components/registry";
import { BankChrome } from "./components/BankChrome";
import { loadDefaultOverview, newConversationId, sendAction, sendMessage, usingMock } from "./lib/api";

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
    }).catch((err: unknown) => {
      if (!cancelled) {
        setError(err instanceof Error ? err.message : 'No se pudo cargar el resumen.');
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
    setError(null);
    try {
      const envelope = await sendMessage(text, conversationId.current);
      showView(envelope);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo enviar la pregunta.');
      setInput(text);
    } finally {
      setIsLoading(false);
    }
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
      setError(err instanceof Error ? err.message : 'No se pudo cargar el resumen.');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <BankChrome />

      <main className="screen">
        <div className="screen-inner">
          <header className="page-intro">
            <p className="breadcrumb">Personal <span aria-hidden="true">/</span> Entender mis gastos</p>
            <div className="page-intro-row">
              <div>
                <p className="eyebrow">TU DINERO, MÁS CLARO</p>
                <h1>Entender mis gastos</h1>
                <p className="page-description">Una mirada a tus gastos para tomar mejores decisiones.</p>
              </div>
              <span className="intro-symbol" aria-hidden="true">
                <svg viewBox="0 0 48 48" fill="none"><path d="M10 35V25M24 35V16M38 35V7" stroke="currentColor" strokeWidth="5" strokeLinecap="round" /><path d="M6 43H43" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
              </span>
            </div>
          </header>
          {usingMock && <p className="demo-notice">Datos de ejemplo · Prueba “barras”, “resumen” o “despensa”.</p>}
          {lastQuestion && (
            <div className="chat-row chat-row--user">
              <div className="chat-bubble">{lastQuestion}</div>
            </div>
          )}

          {isLoading && <div className="screen-loading" role="status">Pensando…</div>}

          {view && !isLoading && (
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
              <button className="breakdown-action" onClick={reloadOverview}>Volver al resumen</button>
            </div>
          )}
          {error && <div className="screen-error" role="alert">
            {error}
            <button className="breakdown-action" onClick={reloadOverview} disabled={isLoading}>Cargar resumen</button>
          </div>}
        </div>
      </main>

      <form className="chat-input" onSubmit={handleSubmit}>
        <div className="chat-caption"><span className="assistant-mark" aria-hidden="true">✦</span> Consulta tus gastos <span className="chat-caption-detail">Escribe una pregunta y explora tu información</span></div>
        <div className="chat-input-inner">
          <input
            type="text"
            aria-label="Escribe tu pregunta"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Escribe tu pregunta…"
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading || !input.trim()}>
            Enviar <span aria-hidden="true">↗</span>
          </button>
        </div>
      </form>
    </div>
  );
}
