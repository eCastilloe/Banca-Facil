import { useId } from 'react';
import type { ProgressProps } from './types';
import './styles.css';

export function Progress({ label, value, max }: ProgressProps) {
  const labelId = useId();
  const valid = Number.isFinite(value) && Number.isFinite(max) && max > 0;
  const ratio = valid ? Math.min(100, Math.max(0, value / max * 100)) : 0;
  return (
    <section className="breakdown-card a2ui-progress">
      <strong id={labelId}>{label}</strong>
      {valid ? <>
        <span>{value.toLocaleString('es-MX')} / {max.toLocaleString('es-MX')} · {Math.round(ratio)}%</span>
        <progress aria-labelledby={labelId} max={100} value={ratio} />
        {value > max && <span>Has superado el objetivo.</span>}
      </> : <span>Objetivo no disponible.</span>}
    </section>
  );
}
