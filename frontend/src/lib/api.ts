import type { A2UIEnvelope } from '../types/a2ui';
import { mockOverview, mockCategoryDetail, mockMessage } from './mockAgent';
import { parseEnvelope } from './parseEnvelope';

const endpoint = import.meta.env.VITE_A2UI_ENDPOINT?.trim();
export const usingMock = !endpoint;

async function request(conversationId: string, payload: Record<string, unknown>, mock: () => A2UIEnvelope): Promise<A2UIEnvelope> {
  if (!endpoint) {
    await new Promise(resolve => setTimeout(resolve, 300));
    return parseEnvelope(JSON.stringify(mock()), conversationId);
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...payload, conversation_id: conversationId }),
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`El servidor respondió con un error (${response.status}).`);
    return parseEnvelope(await response.text(), conversationId);
  } catch (error) {
    if (controller.signal.aborted) throw new Error('El servidor tardó demasiado. Intenta nuevamente.');
    if (error instanceof TypeError) throw new Error('No se pudo conectar con el servidor. Revisa tu conexión.');
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export function sendMessage(text: string, conversationId: string): Promise<A2UIEnvelope> {
  return request(conversationId, { event: 'message', message: text }, () => mockMessage(conversationId, text));
}

export function loadDefaultOverview(conversationId: string): Promise<A2UIEnvelope> {
  return request(conversationId, { event: 'overview' }, () => mockOverview(conversationId));
}

export function sendAction(conversationId: string, componentId: string, actionId: string, params?: Record<string, unknown>): Promise<A2UIEnvelope> {
  return request(conversationId, { event: 'action', component_id: componentId, action_id: actionId, params }, () => {
    if (actionId === 'view_category_detail' && typeof params?.category_id === 'string') {
      return mockCategoryDetail(conversationId, params.category_id);
    }
    if (actionId === 'back_to_overview') return mockOverview(conversationId);
    throw new Error(`Acción no soportada por el mock: ${actionId}`);
  });
}

export function newConversationId(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `conv_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}
