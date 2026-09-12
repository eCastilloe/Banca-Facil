# Integración A2UI

El frontend funciona sin backend: `lib/api.ts` serializa la respuesta del mock a JSON y la pasa por el mismo parser que usa HTTP. El registro principal incluye los seis componentes de `components/a2ui` y `transaction_list`. No es un intérprete universal del protocolo A2UI; implementa el envelope local versión 1.0.

## Probar

Desde `frontend`: `npm ci`, después `npm run dev`.

- Al abrir: progreso, indicador de riesgo, categoría, gráfica circular y botón de detalle.
- Escribe `barras` o `resumen` para cambiar de gráfica.
- Escribe `despensa` o pulsa una categoría/el botón para ver transacciones; “Volver al resumen” recupera la vista inicial.
- `demo vacío`: respuesta sin componentes.
- `demo error`: fallo simulado.
- `demo inválido`: respuesta que no cumple el contrato.

Los datos son ficticios y las preguntas se resuelven con reglas sencillas, sin IA. Los totales de categoría son del periodo completo y las transacciones del mock son solo una muestra.

## Conectar backend

Copia `.env.example` a `.env.local`, asigna `VITE_A2UI_ENDPOINT=http://localhost:3000/chat` (o la URL real) y reinicia Vite. Vacío usa mock; configurado usa HTTP y muestra los errores sin sustituirlos por datos ficticios. No coloques claves privadas en variables VITE.

Contrato HTTP **propuesto, pendiente de acordar con backend**: POST JSON al endpoint configurado. Si usa otro origen, el servidor debe permitir el origen del frontend mediante CORS. La autenticación deberá adaptarse al mecanismo que acuerde el equipo.

```json
{"event":"overview","conversation_id":"id-de-la-conversacion"}
```
```json
{"event":"message","message":"Mis gastos","conversation_id":"id-de-la-conversacion"}
```
```json
{"event":"action","conversation_id":"id-de-la-conversacion","component_id":"detail_button","action_id":"view_category_detail","params":{"category_id":"despensa"}}
```

La respuesta es directamente el envelope, sin envolverlo en `data`:

```json
{
  "version": "1.0",
  "intent": "entender_gastos",
  "conversation_id": "id-de-la-conversacion",
  "components": [
    {"id":"budget","type":"progress","props":{"label":"Presupuesto","value":7200,"max":10000}}
  ]
}
```

El parser exige versión 1.0, la misma conversación, IDs únicos, objetos props y acciones bien formadas. `components: []` muestra el estado vacío. Cada renderer valida sus props y los tipos desconocidos muestran un fallback. Consulta `components/a2ui/README.md` para los contratos del catálogo; `transaction_list` usa `TransactionListProps` de `src/types/a2ui.ts`.

## Verificación

`npm run build`, `npm run lint` y `node --experimental-strip-types --test tests/a2ui.test.mjs` (Node con soporte de TypeScript stripping).
