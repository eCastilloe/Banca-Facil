import type { RendererProps } from "./types";
import { CategoryBreakdown } from "./CategoryBreakdown";

/** El agente pidió `pie_chart` → arranca en modo dona (el usuario puede
 * cambiar a barras desde el toggle, misma data). */
export function PieChart(props: RendererProps) {
  return <CategoryBreakdown {...props} initialMode="donut" />;
}
