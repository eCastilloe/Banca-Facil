import type { CategoryBreakdownItem, Period } from '../types/a2ui';
import { TransactionList } from './TransactionList';
import { validTransactionProps } from '../lib/validateTransactions';

/** Local subview: its back action never leaves the chart. */
export function CategoryDetail({ category, period, onBack }: {
  category: CategoryBreakdownItem;
  period: Period;
  onBack: () => void;
}) {
  const props = {
    category: { id: category.id, label: category.label },
    period,
    total: category.total,
    // Older responses may omit transactions; never fetch to fill the gap.
    transactions: category.transactions ?? [],
  };
  if (!validTransactionProps(props)) {
    return <div className="unknown-card" role="alert">
      Datos no válidos para las transacciones de esta categoría.
      <button className="breakdown-action" onClick={onBack}>Volver</button>
    </div>;
  }
  return <TransactionList component={{
    id: `local_detail_${category.id}`,
    type: 'transaction_list',
    props,
    actions: [{ id: 'local_back', label: 'Volver' }],
  }} onAction={onBack} />;
}
