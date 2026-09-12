import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
// 'banorte-theme.css' (rediseño visual v2 de otra sesión) queda en el repo
// sin cargarse por ahora — pisa el hero/dona/paletas ya aprobados por el
// equipo de frontend. Si se decide adoptarlo, se reactiva aquí.
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
