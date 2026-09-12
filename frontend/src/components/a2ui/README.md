# Catálogo adicional A2UI

Módulo independiente: no se importa automáticamente en App ni modifica el registro actual.
Reutiliza las gráficas, formato MXN, colores y estilos que ya existen. No añade dependencias.

## Contratos

| Nombre (alias) | Props |
| --- | --- |
| PieChart (pie_chart) | `period`, `total_spent`, `categories`: mismo `CategoryBreakdownProps` del proyecto |
| BarChart (bar_chart) | Igual que PieChart |
| Progress (progress) | `label: string`, `value: number`, `max: number` |
| CategoryBadge (category_badge) | `category`, `label?: string` |
| ActionButton (action_button) | `label`, `action: string`, `variant?: primary/secondary`, `disabled?: boolean`, `params?: Record<string, unknown>` |
| RiskIndicator (risk_indicator) | `level: low/medium/high`, `label`, `description?: string` |

Categorías: despensa, comida, transporte, servicios, entretenimiento, compras, salud, otros.
Se usa el vocabulario actual del frontend, en vez de introducir identificadores en inglés.
Progress limita la barra a 0–100%, conserva los valores originales y avisa al superar max.
Un max no positivo muestra “Objetivo no disponible”. Los números no finitos se rechazan en el renderer.

## Integración posterior (no aplicada)

```tsx
import { A2UIComponentRenderer } from './components/a2ui';

<A2UIComponentRenderer
  component={{
    id: 'budget',
    type: 'progress',
    props: { label: 'Presupuesto mensual', value: 7200, max: 10000 },
  }}
  onAction={(actionId, params) => { /* conectar al manejador existente */ }}
/>
```

El registro recibe el envelope local existente `{ id, type, props, actions? }`.
No implementa un parser universal del protocolo A2UI ni cambia el contrato del backend.
Las gráficas conservan `actions` con trigger `category_click` y emiten `category_id`.
ActionButton emite `props.action` y `props.params`; onAction siempre viene de React, nunca del JSON.
Los componentes también se pueden importar por separado con sus props tipadas.
Los wrappers directos de las gráficas son de visualización; para acciones utiliza el renderer.

`resolveComponent(name)` devuelve undefined para nombres desconocidos, incluidos nombres heredados de Object.
El renderer muestra el fallback existente para tipos desconocidos y un mensaje para props inválidas.
Este registro contiene solo los seis componentes nuevos/reutilizados; el registro actual conserva TransactionList.
