import { useRef, useState } from "react";
import type { A2UIEnvelope } from "./types/a2ui";
import { ComponentRenderer } from "./components/registry";
import { newConversationId, sendAction, sendMessage } from "./lib/api";

type Turn =
  | { kind: "user"; id: string; text: string }
  | { kind: "agent"; id: string; envelope: A2UIEnvelope }
  | { kind: "system"; id: string; text: string };

export default function App() {
  const conversationId = useRef(newConversationId());
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || isLoading) return;

    setInput("");
    setTurns((prev) => [...prev, { kind: "user", id: crypto.randomUUID(), text }]);
    setIsLoading(true);
    try {
      const envelope = await sendMessage(text, conversationId.current);
      setTurns((prev) => [...prev, { kind: "agent", id: crypto.randomUUID(), envelope }]);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleAction(actionId: string, params?: Record<string, unknown>) {
    if (isLoading) return;
    setIsLoading(true);
    try {
      const envelope = await sendAction(conversationId.current, actionId, params);
      setTurns((prev) => [...prev, { kind: "agent", id: crypto.randomUUID(), envelope }]);
    } catch (err) {
      setTurns((prev) => [
        ...prev,
        { kind: "system", id: crypto.randomUUID(), text: err instanceof Error ? err.message : String(err) },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="app-eyebrow">Banorte × Tec</span>
        <h1>Entender mis gastos</h1>
      </header>

      <main className="chat-log">
        {turns.length === 0 && (
          <div className="chat-empty">
            Pregunta algo como <em>"¿en qué se me fue el dinero este trimestre?"</em> para empezar.
          </div>
        )}

        {turns.map((turn) => {
          if (turn.kind === "user") {
            return (
              <div key={turn.id} className="chat-row chat-row--user">
                <div className="chat-bubble">{turn.text}</div>
              </div>
            );
          }
          if (turn.kind === "system") {
            return (
              <div key={turn.id} className="chat-row chat-row--system">
                {turn.text}
              </div>
            );
          }
          return (
            <div key={turn.id} className="chat-row chat-row--agent">
              {turn.envelope.components.map((component) => (
                <ComponentRenderer
                  key={component.id}
                  component={component}
                  onAction={(actionId, params) => handleAction(actionId, params)}
                />
              ))}
            </div>
          );
        })}

        {isLoading && <div className="chat-row chat-row--system">Pensando…</div>}
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
