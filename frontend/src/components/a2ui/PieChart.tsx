import { PieChart as ExistingPieChart } from '../PieChart';
import type { ChartProps } from './types';

/** Reuses the current chart and backend contract. Action wiring lives in the registry. */
export function PieChart(props: ChartProps) {
  return <ExistingPieChart component={{ id: 'pie', type: 'pie_chart', props: { ...props } }} onAction={() => {}} />;
}
