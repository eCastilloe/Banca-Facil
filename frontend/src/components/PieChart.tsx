import type { RendererProps } from "./types";
import { CategoryBreakdown } from "./CategoryBreakdown";

/** El agente pidió `pie_chart` → siempre se pinta como dona. Es su
 * decisión, no algo que el usuario pueda cambiar desde aquí. */
export function PieChart(props: RendererProps) {
  return <CategoryBreakdown {...props} mode="donut" />;
}
