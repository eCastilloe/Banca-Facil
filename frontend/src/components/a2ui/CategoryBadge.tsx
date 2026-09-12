import { colorForCategory } from '../../lib/categoryColors';
import type { CategoryBadgeProps } from './types';
import './styles.css';

export function CategoryBadge({ category, label }: CategoryBadgeProps) {
  return <span className="a2ui-category">
    <span className="a2ui-category-dot" aria-hidden="true" style={{ background: colorForCategory(category) }} />
    {label ?? category}
  </span>;
}
