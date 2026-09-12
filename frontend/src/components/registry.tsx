import type { RendererProps } from './types';
import { TransactionList } from './TransactionList';
import { A2UIComponentRenderer } from './a2ui';
import { validTransactionProps } from '../lib/validateTransactions';

/**
 * Punto de entrada único para pintar cualquier componente que mande el
 * agente. `transaction_list` se valida y pinta aquí mismo (es el único
 * componente que no vive en el catálogo a2ui/); todo lo demás
 * (pie_chart, bar_chart, text_block, progress, category_badge,
 * action_button, risk_indicator) lo resuelve A2UIComponentRenderer contra
 * el catálogo validado en components/a2ui/registry.ts.
 */
export function ComponentRenderer(context: RendererProps) {
  if (context.component.type === 'transaction_list') {
    return validTransactionProps(context.component.props) ? (
      <TransactionList {...context} />
    ) : (
      <div className="unknown-card" role="alert">
        Datos no válidos para la lista de transacciones.
      </div>
    );
  }
  return <A2UIComponentRenderer {...context} />;
}
