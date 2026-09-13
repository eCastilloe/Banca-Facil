/** Marco visual V2 del agente; las pestañas adicionales se incorporarán después. */
export function BankChrome() {
  return (
    <>
      <div className="bank-main">
        <div className="bank-main-inner">
          <span className="bank-logo">Bansur</span>
          <nav className="bank-segments bank-segments--agent" aria-label="Sección actual">
            <span className="bank-segment bank-segment--active">Banca Fácil</span>
          </nav>
        </div>
      </div>
      <div className="bank-tabs">
        <div className="bank-tabs-inner">
          <span className="bank-tab bank-tab--active">Entiende tus finanzas</span>
        </div>
      </div>
    </>
  );
}
