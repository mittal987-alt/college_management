import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './index.css'

createRoot(document.getElementById('root')).render(
  // Removed StrictMode so that effect mounting isn't doubled (less annoying for our auth checks in dev)
  <App />
)
