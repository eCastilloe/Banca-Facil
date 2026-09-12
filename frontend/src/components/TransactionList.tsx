import type { RendererProps } from "./types";
import type { TransactionListProps } from "../types/a2ui";
import { formatMXN } from "../lib/format";

export function TransactionList({ component, onAction }: RendererProps) {
  const props = component.props as unknown as TransactionListProps;
  const { category, period, total, transactions } = props;

  return (
    <div className="breakdown-card">
      <div className="breakdown-header">
        <span className="breakdown-period">
          {category ? category.label : "Todas las transacciones"} ·{" "}
          {period.label ?? `${period.start} → ${period.end}`}
        </span>
      </div>

      <div className="breakdown-total">Total: {formatMXN(total)}</div>

      <ul className="tx-list">
        {transactions.map((t) => (
          <li key={t.id} className="tx-row">
            <div>
              <div className="tx-desc">{t.description}</div>
              <div className="tx-date">{t.date}</div>
            </div>
            <div className={`tx-amount ${t.amount < 0 ? "negative" : "positive"}`}>
              {t.amount < 0 ? "-" : "+"}
              {formatMXN(Math.abs(t.amount))}
            </div>
          </li>
        ))}
        {transactions.length === 0 && <li className="tx-empty">No hay transacciones en este periodo.</li>}
      </ul>

      {component.actions?.map((a) => (
        <button key={a.id} className="breakdown-action" onClick={() => onAction(a.id)}>
          {a.label ?? "Continuar"}
        </button>
      ))}
    </div>
  );
}
