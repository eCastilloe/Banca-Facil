import type { A2UIEnvelope } from "../types/a2ui";
import { mockOverview, mockCategoryDetail, mockTopCategoryDetail, mockAllTransactions } from "./mockAgent";

/** Preguntas de arranque rápido — bajan la fricción de la pantalla en
 * blanco y, de paso, muestran la variedad de intenciones que el agente
 * puede resolver dentro de "entender gastos". Cada una mapea a una
 * respuesta distinta del mock (ver sendMessage). */
export const SUGGESTED_PROMPTS = [
  "¿En qué se me fue el dinero este trimestre?",
  "¿En qué categoría gasté más?",
  "Ver todas mis transacciones",
];

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

export async function sendMessage(text: string, conversationId: string): Promise<A2UIEnvelope> {
  // TODO(backend): reemplazar por `fetch(POST /chat, {message: text, conversation_id})`.
  // Esta clasificación por palabras clave es puro relleno del mock — el
  // LLM real interpretaría la intención de verdad, no haría un match de texto.
  await delay(300);
  const q = text.toLowerCase();

  if (q.includes("más") || q.includes("mayor") || q.includes("mas gast")) {
    return mockTopCategoryDetail(conversationId);
  }
  if (q.includes("todas") || q.includes("transacciones") || q.includes("movimientos")) {
    return mockAllTransactions(conversationId);
  }
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
