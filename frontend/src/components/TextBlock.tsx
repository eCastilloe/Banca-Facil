import type { RendererProps } from "./types";

type TextBlockProps = { title: string; subtitle?: string };

/**
 * El "insight" que el agente dice antes (o en vez) de una gráfica — texto
 * suelto, sin tarjeta, para que se lea como algo que el agente interpretó
 * y no como un componente más apilado.
 */
export function TextBlock({ component }: RendererProps) {
  const props = component.props as unknown as TextBlockProps;
  return (
    <div className="text-block">
      <p className="text-block-title">{props.title}</p>
      {props.subtitle && <p className="text-block-subtitle">{props.subtitle}</p>}
    </div>
  );
}
