import { useEffect, useState } from "react";
import type { RendererProps } from "./types";
import type { CategoryBreakdownProps } from "../types/a2ui";
import { colorForCategory } from "../lib/categoryColors";
import { formatMXN } from "../lib/format";
import { useCountUp } from "../lib/useCountUp";

export function BarChart({ component, onAction }: RendererProps) {
  const props = component.props as unknown as CategoryBreakdownProps;
  const { categories, period, total_spent } = props;
  const max = Math.max(...categories.map((c) => c.total), 1);
  const animatedTotal = useCountUp(total_spent);

  // Las barras arrancan en 0 y crecen a su ancho real un tick después de
  // montar, para que entren "creciendo" en vez de aparecer ya llenas.
  const [grown, setGrown] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setGrown(true));
    return () => cancelAnimationFrame(id);
  }, []);

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

      <div className="breakdown-total">Total: {formatMXN(animatedTotal)}</div>

      <ul className="bar-list">
        {categories.map((c) => (
          <li
            key={c.id}
            className="bar-row"
            onClick={() => handleClick(c.id)}
            role={clickAction ? "button" : undefined}
            tabIndex={clickAction ? 0 : undefined}
          >
            <div className="bar-row-top">
              <span className="bar-label">{c.label}</span>
              <span className="bar-amount">{formatMXN(c.total)}</span>
            </div>
            <div className="bar-track">
              <div
                className="bar-fill"
                style={{ width: grown ? `${(c.total / max) * 100}%` : "0%", background: colorForCategory(c.id) }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
