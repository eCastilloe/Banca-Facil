/**
 * Mapeo categoría → color. El backend NO manda colores (fue decisión
 * explícita del equipo dejarlo del lado del frontend) — esta es una
 * propuesta inicial, ajústenla libremente sin que eso afecte al backend
 * ni al contrato de datos.
 */
const PALETTE = [
  "#6355e0", // despensa
  "#0f9488", // comida
  "#e0577a", // transporte
  "#eab308", // servicios
  "#38bdf8", // entretenimiento
  "#22c55e", // salud
  "#f97316", // compras
  "#94a3b8", // otros / sin categorizar
];

const CATEGORY_ORDER = [
  "despensa",
  "comida",
  "transporte",
  "servicios",
  "entretenimiento",
  "salud",
  "compras",
  "otros",
];

export function colorForCategory(categoryId: string): string {
  const idx = CATEGORY_ORDER.indexOf(categoryId);
  if (idx >= 0) return PALETTE[idx];

  // Fallback determinístico para categorías que no estén en la lista fija
  // (para que una categoría nueva no rompa el mapeo, solo tome un color
  // consistente cada vez que aparezca).
  let hash = 0;
  for (let i = 0; i < categoryId.length; i++) {
    hash = (hash * 31 + categoryId.charCodeAt(i)) >>> 0;
  }
  return PALETTE[hash % PALETTE.length];
}
