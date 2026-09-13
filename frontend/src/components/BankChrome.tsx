/** Marco visual del agente; las pestañas adicionales se incorporarán después. */
export function BankChrome() {
  return (
    <>
      <div className="bank-main">
        <div className="bank-main-inner">
          <span className="bank-logo"><img src="https://www.banorte.com/dam/jcr:e96b09d5-b440-4d9f-bc51-d9f12a590cb8/Logo.svg" alt="Banorte" width="172" height="32" /></span>
          <nav className="bank-segments bank-segments--agent" aria-label="Sección actual">
            <span className="bank-segment bank-segment--active">Agente</span>
          </nav>
        </div>
      </div>
      <div className="bank-tabs">
        <div className="bank-tabs-inner">
          <span className="bank-tab bank-tab--active">Entender mis gastos</span>
        </div>
      </div>
    </>
  );
}
