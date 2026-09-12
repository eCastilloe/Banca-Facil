import type { RendererProps } from "./types";
import { CategoryBreakdown } from "./CategoryBreakdown";

/** El agente pidió `bar_chart` → siempre se pinta como barras. Es su
 * decisión, no algo que el usuario pueda cambiar desde aquí. */
export function BarChart(props: RendererProps) {
  return <CategoryBreakdown {...props} mode="bars" />;
}
