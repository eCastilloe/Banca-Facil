import type { CategoryBreakdownProps } from '../../types/a2ui';
import type { RendererProps } from '../types';

export type OnAction = RendererProps['onAction'];
export type Category = 'despensa' | 'comida' | 'transporte' | 'servicios' | 'entretenimiento' | 'compras' | 'salud' | 'otros';
export type RiskLevel = 'low' | 'medium' | 'high';
export type ChartProps = CategoryBreakdownProps;
export type ProgressProps = {
  label: string;
  value: number;
  max: number;
  /** "budget" (default): `max` es un límite/presupuesto real que el usuario
   * creó -- pasarse de ahí es "superar el objetivo". "comparison": `max` es
   * solo una referencia (p. ej. el gasto del periodo anterior) sin que
   * exista un presupuesto -- pasarse no es "superar" nada, solo gastar más
   * que antes. */
  variant?: 'budget' | 'comparison';
};
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
