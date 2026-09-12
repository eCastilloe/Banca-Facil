/**
 * Agente simulado — MISMA forma de respuesta (A2UIEnvelope) que va a
 * mandar el backend real, para poder construir y probar el registry y el
 * layout de chat antes de que el contrato HTTP (tarea compartida "sh-1")
 * y el orquestador estén listos.
 *
 * Cuando el backend exponga su endpoint, todo esto se reemplaza dentro de
 * lib/api.ts sin tocar ni el registry ni los componentes.
 */
import type { A2UIEnvelope, TransactionItem } from "../types/a2ui";

const CATEGORIES = [
  { id: "despensa", label: "Despensa / supermercado", total: 4200, percent: 22.8 },
  { id: "comida", label: "Comida y restaurantes", total: 3100, percent: 16.8 },
  { id: "compras", label: "Compras", total: 3900, percent: 21.2 },
  { id: "transporte", label: "Transporte", total: 2650, percent: 14.4 },
  { id: "servicios", label: "Servicios", total: 1830, percent: 9.9 },
  { id: "entretenimiento", label: "Entretenimiento y suscripciones", total: 1420, percent: 7.7 },
  { id: "salud", label: "Salud", total: 980, percent: 5.3 },
  { id: "otros", label: "Otros / sin categorizar", total: 340, percent: 1.9 },
];

const TOTAL_SPENT = CATEGORIES.reduce((sum, c) => sum + c.total, 0);

const PERIOD = {
  start: "2026-06-12",
  end: "2026-09-12",
  label: "Últimos 3 meses",
  requested_start: "2026-01-01",
  was_clamped: true,
};

const TRANSACTIONS: Record<string, TransactionItem[]> = {
  despensa: [
    { id: "t1", date: "2026-09-10", description: "Walmart", amount: -540.3 },
    { id: "t2", date: "2026-08-22", description: "Soriana", amount: -612.1 },
    { id: "t3", date: "2026-07-15", description: "OXXO", amount: -128.5 },
  ],
  comida: [
    { id: "t4", date: "2026-09-08", description: "Restaurante La Parrilla", amount: -320.0 },
    { id: "t5", date: "2026-08-30", description: "Starbucks", amount: -95.0 },
  ],
  compras: [
    { id: "t6", date: "2026-09-01", description: "Amazon", amount: -1200.0 },
    { id: "t7", date: "2026-08-12", description: "Liverpool", amount: -2700.0 },
  ],
  transporte: [
    { id: "t8", date: "2026-09-09", description: "Gasolinera Pemex", amount: -800.0 },
    { id: "t9", date: "2026-08-28", description: "Uber", amount: -175.0 },
  ],
  servicios: [
    { id: "t10", date: "2026-09-05", description: "CFE", amount: -450.0 },
    { id: "t11", date: "2026-09-03", description: "Telmex", amount: -580.0 },
  ],
  entretenimiento: [
    { id: "t12", date: "2026-09-01", description: "Netflix", amount: -219.0 },
    { id: "t13", date: "2026-09-01", description: "Spotify", amount: -115.0 },
  ],
  salud: [{ id: "t14", date: "2026-08-19", description: "Farmacia Guadalajara", amount: -340.0 }],
  otros: [{ id: "t15", date: "2026-07-30", description: "Cargo sin identificar", amount: -340.0 }],
};

/** El LLM decide libremente el `type` — en el mock lo simulamos con un
 * default de `pie_chart` (lo que se ve al abrir la app, sin que el usuario
 * tenga que preguntar nada), pero cuando la pregunta es explícita el mock
 * elige `bar_chart` por ser más legible con 8 categorías — igual que se
 * acordó que decidiría el modelo real caso por caso. */
export function mockOverview(
  conversationId: string,
  preferredType: "pie_chart" | "bar_chart" = "pie_chart",
): A2UIEnvelope {
  return {
    version: "1.0",
    intent: "entender_gastos",
    conversation_id: conversationId,
    components: [
      { id: 'budget_progress', type: 'progress', props: { label: 'Presupuesto del periodo', value: TOTAL_SPENT, max: 25000 } },
      { id: 'budget_risk', type: 'risk_indicator', props: { level: 'medium', label: 'Acercándote al presupuesto', description: 'Has utilizado cerca del 74% del presupuesto de ejemplo.' } },
      { id: 'category_badge', type: 'category_badge', props: { category: 'despensa', label: 'Mayor gasto: despensa' } },
      {
        id: "spending_overview",
        type: preferredType,
        props: {
          period: PERIOD,
          total_spent: TOTAL_SPENT,
          categories: CATEGORIES.map(category => ({ ...category, transactions: TRANSACTIONS[category.id] ?? [] })),
        },
      },
      { id: 'detail_button', type: 'action_button', props: { label: 'Ver gastos de despensa', action: 'view_category_detail', params: { category_id: 'despensa' } } },
    ],
  };
}

/** Deterministic demo scenarios; this is not a language model. */
export function mockMessage(conversationId: string, message: string): A2UIEnvelope {
  const query = message.trim().toLocaleLowerCase('es-MX');
  if (query === 'demo error') throw new Error('Error simulado. Puedes intentar otra pregunta o volver al resumen.');
  if (query === 'demo vacío' || query === 'demo vacio') {
    return { version: '1.0', intent: 'sin_resultados', conversation_id: conversationId, components: [] };
  }
  if (query === 'demo inválido' || query === 'demo invalido') {
    return { ...mockOverview(conversationId), version: 'invalid' };
  }
  const category = CATEGORIES.find(item => query.includes(item.id));
  if (category) return mockCategoryDetail(conversationId, category.id);
  return mockOverview(conversationId, query.includes('resumen') || query.includes('circular') ? 'pie_chart' : 'bar_chart');
}

export function mockCategoryDetail(conversationId: string, categoryId: string): A2UIEnvelope {
  const category = CATEGORIES.find((c) => c.id === categoryId);
  const transactions = TRANSACTIONS[categoryId] ?? [];
  return {
    version: "1.0",
    intent: "ver_categoria_detalle",
    conversation_id: conversationId,
    components: [
      {
        id: `category_detail_${categoryId}`,
        type: "transaction_list",
        props: {
          category: category ? { id: category.id, label: category.label } : undefined,
          period: PERIOD,
          total: category?.total ?? 0,
          transactions,
        },
        actions: [{ id: "back_to_overview", label: "Volver al resumen" }],
      },
    ],
  };
}
