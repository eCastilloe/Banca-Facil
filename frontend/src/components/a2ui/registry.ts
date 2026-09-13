import { createElement, type ComponentType } from 'react';
import type { RendererProps } from '../types';
import { PieChart as ExistingPieChart } from '../PieChart';
import { BarChart as ExistingBarChart } from '../BarChart';
import { Table as ExistingTable } from '../Table';
import { TextBlock as ExistingTextBlock } from '../TextBlock';
import { UnknownComponent } from '../UnknownComponent';
import { Progress } from './Progress';
import { CategoryBadge } from './CategoryBadge';
import { ActionButton } from './ActionButton';
import { RiskIndicator } from './RiskIndicator';
import { validProps } from './validation';
import type { ComponentPropsMap } from './types';

function adapter<K extends keyof ComponentPropsMap>(name: K, render: (props: ComponentPropsMap[K], context: RendererProps) => React.ReactNode): ComponentType<RendererProps> {
  return function ValidatedComponent(context: RendererProps) {
    const props = context.component.props;
    if (!validProps(name, props)) return createElement('div', { className: 'unknown-card' }, `Datos no válidos para ${name}.`);
    return render(props, context);
  };
}

/** Same envelope and action callback as the existing renderer; no automatic registration. */
export const componentRegistry = Object.freeze({
  PieChart: adapter('PieChart', (_props, context) => createElement(ExistingPieChart, context)),
  BarChart: adapter('BarChart', (_props, context) => createElement(ExistingBarChart, context)),
  Table: adapter('Table', (_props, context) => createElement(ExistingTable, context)),
  Progress: adapter('Progress', props => createElement(Progress, props)),
  CategoryBadge: adapter('CategoryBadge', props => createElement(CategoryBadge, props)),
  ActionButton: adapter('ActionButton', (props, { onAction }) => createElement(ActionButton, { ...props, onAction })),
  RiskIndicator: adapter('RiskIndicator', props => createElement(RiskIndicator, props)),
  TextBlock: adapter('TextBlock', (_props, context) => createElement(ExistingTextBlock, context)),
});

const aliases: Readonly<Record<string, keyof typeof componentRegistry>> = Object.freeze({
  pie_chart: 'PieChart', bar_chart: 'BarChart', table: 'Table', progress: 'Progress', category_badge: 'CategoryBadge', action_button: 'ActionButton', risk_indicator: 'RiskIndicator', text_block: 'TextBlock',
});

export function resolveComponent(name: string): ComponentType<RendererProps> | undefined {
  const key = Object.hasOwn(aliases, name) ? aliases[name] : name;
  return Object.hasOwn(componentRegistry, key) ? componentRegistry[key as keyof typeof componentRegistry] : undefined;
}

export function A2UIComponentRenderer(context: RendererProps) {
  const Component = resolveComponent(context.component.type) ?? UnknownComponent;
  return createElement(Component, context);
}
