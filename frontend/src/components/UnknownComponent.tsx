import type { RendererProps } from "./types";

/**
 * Se pinta cuando el agente manda un `type` que el frontend todavía no
 * tiene registrado. Evita que la app truene y deja visible qué falta
 * construir — útil mientras el catálogo de componentes sigue creciendo.
 */
export function UnknownComponent({ component }: RendererProps) {
  return (
    <div className="unknown-card">
      <div className="unknown-title">
        Componente no soportado: <code>{component.type}</code>
      </div>
      <pre className="unknown-json">{JSON.stringify(component.props, null, 2)}</pre>
    </div>
  );
}
