import type { ComponentPropsMap } from './types';

type Data = Record<string, unknown>;
const object = (v: unknown): v is Data => typeof v === 'object' && v !== null && !Array.isArray(v);
const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const text = (v: unknown): v is string => typeof v === 'string';
const optionalText = (v: unknown) => v === undefined || text(v);
const categories = ['despensa', 'comida', 'transporte', 'servicios', 'entretenimiento', 'compras', 'salud', 'otros'];

export function validProps<K extends keyof ComponentPropsMap>(name: K, p: unknown): p is ComponentPropsMap[K] {
  if (!object(p)) return false;
  switch (name) {
    case 'PieChart':
    case 'BarChart':
    case 'Table':
      return object(p.period) && text(p.period.start) && text(p.period.end) && optionalText(p.period.label)
        && (p.period.was_clamped === undefined || typeof p.period.was_clamped === 'boolean')
        && finite(p.total_spent) && p.total_spent >= 0 && Array.isArray(p.categories)
        && p.categories.every(c => object(c) && text(c.id) && text(c.label) && finite(c.total) && c.total >= 0 && finite(c.percent) && c.percent >= 0 && c.percent <= 100);
    case 'Progress': return text(p.label) && finite(p.value) && finite(p.max);
    case 'CategoryBadge': return text(p.category) && categories.includes(p.category) && optionalText(p.label);
    case 'ActionButton': return text(p.label) && text(p.action) && p.action.trim().length > 0
      && (p.variant === undefined || p.variant === 'primary' || p.variant === 'secondary')
      && (p.disabled === undefined || typeof p.disabled === 'boolean') && (p.params === undefined || object(p.params));
    case 'RiskIndicator': return ['low', 'medium', 'high'].includes(String(p.level)) && text(p.label) && optionalText(p.description);
    case 'TextBlock': return text(p.title) && optionalText(p.subtitle);
    default: return false;
  }
}
