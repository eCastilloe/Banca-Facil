/**
 * Íconos por categoría — línea simple, monocromo vía currentColor, sin
 * emoji. El "vibe Banorte" es esto: minimal, geométrico, no ilustrativo.
 */
type Props = { categoryId: string; className?: string };

const SHARED = {
  viewBox: "0 0 20 20",
  fill: "none",
  xmlns: "http://www.w3.org/2000/svg",
} as const;

const STROKE = { stroke: "currentColor", strokeWidth: 1.5, strokeLinecap: "round", strokeLinejoin: "round" } as const;

export function CategoryIcon({ categoryId, className }: Props) {
  switch (categoryId) {
    case "despensa":
      return (
        <svg {...SHARED} className={className}>
          <path d="M2 3h2l1.7 9.9A1.6 1.6 0 0 0 7.3 14.3h6.9a1.6 1.6 0 0 0 1.58-1.32L17 6H5.1" {...STROKE} />
          <circle cx="8" cy="17" r="1.1" fill="currentColor" />
          <circle cx="14" cy="17" r="1.1" fill="currentColor" />
        </svg>
      );
    case "comida":
      return (
        <svg {...SHARED} className={className}>
          <path d="M6 2v6a2 2 0 1 0 4 0V2M8 8v10" {...STROKE} />
          <path d="M14 2c-1.2 0-2.2 1.4-2.2 3.5S12.8 9 14 9v9" {...STROKE} />
        </svg>
      );
    case "transporte":
      return (
        <svg {...SHARED} className={className}>
          <path d="M3.5 12l1.3-4.6A1.8 1.8 0 0 1 6.5 6h7a1.8 1.8 0 0 1 1.7 1.4L16.5 12" {...STROKE} />
          <rect x="2.5" y="12" width="15" height="3.6" rx="1.2" stroke="currentColor" strokeWidth="1.5" />
          <circle cx="6" cy="17.2" r="1.1" fill="currentColor" />
          <circle cx="14" cy="17.2" r="1.1" fill="currentColor" />
        </svg>
      );
    case "servicios":
      return (
        <svg {...SHARED} className={className}>
          <path d="M11 2 4.5 11h4.5l-1 7 7-9H10.5L11 2z" {...STROKE} />
        </svg>
      );
    case "entretenimiento":
      return (
        <svg {...SHARED} className={className}>
          <circle cx="10" cy="10" r="7.2" stroke="currentColor" strokeWidth="1.5" />
          <path d="M8.3 7.2l4.6 2.8-4.6 2.8V7.2z" fill="currentColor" />
        </svg>
      );
    case "compras":
      return (
        <svg {...SHARED} className={className}>
          <path d="M5.3 6.8h9.4l-.8 9.4a1.3 1.3 0 0 1-1.3 1.2H7.4a1.3 1.3 0 0 1-1.3-1.2L5.3 6.8z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
          <path d="M7.3 6.8V5.3a2.7 2.7 0 0 1 5.4 0v1.5" {...STROKE} />
        </svg>
      );
    case "salud":
      return (
        <svg {...SHARED} className={className}>
          <path
            d="M10 17s-6.2-3.8-6.2-8.4A3.9 3.9 0 0 1 10 6a3.9 3.9 0 0 1 6.2 2.6C16.2 13.2 10 17 10 17z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        </svg>
      );
    default:
      return (
        <svg {...SHARED} className={className}>
          <path d="M3 3h6.2l7.8 7.8-6.2 6.2L3 9.2V3z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
          <circle cx="7" cy="7" r="1" fill="currentColor" />
        </svg>
      );
  }
}
