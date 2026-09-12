/**
 * Contrato A2UI acordado con el backend (ver docs/a2ui-schema.md del equipo).
 * El agente manda uno de estos "envelopes"; el frontend nunca decide qué
 * componente pintar, solo sabe pintar los `type` que tiene registrados
 * (ver components/registry.tsx).
 */

export type Period = {
  start: string; // YYYY-MM-DD
  end: string; // YYYY-MM-DD
  label?: string;
  /** Si el usuario pidió un rango más amplio, aquí viene lo que pidió de verdad. */
  requested_start?: string;
  requested_end?: string;
  /** true si el backend recortó el rango pedido (tope de 3 meses). */
  was_clamped?: boolean;
};

export type CategoryBreakdownItem = {
  id: string;
  label: string;
  total: number;
  percent: number;
  transactions: TransactionItem[];
};

/** Props compartidas por pie_chart y bar_chart — el LLM elige el `type`,
 * no la forma de los datos. */
export type CategoryBreakdownProps = {
  period: Period;
  total_spent: number;
  categories: CategoryBreakdownItem[];
};

export type TransactionItem = {
  id: string;
  date: string;
  description: string;
  amount: number;
};

export type TransactionListProps = {
  category?: { id: string; label: string };
  period: Period;
  total: number;
  transactions: TransactionItem[];
};

export type ComponentAction = {
  id: string;
  label?: string;
  /** Cómo se dispara: "category_click" (clic en un ítem del desglose),
   * "button" (botón explícito), etc. Opcional — algunos componentes solo
   * tienen una forma natural de disparar su acción. */
  trigger?: string;
};

/** Une todo componente A2UI. `props` es genérico porque el catálogo de
 * `type`s puede crecer sin tocar este tipo — cada componente concreto
 * hace su propio cast/validación de props al recibirlas. */
export type A2UIComponent = {
  id: string;
  type: string;
  props: Record<string, unknown>;
  actions?: ComponentAction[];
};

export type A2UIEnvelope = {
  version: string;
  intent: string;
  conversation_id: string;
  components: A2UIComponent[];
  /** Preguntas de seguimiento sugeridas para ESTA respuesta puntual — el
   * agente las arma según el contexto de lo que se acaba de mostrar, no
   * es una lista fija del frontend. Va aparte de `components` porque no
   * es contenido para pintar, es una afordancia de navegación; el
   * frontend decide cómo mostrarla (barra colapsable, fija arriba del
   * input), no si mostrarla. */
  suggested_prompts?: string[];
};

/** Lo que el frontend manda de vuelta al agente cuando el usuario
 * interactúa con la UI generada (clic en categoría, botón, etc.). */
export type ActionEvent = {
  event: "action";
  conversation_id: string;
  component_id: string;
  action_id: string;
  params?: Record<string, unknown>;
};
