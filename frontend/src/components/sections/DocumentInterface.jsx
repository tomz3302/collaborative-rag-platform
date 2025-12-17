import React, { useState, useEffect } from 'react';
import { FileText, ArrowRight, Loader } from 'lucide-react';
import { apiFetch } from '../../utils/api';

export const DocumentInterface = ({
  currentDoc,
  docThreads,
  openThreadInMap,
  spaceId
}) => {
  // 1. State to hold the "Real" Supabase Link
  const [pdfUrl, setPdfUrl] = useState(null);
  const [loading, setLoading] = useState(false);

  // 2. Effect: Whenever the user clicks a document, fetch its real Link
  useEffect(() => {
    if (currentDoc) {
      setLoading(true);
      apiFetch(`/api/documents/${currentDoc.id}/content?space_id=${spaceId}`)
        .then(res => res.json())
        .then(data => {
            // "data.url" is the Supabase link we want
            setPdfUrl(data.url);
            setLoading(false);
        })
        .catch(err => {
            console.error("Failed to load PDF url", err);
            setLoading(false);
        });
    } else {
        setPdfUrl(null);
    }
  }, [currentDoc]);

  return (
    <div className="w-full h-full flex">
        {/* LEFT SIDE: PDF VIEWER */}
        <div className="w-1/2 h-full border-r-2 flex items-center justify-center flex-col border-black bg-gray-100">
            {currentDoc ? (
                loading ? (
                    // Show spinner while fetching the link
                    <div className="flex flex-col items-center opacity-50">
                        <Loader className="animate-spin mb-2" />
                        <span className="font-mono text-xs">RESOLVING_LINK...</span>
                    </div>
                ) : (
                    // 3. Render the iframe using the REAL Link (pdfUrl)
                    <iframe 
                        src={pdfUrl} 
                        className="w-full h-full border-none" 
                        title="PDF Viewer"
                    />
                )
            ) : (
                <div className="p-8 border-2 border-dashed border-gray-300 text-gray-400 text-center">
                    <FileText size={48} className="mx-auto mb-4"/>
                    <p className="font-mono text-sm">PDF_RENDERER_MOUNTED</p>
                    <p className="text-xs mt-2 opacity-50">Select a document to view</p>
                </div>
            )}
        </div>

        {/* RIGHT SIDE: THREADS (No changes needed here) */}
        <div className="w-1/2 p-0 overflow-y-auto bg-white">
            <div className="h-16 border-b-2 flex items-center px-6 border-black bg-gray-50">
                <h3 className="text-sm font-bold uppercase tracking-wider">Threads</h3>
            </div>
            {docThreads.length === 0 && (
                <div className="p-8 text-center opacity-50 font-mono text-sm">NO_THREADS_FOUND</div>
            )}
            {docThreads.map(thread => (
                <div key={thread.id} onClick={() => openThreadInMap(thread)}
                    className="group relative p-6 border-b cursor-pointer transition-colors border-black hover:bg-black hover:text-white">
                    <div className="flex justify-between items-start mb-2">
                        <span className="text-xs font-bold border px-2 py-0.5 border-black group-hover:border-white">PAGE_{thread.page_number}</span>
                        <span className="text-xs font-mono opacity-60">ID: {thread.id}</span>
                    </div>
                    <h4 className="font-bold text-lg mb-1">{thread.title}</h4>
                    {thread.user && (
                        <div className="text-xs opacity-70 mt-2 font-mono">
                            Created by: <span className="font-bold">{thread.user}</span>
                        </div>
                    )}
                    <div className="flex items-center gap-2 text-xs opacity-60 mt-4 group-hover:opacity-100">
                        <span>Explore</span> <ArrowRight size={12}/>
                    </div>
                </div>
            ))}
        </div>
    </div>
  );
};