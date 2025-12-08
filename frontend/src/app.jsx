import React, { useState } from 'react';
import SpaceSelector from './components/SpaceSelector';
import NexusRAG from './components/NexusRAG'; // Your main app file

function App() {
  // If null, we show the selector. If set, we show the app.
  const [activeSpaceId, setActiveSpaceId] = useState(null);

  // Function to log out/exit space (optional, pass to NexusRAG if you want a "Back" button)
  const exitSpace = () => setActiveSpaceId(null);

  return (
    <div>
      {!activeSpaceId ? (
        // 1. Show Selector if no ID
        <SpaceSelector onSelectSpace={(id) => setActiveSpaceId(id)} />
      ) : (
        // 2. Show Main App if ID exists, passing the ID as a prop
        <NexusRAG spaceId={activeSpaceId} onExit={exitSpace} />
      )}
    </div>
  );
}

export default App;