import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquare, FileText, X, Plus, Sparkles,
  GitBranch, ArrowRight, Upload, TreeDeciduous,
  ChevronRight, Loader2, Minimize2, Maximize2
} from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

// --- UTILS ---
function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// --- COMPONENTS ---

// 1. Mind Map Card (The individual chat columns)
const MindMapCard = ({ title, children, onClose, isRoot }) => (
  <motion.div
    initial={{ opacity: 0, x: 20, scale: 0.95 }}
    animate={{ opacity: 1, x: 0, scale: 1 }}
    exit={{ opacity: 0, scale: 0.9 }}
    className={cn(
      "flex-shrink-0 w-[400px] max-h-[80vh] flex flex-col rounded-3xl overflow-hidden",
      "bg-[#1c1c1e]/60 backdrop-blur-xl border border-white/10 shadow-2xl transition-all",
      "hover:bg-[#1c1c1e]/70 hover:border-white/20"
    )}
  >
    {/* Header */}
    <div className="h-14 flex items-center justify-between px-6 border-b border-white/10 bg-white/5">
      <div className="flex items-center gap-2">
        {isRoot ? <MessageSquare size={16} className="text-blue-400" /> : <GitBranch size={16} className="text-purple-400" />}
        <span className="text-sm font-semibold text-white/90 truncate max-w-[200px]">{title}</span>
      </div>
      {!isRoot && (
        <button onClick={onClose} className="text-white/40 hover:text-white transition-colors">
          <X size={16} />
        </button>
      )}
    </div>

    {/* Content */}
    <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
      {children}
    </div>
  </motion.div>
);

