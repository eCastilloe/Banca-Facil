import { BarChart as ExistingBarChart } from '../BarChart';
import type { ChartProps } from './types';

export function BarChart(props: ChartProps) {
  return <ExistingBarChart component={{ id: 'bars', type: 'bar_chart', props: { ...props } }} onAction={() => {}} />;
}
