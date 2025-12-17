import React from 'react';
import { BookOpenCheck, Terminal, FileText, Upload, Loader2, LogOut, Sparkles } from 'lucide-react';
import { cn } from '../lib/utils';

export const Sidebar = ({
  view,
  setView,
  documents,
  currentDoc,
  openDocument,
  isUploading,
  handleFileUpload,
  onExit
}) => {
  return (
    <nav className="w-20 lg:w-64 border-r-2 flex flex-col border-black bg-gray-50">
      <div className="h-16 flex items-center gap-3 px-6 border-b-2 border-black bg-white">
        <div className="relative group">
          <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 to-purple-500 rounded blur opacity-30 group-hover:opacity-60 transition duration-500"></div>
          <div className="relative w-8 h-8 flex items-center justify-center border shadow-[2px_2px_0px_0px_rgba(0,0,0,0.5)] bg-black text-white border-black">
            <BookOpenCheck size={18} />
          </div>
        </div>
        <span className="font-bold text-lg hidden lg:block tracking-tight">Clark</span>
      </div>

      <div className="px-4 py-6 space-y-4 flex flex-col h-full">
          {/* View Switcher */}
          <button onClick={() => setView('chat')}
              className={cn(
                  "w-full flex items-center gap-3 px-4 py-3 border-2 transition-all active:translate-x-[2px] active:translate-y-[2px] active:shadow-none",
                  "bg-white text-black border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:bg-gray-100",
                  view === 'chat' && "bg-black text-white"
              )}>
              <Terminal size={18} /> <span className="hidden lg:block font-bold">TERMINAL</span>
          </button>

          <div className="h-px opacity-20 my-4 bg-black" />

          {/* Documents List */}
          <div className="space-y-2 flex-1 overflow-y-auto">
              <span className="text-xs font-bold uppercase px-2 opacity-50">Data Sources</span>
              {documents.map(doc => (
                  <button key={doc.id} onClick={() => openDocument(doc)}
                      className={cn(
                          "w-full flex items-center gap-3 px-3 py-2 text-left truncate border border-transparent transition-all",
                          "hover:border-black hover:bg-white",
                          currentDoc?.id === doc.id && view === 'document'
                              ? "font-bold bg-white border-black"
                              : "opacity-60 hover:opacity-100"
                      )}>
                      <FileText size={16} /> <span className="hidden lg:block truncate text-sm">{doc.filename}</span>
                  </button>
              ))}
          </div>

          {/* Upload Button */}
          <label className="mt-auto flex items-center justify-center gap-2 w-full py-3 border-2 border-dashed cursor-pointer transition-colors border-gray-400 text-gray-500 hover:border-black hover:text-black hover:bg-white">
              {isUploading ? <Loader2 className="animate-spin" size={16}/> : <Upload size={16} />}
              <span className="text-sm font-bold hidden lg:block">UPLOAD_PDF</span>
              <input type="file" className="hidden" accept="application/pdf" onChange={handleFileUpload} />
          </label>

          {/* Exit Button */}
          <button 
            onClick={onExit}
            className="flex items-center justify-center gap-2 w-full py-3 border-2 border-black bg-white text-black hover:bg-red-50 hover:border-red-500 hover:text-red-500 transition-colors font-bold text-sm shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none"
          >
            <LogOut size={16} />
            <span className="hidden lg:block">EXIT_SPACE</span>
          </button>
      </div>
    </nav>
  );
};