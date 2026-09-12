import type { ActionButtonProps, OnAction } from './types';
import './styles.css';

export function ActionButton({ label, action, variant = 'secondary', disabled = false, params, onAction }: ActionButtonProps & { onAction: OnAction }) {
  return <button type="button" className={`a2ui-action a2ui-action--${variant}`} disabled={disabled}
    onClick={() => onAction(action, params)}>{label}</button>;
}
