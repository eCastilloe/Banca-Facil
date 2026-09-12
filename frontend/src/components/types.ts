import type { A2UIComponent } from "../types/a2ui";

/** Todo componente del registry recibe esta misma forma: el bloque A2UI
 * que le toca pintar, y una función para avisarle al agente cuando el
 * usuario interactúa (clic en categoría, botón de acción, etc.). */
export type RendererProps = {
  component: A2UIComponent;
  onAction: (actionId: string, params?: Record<string, unknown>) => void;
};
