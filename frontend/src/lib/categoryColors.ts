/**
 * Mapeo categoría → color. El backend NO manda colores (fue decisión
 * explícita del equipo dejarlo del lado del frontend) — esta es una
 * propuesta inicial, ajústenla libremente sin que eso afecte al backend
 * ni al contrato de datos.
 *
 * Los tonos salen directo del design system real de Banorte (extraídos de
 * banorte.com: --color_primario_100/300, --color_secundario_700,
 * --color_positivo_100, --color_aviso_100, --color_gris_500/300), para
 * que el desglose por categoría se sienta parte de la misma marca aunque
 * necesite más matices de los que ellos exponen para texto/botones.
 */
const PALETTE = [
  "#EB0029", // despensa            — primario_100 (rojo Banorte)
  "#323E48", // comida              — secundario_700 (tinta)
  "#6CC04A", // transporte          — positivo_100 (verde)
  "#F5BE64", // servicios           — aviso_100 (ámbar)
  "#5B6670", // entretenimiento     — gris_600
  "#8F0017", // compras             — primario_300 (rojo oscuro)
  "#7B868C", // salud               — gris_500
  "#C1C5C8", // otros/sin categorizar — gris_300
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