// --- MAIN APPLICATION ---
export default function NexusRAG() {
  // --- STATE ---
  const [view, setView] = useState('chat'); // 'chat' | 'document'
  const [documents, setDocuments] = useState([]);
  const [isUploading, setIsUploading] = useState(false);

  // General Chat
  const [messages, setMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);

  // Document & Threads
  const [currentDoc, setCurrentDoc] = useState(null);
  const [docThreads, setDocThreads] = useState([]);

  // --- MIND MAP STATE (The Fluid UI) ---
  // We treat the conversation as an array of columns.
  // Index 0 is the root thread. Index 1+ are branches.
  const [isMapOpen, setIsMapOpen] = useState(false);
  const [mapColumns, setMapColumns] = useState([]); // Array of Thread Objects

  // --- API FETCHING ---
  useEffect(() => { fetchDocuments(); }, []);

  const fetchDocuments = async () => {
    try {
      const res = await fetch('/api/documents');
      const data = await res.json();
      setDocuments(data.documents || []);
    } catch (err) { console.error(err); }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      await fetch('/api/upload', { method: 'POST', body: formData });
      await fetchDocuments();
    } finally { setIsUploading(false); }
  };

  const openDocument = async (doc) => {
    setCurrentDoc(doc);
    setView('document');
    setDocThreads([]);
    try {
      const res = await fetch(`/api/documents/${doc.id}/threads`);
      const data = await res.json();
      setDocThreads(data.threads || []);
    } catch (err) { console.error(err); }
  };

  // --- CHAT LOGIC ---
  const sendChatMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    const text = chatInput;
    setChatInput('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setIsChatLoading(true);
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.response, source: data.source }]);
    } finally { setIsChatLoading(false); }
  };

  // --- MIND MAP LOGIC ---

  // 1. Open a thread (Root Column)
  const openThreadInMap = async (threadSummary) => {
    setIsMapOpen(true);
    setMapColumns([]); // Clear previous map

    try {
      const res = await fetch(`/api/threads/${threadSummary.id}`);
      const data = await res.json();
      // Initialize map with just the root thread
      setMapColumns([data.thread || threadSummary]);
    } catch (err) { console.error(err); }
  };

  // 2. Dig Deeper (Create/Fetch Branch)
  const handleDigDeeper = async (parentThreadIndex, messageId) => {
    // Optimistic UI: Add a loading placeholder column
    const placeholderBranch = {
        id: `temp-${Date.now()}`,
        title: "Digging Deeper...",
        isLoading: true,
        messages: []
    };

    // Remove any existing branches to the right of the current level (mind map logic: one active branch per level)
    const newColumns = mapColumns.slice(0, parentThreadIndex + 1);
    setMapColumns([...newColumns, placeholderBranch]);

    // Simulate API delay or fetch actual branch logic here
    // In a real app, you might check if a branch already exists for this messageId
    // For now, we create a fresh "branch" context
    setTimeout(() => {
        setMapColumns(prev => {
            const updated = [...prev];
            updated[parentThreadIndex + 1] = {
                id: `branch-${messageId}`,
                title: "Deep Dive",
                isLoading: false,
                parentId: messageId,
                messages: [{ role: 'assistant', content: "I've opened a new branch to discuss this specific point. What details would you like to clarify?" }]
            };
            return updated;
        });
    }, 600);
  };

  // 3. Send Message in a specific column
  const sendMessageInColumn = async (columnIndex, text) => {
    if (!text.trim()) return;

    // Update UI immediately
    setMapColumns(prev => {
        const updated = [...prev];
        const column = { ...updated[columnIndex] };
        column.messages = [...(column.messages || []), { role: 'user', content: text, user: 'Me' }];
        updated[columnIndex] = column;
        return updated;
    });

    // Simulate AI Reply for the demo (Replace with your actual API endpoint)
    setTimeout(() => {
        setMapColumns(prev => {
            const updated = [...prev];
            const column = { ...updated[columnIndex] };
            column.messages = [...(column.messages || []), {
                role: 'assistant',
                content: "Here is more context on that topic based on the document..."
            }];
            updated[columnIndex] = column;
            return updated;
        });
    }, 1000);
  };

  return (
    <div className="flex h-screen w-full bg-black text-white font-sans overflow-hidden">

      {/* BACKGROUND (The Context) */}
      <div className={cn("flex h-full w-full transition-all duration-500", isMapOpen ? "scale-[0.98] opacity-50 blur-[2px]" : "")}>
          {/* SIDEBAR */}
          <nav className="w-20 lg:w-64 border-r border-white/10 bg-black flex flex-col">
            <div className="p-6 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
                <Sparkles size={16} className="text-white" />
              </div>
              <span className="font-bold text-lg hidden lg:block">Nexus</span>
            </div>

            <div className="px-4 space-y-2">
                <button onClick={() => setView('chat')} className={cn("w-full flex items-center gap-3 px-3 py-3 rounded-xl", view === 'chat' ? "bg-blue-600" : "text-gray-400 hover:bg-white/5")}>
                    <MessageSquare size={18} /> <span className="hidden lg:block">Chat</span>
                </button>
                <div className="h-px bg-white/10 my-2" />
                {documents.map(doc => (
                    <button key={doc.id} onClick={() => openDocument(doc)} className={cn("w-full flex items-center gap-3 px-3 py-3 rounded-xl text-left truncate", currentDoc?.id === doc.id && view === 'document' ? "bg-white/10 text-white" : "text-gray-400 hover:bg-white/5")}>
                        <FileText size={18} /> <span className="hidden lg:block truncate">{doc.filename}</span>
                    </button>
                ))}
                 <label className="flex items-center justify-center gap-2 w-full py-3 rounded-xl border border-dashed border-gray-700 text-gray-500 hover:border-blue-500 hover:text-blue-500 cursor-pointer">
                    {isUploading ? <Loader2 className="animate-spin" size={16}/> : <Upload size={16} />}
                    <input type="file" className="hidden" onChange={handleFileUpload} />
                </label>
            </div>
          </nav>

          {/* MAIN CONTENT */}
          <main className="flex-1 flex bg-[#050505] relative">
            {view === 'chat' ? (
                // GENERAL CHAT VIEW
                <div className="w-full max-w-3xl mx-auto flex flex-col p-6">
                    <div className="flex-1 overflow-y-auto space-y-6 pb-4">
                        {messages.map((msg, i) => (
                            <div key={i} className={cn("flex gap-4", msg.role === 'user' ? "flex-row-reverse" : "")}>
                                <div className={cn("p-4 rounded-2xl max-w-[80%]", msg.role === 'user' ? "bg-blue-600" : "bg-[#1c1c1e] border border-white/10")}>
                                    {msg.content}
                                </div>
                            </div>
                        ))}
                    </div>
                    <form onSubmit={sendChatMessage} className="relative">
                        <input value={chatInput} onChange={e => setChatInput(e.target.value)} className="w-full bg-[#1c1c1e] border border-white/10 rounded-full px-6 py-4 focus:outline-none focus:border-blue-500" placeholder="Ask anything..." />
                    </form>
                </div>
            ) : (
                // DOCUMENT VIEW
                <div className="w-full h-full flex">
                    {currentDoc && (
                        <iframe src={`/api/documents/${currentDoc.id}/content`} className="w-1/2 h-full border-r border-white/10" />
                    )}
                    <div className="w-1/2 p-6 overflow-y-auto">
                        <h3 className="text-xs font-bold text-gray-500 uppercase mb-4">Threads</h3>
                        {docThreads.map(thread => (
                            <div key={thread.id} onClick={() => openThreadInMap(thread)} className="group relative pl-6 pb-6 border-l border-white/10 cursor-pointer">
                                <div className="absolute -left-[5px] top-0 w-2.5 h-2.5 rounded-full bg-blue-500 ring-4 ring-black" />
                                <div className="p-4 rounded-xl bg-[#1c1c1e] border border-white/5 hover:bg-white/5 hover:border-blue-500/30 transition-all">
                                    <h4 className="font-medium text-gray-200">{thread.title}</h4>
                                    <p className="text-xs text-gray-500 mt-1">Click to view in Mind Map</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
          </main>
      </div>

      {/* --- FLUID MIND MAP OVERLAY --- */}
      <AnimatePresence>
        {isMapOpen && (
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-50 flex flex-col bg-black/40 backdrop-blur-md"
            >
                {/* Overlay Header */}
                <div className="h-16 flex items-center justify-between px-8">
                    <div className="flex items-center gap-2">
                        <span className="bg-blue-500/20 text-blue-400 px-2 py-1 rounded text-xs font-bold uppercase tracking-wider">Mind Map Mode</span>
                    </div>
                    <button onClick={() => setIsMapOpen(false)} className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors">
                        <Minimize2 size={16} />
                    </button>
                </div>

                {/* Horizontal Scroll Container (The Canvas) */}
                <div className="flex-1 overflow-x-auto overflow-y-hidden p-8 flex items-center gap-8 custom-scrollbar">

                    {mapColumns.map((col, colIndex) => (
                        <React.Fragment key={col.id || colIndex}>

                            {/* Render Arrow Connector if not first column */}
                            {colIndex > 0 && (
                                <motion.div
                                    initial={{ width: 0, opacity: 0 }}
                                    animate={{ width: 'auto', opacity: 1 }}
                                    className="text-white/20 flex flex-col items-center justify-center"
                                >
                                    <ArrowRight size={24} />
                                </motion.div>
                            )}

                            {/* Render The Column Card */}
                            <MindMapCard
                                title={col.title}
                                isRoot={colIndex === 0}
                                onClose={() => {
                                    // Close this column and all after it
                                    setMapColumns(prev => prev.slice(0, colIndex));
                                }}
                            >
                                {col.isLoading ? (
                                    <div className="h-40 flex items-center justify-center text-gray-500 gap-2">
                                        <Loader2 className="animate-spin" /> Generating Branch...
                                    </div>
                                ) : (
                                    <>
                                        {col.messages?.map((msg, idx) => (
                                            <div key={idx} className="group flex flex-col gap-1">
                                                <div className={cn("flex gap-2", msg.role === 'user' ? "flex-row-reverse" : "")}>
                                                    {/* Avatar */}
                                                    <div className={cn("w-6 h-6 rounded-full flex items-center justify-center text-[10px]", msg.role === 'assistant' ? "bg-white/10 text-blue-400" : "bg-purple-500/20 text-purple-400")}>
                                                        {msg.role === 'assistant' ? <Sparkles size={10}/> : "ME"}
                                                    </div>

                                                    {/* Bubble */}
                                                    <div className={cn(
                                                        "p-3 rounded-xl text-sm max-w-[90%] border",
                                                        msg.role === 'assistant' ? "bg-black/20 border-white/5 text-gray-300" : "bg-blue-600/20 border-blue-500/30 text-blue-100"
                                                    )}>
                                                        {msg.content}
                                                    </div>
                                                </div>

                                                {/* DIG DEEPER ACTION */}
                                                {msg.role === 'assistant' && (
                                                    <div className="ml-8">
                                                        <button
                                                            onClick={() => handleDigDeeper(colIndex, msg.id)}
                                                            className={cn(
                                                                "opacity-0 group-hover:opacity-100 transition-opacity text-[10px] flex items-center gap-1 px-2 py-1 rounded-full",
                                                                "text-green-400 hover:bg-green-500/10 border border-transparent hover:border-green-500/30"
                                                            )}
                                                        >
                                                            <GitBranch size={12} /> Dig Deeper
                                                        </button>
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </>
                                )}

                                {/* Input for this specific column */}
                                {!col.isLoading && (
                                    <div className="mt-4 pt-4 border-t border-white/5">
                                        <form
                                            onSubmit={(e) => {
                                                e.preventDefault();
                                                const input = e.target.elements.input;
                                                sendMessageInColumn(colIndex, input.value);
                                                input.value = "";
                                            }}
                                            className="relative"
                                        >
                                            <input
                                                name="input"
                                                placeholder="Reply here..."
                                                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2 text-sm focus:outline-none focus:border-blue-500/50"
                                            />
                                        </form>
                                    </div>
                                )}
                            </MindMapCard>
                        </React.Fragment>
                    ))}

                    {/* Spacer for comfortable scrolling */}
                    <div className="w-20 flex-shrink-0" />
                </div>
            </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}