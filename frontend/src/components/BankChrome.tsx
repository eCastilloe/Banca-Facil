import { useEffect, useRef } from "react";

/**
 * Chrome de "sitio de Banorte" alrededor de nuestra pantalla — pedido
 * explícito del equipo: que esto se sienta como una pestaña más dentro de
 * banorte.com, no como una app aparte.
 *
 * Marco visual inspirado en banorte.com, con su logo público (decisión de
 * equipo — se usa el diseño V2 de Jorge). Todo lo que no sea "Entiende tus
 * finanzas" es decorativo/inerte: no construimos esas secciones, solo el
 * marco visual.
 */
const SEGMENTS = ["Personal", "Empresas", "PyME", "Gobierno"];
const PRODUCT_TABS = ["Cuentas", "Tarjetas", "Créditos", "Seguros", "Inversión"];

export function BankChrome() {
  const activeTabRef = useRef<HTMLSpanElement>(null);

  // En pantallas angostas la fila de pestañas hace scroll horizontal — nos
  // aseguramos de que la nuestra (la última) siempre arranque visible.
  useEffect(() => {
    activeTabRef.current?.scrollIntoView({ inline: "end", block: "nearest" });
  }, []);

  return (
    <>
      <div className="bank-utility">
        <div className="bank-utility-inner">
          <span className="bank-group">GRUPO FINANCIERO BANORTE <span aria-hidden="true">↗</span></span>
          <div className="bank-utility-right">
            <span>Ubícanos</span>
            <span>Banca en línea</span>
          </div>
        </div>
      </div>

      <div className="bank-main">
        <div className="bank-main-inner">
          <span className="bank-logo"><img src="https://www.banorte.com/dam/jcr:e96b09d5-b440-4d9f-bc51-d9f12a590cb8/Logo.svg" alt="Banorte" width="172" height="32" /></span>

          <nav className="bank-segments" aria-hidden="true">
            {SEGMENTS.map((s, i) => (
              <span key={s} className={i === 0 ? "bank-segment bank-segment--active" : "bank-segment"}>
                {s}
              </span>
            ))}
          </nav>

          <div className="bank-actions" aria-hidden="true">
            <span className="bank-icon-btn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
                <path d="M20 20L16.65 16.65" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </span>
            <span className="bank-enter-btn">Entrar</span>
          </div>
        </div>
      </div>

      <div className="bank-tabs">
        <div className="bank-tabs-inner">
          {PRODUCT_TABS.map((t) => (
            <span key={t} className="bank-tab" aria-hidden="true">
              {t}
            </span>
          ))}
          <span ref={activeTabRef} className="bank-tab bank-tab--active">
            Entiende tus finanzas
          </span>
        </div>
      </div>
    </>
  );
}
