import React from 'react';
import { useNavigate } from 'react-router-dom';
import SpaceSelector from '../components/SpaceSelector'; 

const Dashboard = () => {
  const navigate = useNavigate();

  const handleSelectSpace = (spaceId) => {
    // Save to localStorage for persistence (optional, but good for context)
    localStorage.setItem('activeSpaceId', spaceId.toString());
    // Navigate to the space route
    navigate(`/space/${spaceId}`);
  };

  return (
    <div className="h-screen w-full bg-gray-900">
      <SpaceSelector onSelectSpace={handleSelectSpace} />
    </div>
  );
};

export default Dashboard;