/** Colores básicos por categoría, compartidos por gráfica y leyenda. */
const PALETTE = [
  "#FACC15", // despensa: amarillo
  "#F97316", // comida: naranja
  "#16A34A", // transporte: verde
  "#DC2626", // servicios: rojo
  "#9333EA", // entretenimiento: morado
  "#2563EB", // compras: azul
  "#06B6D4", // salud: cian
  "#64748B", // otros: gris
];

const CATEGORY_ORDER = [
  "despensa",
  "comida",
  "transporte",
  "servicios",
  "entretenimiento",
  "compras",
  "salud",
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
