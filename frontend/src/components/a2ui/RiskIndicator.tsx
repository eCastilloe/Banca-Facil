import type { RiskIndicatorProps } from './types';
import './styles.css';

const LEVELS = { low: 'Bajo', medium: 'Moderado', high: 'Alto' };
export function RiskIndicator({ level, label, description }: RiskIndicatorProps) {
  return <section className={`breakdown-card a2ui-risk a2ui-risk--${level}`}>
    <strong>{label}</strong>
    <span>Riesgo: {LEVELS[level]}</span>
    {description && <p>{description}</p>}
  </section>;
}
