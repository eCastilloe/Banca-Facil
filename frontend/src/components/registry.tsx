import type { ComponentType } from "react";
import type { RendererProps } from "./types";
import { PieChart } from "./PieChart";
import { BarChart } from "./BarChart";
import { TransactionList } from "./TransactionList";
import { TextBlock } from "./TextBlock";
import { UnknownComponent } from "./UnknownComponent";

/**
 * Catálogo cerrado de componentes que el agente puede invocar (ver
 * docs/a2ui-schema.md). El LLM elige libremente cuál usar entre los que
 * están aquí — agregar un componente nuevo es solo:
 *   1. construir el componente,
 *   2. registrarlo en este objeto,
 *   3. avisarle al backend que ya existe (para que el system prompt lo liste).
 */
const REGISTRY: Record<string, ComponentType<RendererProps>> = {
  pie_chart: PieChart,
  bar_chart: BarChart,
  transaction_list: TransactionList,
  text_block: TextBlock,
};

export function ComponentRenderer({ component, onAction }: RendererProps) {
  const Component = REGISTRY[component.type] ?? UnknownComponent;
  return <Component component={component} onAction={onAction} />;
}
