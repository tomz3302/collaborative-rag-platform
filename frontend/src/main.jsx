// frontend/src/main.jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import NexusRAG from './components/NexusRAG.jsx'
import './index.css' // We will create this next for Tailwind

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <NexusRAG />
  </React.StrictMode>,
)