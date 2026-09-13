import type { RendererProps } from "./types";
import { CategoryBreakdown } from "./CategoryBreakdown";

/** El agente pidió `table` → cuando hay varias categorías parejas, una
 * gráfica no deja comparar montos exactos. Misma decisión del agente que
 * pie_chart/bar_chart, mismo motor compartido (CategoryBreakdown). */
export function Table(props: RendererProps) {
  return <CategoryBreakdown {...props} mode="table" />;
}
