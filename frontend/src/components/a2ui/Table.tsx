import { Table as ExistingTable } from '../Table';
import type { ChartProps } from './types';

/** Reuses the same CategoryBreakdown engine as pie_chart/bar_chart, mode="table". */
export function Table(props: ChartProps) {
  return <ExistingTable component={{ id: 'table', type: 'table', props: { ...props } }} onAction={() => {}} />;
}
