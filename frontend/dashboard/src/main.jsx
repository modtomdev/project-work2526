import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import SvgSimulation from './Components/SvgSimulation.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <SvgSimulation />
  </StrictMode>,
)
