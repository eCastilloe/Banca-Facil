import { useState } from "react";
import type { RendererProps } from "./types";
import { CategoryDetail } from './CategoryDetail';
import type { CategoryBreakdownProps } from "../types/a2ui";
import { colorForCategory } from "../lib/categoryColors";
import { formatMXN } from "../lib/format";

export function BarChart({ component }: RendererProps) {
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);
  const props = component.props as unknown as CategoryBreakdownProps;
  const { categories, period, total_spent } = props;
  const max = Math.max(...categories.map((c) => c.total), 1);

  const selectedCategory = categories.find(category => category.id === selectedCategoryId);
  if (selectedCategory) return <CategoryDetail category={selectedCategory} period={period} onBack={() => setSelectedCategoryId(null)} />;

  return (
    <div className="breakdown-card">
      <div className="breakdown-header">
        <span className="breakdown-period">{period.label ?? `${period.start} → ${period.end}`}</span>
        {period.was_clamped && <span className="breakdown-clamped">Tope de 3 meses aplicado</span>}
      </div>

      <div className="breakdown-total">Total: {formatMXN(total_spent)}</div>

      <ul className="bar-list">
        {categories.map((c) => (
          <li
            key={c.id}
            className="bar-row"
            onClick={() => setSelectedCategoryId(c.id)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                setSelectedCategoryId(c.id);
              }
            }}
            role="button"
            tabIndex={0}
          >
            <div className="bar-row-top">
              <span className="bar-label">{c.label}</span>
              <span className="bar-amount">{formatMXN(c.total)}</span>
            </div>
            <div className="bar-track">
              <div
                className="bar-fill"
                style={{ width: `${(c.total / max) * 100}%`, background: colorForCategory(c.id) }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
