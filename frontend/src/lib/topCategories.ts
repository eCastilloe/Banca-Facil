import type { CategoryBreakdownItem } from "../types/a2ui";

export type SplitCategories = {
  visible: CategoryBreakdownItem[];
  hidden: CategoryBreakdownItem[];
  hiddenTotal: number;
  hiddenPercent: number;
};

/** Recorta el desglose a las `limit` categorías con más gasto (ordenadas
 * de mayor a menor), agrupando el resto — así el pie/bar chart no
 * arranca mostrando las 8 categorías de golpe. */
export function splitTopCategories(categories: CategoryBreakdownItem[], limit = 4): SplitCategories {
  const sorted = [...categories].sort((a, b) => b.total - a.total);
  const visible = sorted.slice(0, limit);
  const hidden = sorted.slice(limit);
  const hiddenTotal = hidden.reduce((sum, c) => sum + c.total, 0);
  const hiddenPercent = hidden.reduce((sum, c) => sum + c.percent, 0);
  return { visible, hidden, hiddenTotal, hiddenPercent };
}
