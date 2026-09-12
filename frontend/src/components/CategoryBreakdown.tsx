import { useEffect, useState } from "react";
import type { RendererProps } from "./types";
import type { CategoryBreakdownItem, CategoryBreakdownProps } from "../types/a2ui";
import { colorForCategory } from "../lib/categoryColors";
import { formatMXN } from "../lib/format";
import { useCountUp } from "../lib/useCountUp";
import { splitTopCategories } from "../lib/topCategories";
import { CategoryIcon } from "./CategoryIcon";

const MORE_ID = "__more__";
const VISIBLE_LIMIT = 4;
const RING_RADIUS = 76;
const RING_STROKE = 26;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

type Mode = "donut" | "bars";

/**
 * Motor compartido de pie_chart y bar_chart: mismos datos, dos formas de
 * pintarlas. Cuál de las dos se usa lo decide el agente (el `type` que
 * manda en el envelope) — no hay switch para que el usuario lo cambie a
 * mano, eso pisaría la decisión del LLM. El modo queda fijo por
 * instancia; PieChart/BarChart son los dos "sabores" registrados.
 *
 * También recorta a las 4 categorías con más gasto por default (menos
 * contaminación visual) con un "+N más" que expande el resto.
 */
export function CategoryBreakdown({ component, onAction, mode }: RendererProps & { mode: Mode }) {
  const props = component.props as unknown as CategoryBreakdownProps;
  const { categories, period, total_spent } = props;
  const animatedTotal = useCountUp(total_spent);

  const [expanded, setExpanded] = useState(false);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [grown, setGrown] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setGrown(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const { visible, hidden, hiddenTotal, hiddenPercent } = splitTopCategories(categories, VISIBLE_LIMIT);
  const rows: CategoryBreakdownItem[] = expanded
    ? [...visible, ...hidden]
    : hidden.length > 0
      ? [
          ...visible,
          {
            id: MORE_ID,
            label: `+${hidden.length} categoría${hidden.length > 1 ? "s" : ""} más`,
            total: hiddenTotal,
            percent: hiddenPercent,
          },
        ]
      : visible;

  const clickAction = component.actions?.find((a) => a.trigger === "category_click");

  function handleRowClick(id: string) {
    if (id === MORE_ID) {
      setExpanded(true);
      return;
    }
    if (clickAction) onAction(clickAction.id, { category_id: id });
  }

  function iconFor(id: string) {
    const color = id === MORE_ID ? "var(--color-ink-subtle)" : colorForCategory(id);
    const bg = id === MORE_ID ? "var(--color-bg)" : `${colorForCategory(id)}1A`;
    return { color, bg };
  }

  const max = Math.max(...rows.map((c) => c.total), 1);

  let cursor = 0;
  const segments = rows.map((c) => {
    const length = (c.percent / 100) * RING_CIRCUMFERENCE;
    const offset = (cursor / 100) * RING_CIRCUMFERENCE;
    cursor += c.percent;
    return { ...c, length, offset };
  });

  return (
    <div className="breakdown-card">
      <div className="breakdown-header">
        <span className="breakdown-period">{period.label ?? `${period.start} → ${period.end}`}</span>
        {period.was_clamped && <span className="breakdown-clamped">Tope de 3 meses aplicado</span>}
      </div>

      {mode === "donut" ? (
        <div className="breakdown-body breakdown-body--donut">
          <div className="donut-wrap">
            <svg viewBox="0 0 200 200" className="donut-svg">
              <circle cx="100" cy="100" r={RING_RADIUS} fill="none" stroke="var(--color-bg)" strokeWidth={RING_STROKE} />
              {segments.map((s) => {
                const { color } = iconFor(s.id);
                return (
                  <circle
                    key={s.id}
                    cx="100"
                    cy="100"
                    r={RING_RADIUS}
                    fill="none"
                    stroke={color}
                    strokeWidth={hoveredId === s.id ? RING_STROKE + 6 : RING_STROKE}
                    strokeDasharray={`${grown ? s.length : 0} ${RING_CIRCUMFERENCE}`}
                    strokeDashoffset={-s.offset}
                    transform="rotate(-90 100 100)"
                    className="donut-segment"
                    onMouseEnter={() => setHoveredId(s.id)}
                    onMouseLeave={() => setHoveredId(null)}
                    onClick={() => handleRowClick(s.id)}
                    style={{ cursor: "pointer" }}
                  />
                );
              })}
            </svg>
            <div className="donut-hole">
              <span className="donut-total">{formatMXN(animatedTotal)}</span>
              <span className="donut-total-label">gastado</span>
            </div>
          </div>

          <ul className="chip-list">
            {rows.map((c) => {
              const { color, bg } = iconFor(c.id);
              return (
                <li
                  key={c.id}
                  className={hoveredId === c.id ? "chip-row chip-row--hover" : "chip-row"}
                  onMouseEnter={() => setHoveredId(c.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  onClick={() => handleRowClick(c.id)}
                  role="button"
                  tabIndex={0}
                >
                  <span className="chip-icon" style={{ color, background: bg }}>
                    {c.id === MORE_ID ? (
                      <span className="chip-icon-dots">+{hidden.length}</span>
                    ) : (
                      <CategoryIcon categoryId={c.id} className="chip-icon-svg" />
                    )}
                  </span>
                  <span className="chip-label">{c.label}</span>
                  <span className="chip-amount">{formatMXN(c.total)}</span>
                  <span className="chip-percent">{c.percent.toFixed(1)}%</span>
                </li>
              );
            })}
          </ul>
        </div>
      ) : (
        <div className="breakdown-body breakdown-body--bars">
          <div className="breakdown-total">Total: {formatMXN(animatedTotal)}</div>
          <ul className="bar-list">
            {rows.map((c) => {
              const { color, bg } = iconFor(c.id);
              return (
                <li key={c.id} className="bar-row" onClick={() => handleRowClick(c.id)} role="button" tabIndex={0}>
                  <div className="bar-row-top">
                    <span className="bar-icon" style={{ color, background: bg }}>
                      {c.id === MORE_ID ? (
                        <span className="chip-icon-dots">+{hidden.length}</span>
                      ) : (
                        <CategoryIcon categoryId={c.id} className="chip-icon-svg" />
                      )}
                    </span>
                    <span className="bar-label">{c.label}</span>
                    <span className="bar-amount">{formatMXN(c.total)}</span>
                  </div>
                  <div className="bar-track">
                    <div
                      className="bar-fill"
                      style={{ width: grown ? `${(c.total / max) * 100}%` : "0%", background: c.id === MORE_ID ? "var(--color-border)" : colorForCategory(c.id) }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {expanded && categories.length > VISIBLE_LIMIT && (
        <button type="button" className="breakdown-collapse" onClick={() => setExpanded(false)}>
          Ver menos
        </button>
      )}
    </div>
  );
}
