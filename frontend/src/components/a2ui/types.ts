import type { CategoryBreakdownProps } from '../../types/a2ui';
import type { RendererProps } from '../types';

export type OnAction = RendererProps['onAction'];
export type Category = 'despensa' | 'comida' | 'transporte' | 'servicios' | 'entretenimiento' | 'compras' | 'salud' | 'otros';
export type RiskLevel = 'low' | 'medium' | 'high';
export type ChartProps = CategoryBreakdownProps;
export type ProgressProps = { label: string; value: number; max: number };
export type CategoryBadgeProps = { category: Category; label?: string };
export type ActionButtonProps = {
  label: string;
  action: string;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
  params?: Record<string, unknown>;
};
export type RiskIndicatorProps = { level: RiskLevel; label: string; description?: string };
export type TextBlockProps = { title: string; subtitle?: string };
export type ComponentPropsMap = {
  PieChart: ChartProps;
  BarChart: ChartProps;
  Progress: ProgressProps;
  CategoryBadge: CategoryBadgeProps;
  ActionButton: ActionButtonProps;
  RiskIndicator: RiskIndicatorProps;
  TextBlock: TextBlockProps;
};
