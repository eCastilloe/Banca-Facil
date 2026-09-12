import type { RendererProps } from './types';
import { TransactionList } from './TransactionList';
import { A2UIComponentRenderer } from './a2ui';
import { validTransactionProps } from '../lib/validateTransactions';

export function ComponentRenderer(context: RendererProps) {
  if (context.component.type === 'transaction_list') {
    return validTransactionProps(context.component.props)
      ? <TransactionList {...context} />
      : <div className="unknown-card" role="alert">Datos no válidos para la lista de transacciones.</div>;
  }
  return <A2UIComponentRenderer {...context} />;
}
