import React from 'react';
import { FileText, ArrowRight } from 'lucide-react';

export const DocumentInterface = ({
  currentDoc,
  docThreads,
  openThreadInMap
}) => {
  return (
    <div className="w-full h-full flex">
        <div className="w-1/2 h-full border-r-2 flex items-center justify-center flex-col border-black bg-gray-100">
            {currentDoc ? (
                <iframe src={`/api/documents/${currentDoc.id}/content`} className="w-full h-full border-none" />
            ) : (
                <div className="p-8 border-2 border-dashed border-gray-300 text-gray-400 text-center">
                    <FileText size={48} className="mx-auto mb-4"/>
                    <p>PDF_RENDERER_MOUNTED</p>
                </div>
            )}
        </div>

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
                    <div className="flex items-center gap-2 text-xs opacity-60 mt-4 group-hover:opacity-100">
                        <span>Explore</span> <ArrowRight size={12}/>
                    </div>
                </div>
            ))}
        </div>
    </div>
  );
};