import type { A2UIEnvelope } from '../types/a2ui';

const object = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);
const text = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0;

/** Validate both mock and HTTP JSON at the reception boundary. */
export function parseEnvelope(input: unknown, conversationId: string): A2UIEnvelope {
  let data: unknown = input;
  if (typeof input === 'string') {
    try { data = JSON.parse(input); }
    catch { throw new Error('La respuesta no contiene JSON válido.'); }
  }
  if (!object(data) || data.version !== '1.0' || !text(data.intent)
    || data.conversation_id !== conversationId || !Array.isArray(data.components)) {
    throw new Error('La respuesta no cumple el contrato A2UI 1.0 de esta conversación.');
  }
  const ids = new Set<string>();
  for (const component of data.components) {
    if (!object(component) || !text(component.id) || !text(component.type) || !object(component.props)
      || ids.has(component.id)) throw new Error('La respuesta contiene componentes inválidos o IDs repetidos.');
    ids.add(component.id);
    if (component.actions !== undefined && (!Array.isArray(component.actions)
      || !component.actions.every(action => object(action) && text(action.id)
        && (action.label === undefined || typeof action.label === 'string')
        && (action.trigger === undefined || typeof action.trigger === 'string')))) {
      throw new Error('La respuesta contiene acciones inválidas.');
    }
  }
  return data as A2UIEnvelope;
}
