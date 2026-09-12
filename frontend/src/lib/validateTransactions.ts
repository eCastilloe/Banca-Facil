import type { TransactionListProps } from '../types/a2ui';

const object = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);
const text = (value: unknown) => typeof value === 'string';
const finite = (value: unknown) => typeof value === 'number' && Number.isFinite(value);

export function validTransactionProps(props: unknown): props is TransactionListProps {
  return object(props) && object(props.period)
    && text(props.period.start) && text(props.period.end)
    && (props.period.label === undefined || text(props.period.label))
    && (props.category === undefined || (object(props.category) && text(props.category.id) && text(props.category.label)))
    && finite(props.total) && Array.isArray(props.transactions)
    && props.transactions.every(item => object(item) && text(item.id) && text(item.date)
      && text(item.description) && finite(item.amount));
}
