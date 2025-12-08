import React, { useState, useEffect } from 'react';
import { Box, Plus, ArrowRight, Folder, Terminal, Loader2 } from 'lucide-react';
import { cn } from './lib/utils'; // Assuming this exists from previous refactor

export default function SpaceSelector({ onSelectSpace }) {
  const [spaces, setSpaces] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);

  // Form State
  const [newSpaceName, setNewSpaceName] = useState('');
  const [newSpaceDesc, setNewSpaceDesc] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Initial Fetch
  useEffect(() => {
    fetchSpaces();
  }, []);

  const fetchSpaces = async () => {
    try {
      const res = await fetch('/api/spaces');
      const data = await res.json();
      setSpaces(data.spaces || []);
    } catch (err) {
      console.error("Failed to load spaces", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateSpace = async (e) => {
    e.preventDefault();
    if (!newSpaceName.trim()) return;

    setIsSubmitting(true);
    try {
      const res = await fetch('/api/spaces', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newSpaceName,
          description: newSpaceDesc
        })
      });
      const data = await res.json();

      if (data.space_id) {
        // Refresh list and close form
        await fetchSpaces();
        setIsCreating(false);
        setNewSpaceName('');
        setNewSpaceDesc('');
      }
    } catch (err) {
      console.error("Error creating space", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-black font-mono flex flex-col items-center justify-center p-8">

      {/* HEADER */}
      <div className="mb-12 text-center space-y-4">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-black text-white border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            <Box size={32} />
        </div>
        <h1 className="text-4xl font-black tracking-tighter">NEXUS_OS</h1>
        <p className="opacity-60 text-sm">SELECT_WORKSPACE_TO_INITIALIZE</p>
      </div>

      {/* MAIN GRID */}
      <div className="w-full max-w-5xl grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

        {/* CREATE NEW CARD */}
        <button
          onClick={() => setIsCreating(true)}
          className="group relative h-48 border-2 border-dashed border-gray-400 flex flex-col items-center justify-center gap-4 transition-all hover:border-black hover:bg-white hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]"
        >
          <div className="p-3 rounded-full bg-gray-100 group-hover:bg-black group-hover:text-white transition-colors">
            <Plus size={24} />
          </div>
          <span className="font-bold text-sm uppercase tracking-wider">Create New Space</span>
        </button>

        {/* LOADING STATE */}
        {isLoading && (
           <div className="col-span-full flex justify-center py-12 opacity-50">
             <Loader2 className="animate-spin" />
           </div>
        )}

        {/* EXISTING SPACES */}
        {spaces.map((space) => (
          <div
            key={space.id}
            onClick={() => onSelectSpace(space.id)}
            className="cursor-pointer h-48 bg-white border-2 border-black p-6 flex flex-col justify-between transition-all hover:-translate-y-1 hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]"
          >
            <div>
              <div className="flex justify-between items-start mb-2">
                 <Folder size={20} />
                 <span className="text-xs opacity-40 font-bold">ID: {space.id}</span>
              </div>
              <h3 className="text-xl font-bold truncate">{space.name}</h3>
              <p className="text-xs mt-2 opacity-60 line-clamp-2">{space.description}</p>
            </div>

            <div className="flex items-center gap-2 text-xs font-bold uppercase mt-4">
              <span>Enter_System</span> <ArrowRight size={12} />
            </div>
          </div>
        ))}
      </div>

      {/* CREATE MODAL OVERLAY */}
      {isCreating && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border-2 border-black w-full max-w-md shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] p-8">
             <div className="flex items-center gap-3 mb-6 border-b-2 border-black pb-4">
                <Terminal size={20} />
                <h2 className="font-bold text-lg">CONFIGURE_NEW_SPACE</h2>
             </div>

             <form onSubmit={handleCreateSpace} className="space-y-4">
                <div>
                   <label className="block text-xs font-bold uppercase mb-2">Space Name</label>
                   <input
                     autoFocus
                     value={newSpaceName}
                     onChange={(e) => setNewSpaceName(e.target.value)}
                     className="w-full border-2 border-black p-3 bg-gray-50 focus:bg-white focus:outline-none focus:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] transition-all font-mono"
                     placeholder="e.g. CS101_Algorithms"
                   />
                </div>
                <div>
                   <label className="block text-xs font-bold uppercase mb-2">Description</label>
                   <textarea
                     value={newSpaceDesc}
                     onChange={(e) => setNewSpaceDesc(e.target.value)}
                     className="w-full border-2 border-black p-3 bg-gray-50 focus:bg-white focus:outline-none focus:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] transition-all font-mono h-24 resize-none"
                     placeholder="Project goals..."
                   />
                </div>

                <div className="flex gap-4 pt-4">
                  <button
                    type="button"
                    onClick={() => setIsCreating(false)}
                    className="flex-1 py-3 font-bold border-2 border-transparent hover:bg-gray-100"
                  >
                    CANCEL
                  </button>
                  <button
                    type="submit" 
                    disabled={isSubmitting}
                    className="flex-1 py-3 bg-black text-white font-bold border-2 border-black hover:bg-gray-800 disabled:opacity-50"
                  >
                    {isSubmitting ? 'INITIALIZING...' : 'CREATE SPACE'}
                  </button>
                </div>
             </form>
          </div>
        </div>
      )}

    </div>
  );
}