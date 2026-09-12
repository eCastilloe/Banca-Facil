import type { RendererProps } from "./types";
import { CategoryBreakdown } from "./CategoryBreakdown";

/** El agente pidió `bar_chart` → arranca en modo barras (el usuario puede
 * cambiar a dona desde el toggle, misma data). */
export function BarChart(props: RendererProps) {
  return <CategoryBreakdown {...props} initialMode="bars" />;
}
