import type { RendererProps } from "./types";
import type { CategoryBreakdownProps } from "../types/a2ui";
import { colorForCategory } from "../lib/categoryColors";
import { formatMXN } from "../lib/format";
import { useCountUp } from "../lib/useCountUp";

export function PieChart({ component, onAction }: RendererProps) {
  const props = component.props as unknown as CategoryBreakdownProps;
  const { categories, period, total_spent } = props;
  const animatedTotal = useCountUp(total_spent);

  let cursor = 0;
  const stops = categories.map((c) => {
    const start = cursor;
    cursor += c.percent;
    return `${colorForCategory(c.id)} ${start}% ${cursor}%`;
  });
  const gradient = categories.length ? `conic-gradient(${stops.join(", ")})` : "var(--border)";

  const clickAction = component.actions?.find((a) => a.trigger === "category_click");
  const handleClick = (categoryId: string) => {
    if (clickAction) onAction(clickAction.id, { category_id: categoryId });
  };

  return (
    <div className="breakdown-card">
      <div className="breakdown-header">
        <span className="breakdown-period">{period.label ?? `${period.start} → ${period.end}`}</span>
        {period.was_clamped && <span className="breakdown-clamped">Tope de 3 meses aplicado</span>}
      </div>

      <div className="breakdown-body breakdown-body--pie">
        <div className="pie" style={{ background: gradient }}>
          <div className="pie-hole">
            <span className="pie-total">{formatMXN(animatedTotal)}</span>
            <span className="pie-total-label">gastado</span>
          </div>
        </div>

        <ul className="breakdown-legend">
          {categories.map((c) => (
            <li
              key={c.id}
              className="legend-row"
              onClick={() => handleClick(c.id)}
              role={clickAction ? "button" : undefined}
              tabIndex={clickAction ? 0 : undefined}
            >
              <span className="legend-dot" style={{ background: colorForCategory(c.id) }} />
              <span className="legend-label">{c.label}</span>
              <span className="legend-amount">{formatMXN(c.total)}</span>
              <span className="legend-percent">{c.percent.toFixed(1)}%</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
