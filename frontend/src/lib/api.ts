import type { A2UIEnvelope } from "../types/a2ui";
import { mockOverview, mockCategoryDetail } from "./mockAgent";

/**
 * Punto único de contacto con el agente. Hoy responde con datos
 * simulados (mismo contrato A2UIEnvelope que mandará el backend real);
 * cuando el contrato HTTP quede definido (tarea compartida "sh-1"), estas
 * dos funciones son las únicas que hay que reescribir — nada en
 * App.tsx ni en los componentes debería cambiar.
 */

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function sendMessage(_text: string, conversationId: string): Promise<A2UIEnvelope> {
  // TODO(backend): reemplazar por `fetch(POST /chat, {message: text, conversation_id})`
  await delay(300);
  return mockOverview(conversationId, "bar_chart");
}

/** Se llama una sola vez al abrir la app, sin que el usuario haya escrito
 * nada — muestra el resumen de una vez en vez de esperar una pregunta.
 * TODO(backend): reemplazar por el primer `GET/POST` que arranque la
 * conversación con el resumen por default del periodo actual. */
export async function loadDefaultOverview(conversationId: string): Promise<A2UIEnvelope> {
  await delay(300);
  return mockOverview(conversationId, "pie_chart");
}

export async function sendAction(
  conversationId: string,
  actionId: string,
  params?: Record<string, unknown>,
): Promise<A2UIEnvelope> {
  // TODO(backend): reemplazar por `fetch(POST /chat, {event:"action", conversation_id, action_id, params})`
  await delay(200);

  if (actionId === "view_category_detail" && typeof params?.category_id === "string") {
    return mockCategoryDetail(conversationId, params.category_id);
  }
  if (actionId === "back_to_overview") {
    return mockOverview(conversationId);
  }
  throw new Error(`Acción no soportada por el mock: ${actionId}`);
}

export function newConversationId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `conv_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}
