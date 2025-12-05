import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquare, FileText, X, Plus, Sparkles,
  GitBranch, ArrowRight, Upload, TreeDeciduous,
  ChevronRight, Loader2, Minimize2, Maximize2, Terminal,
  Box, Moon, Sun
} from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

// --- UTILS ---
function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// --- COMPONENTS ---

// 1. Pixelated Loader (3 bouncing squares)
const PixelLoader = () => (
  <div className="flex items-center gap-2 h-6">
    <div className="w-2 h-2 bg-current animate-[bounce_1s_infinite_0ms]"></div>
    <div className="w-2 h-2 bg-current animate-[bounce_1s_infinite_200ms]"></div>
    <div className="w-2 h-2 bg-current animate-[bounce_1s_infinite_400ms]"></div>
  </div>
);

// 2. Glitch Effect Styles
const GlitchStyles = () => (
  <style>{`
    @keyframes glitch-anim-1 {
      0% { clip-path: inset(20% 0 80% 0); transform: translate(-2px, 1px); }
      20% { clip-path: inset(60% 0 10% 0); transform: translate(2px, -1px); }
      40% { clip-path: inset(40% 0 50% 0); transform: translate(-2px, 2px); }
      60% { clip-path: inset(80% 0 5% 0); transform: translate(2px, -2px); }
      80% { clip-path: inset(10% 0 60% 0); transform: translate(-1px, 1px); }
      100% { clip-path: inset(30% 0 70% 0); transform: translate(0); }
    }
    .glitching {
      animation: glitch-anim-1 0.3s infinite linear alternate-reverse;
    }
  `}</style>
);

// 3. Mind Map Card (Refactored for Dark Mode support)
const MindMapCard = ({ title, children, onClose, isRoot }) => (
  <motion.div
    initial={{ opacity: 0, x: 20, scale: 0.95 }}
    animate={{ opacity: 1, x: 0, scale: 1 }}
    exit={{ opacity: 0, scale: 0.9 }}
    className={cn(
      "flex-shrink-0 w-[400px] max-h-[80vh] flex flex-col overflow-hidden transition-colors duration-200",
      // Neo-Brutalist Styling (Light/Dark)
      "border-2",
      "bg-white text-black border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]",
      "dark:bg-zinc-900 dark:text-white dark:border-white dark:shadow-[8px_8px_0px_0px_rgba(255,255,255,1)]"
    )}
  >
    {/* Header */}
    <div className="h-14 flex items-center justify-between px-4 border-b-2 border-inherit bg-gray-50 dark:bg-zinc-800">
      <div className="flex items-center gap-2">
        {isRoot ? <Terminal size={18} /> : <GitBranch size={18} />}
        <span className="text-sm font-bold uppercase tracking-wider truncate max-w-[200px]">{title}</span>
      </div>
      {!isRoot && (
        <button onClick={onClose} className="hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors p-1 border border-transparent hover:border-inherit">
          <X size={16} />
        </button>
      )}
    </div>

    {/* Content */}
    <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar bg-white dark:bg-zinc-900">
      {children}
    </div>
  </motion.div>
);

// --- MAIN APPLICATION ---
export default function NexusRAG() {
  // --- STATE ---
  const [darkMode, setDarkMode] = useState(false);
  const [isGlitching, setIsGlitching] = useState(false);

  const [view, setView] = useState('chat'); // 'chat' | 'document'
  const [documents, setDocuments] = useState([]);
  const [isUploading, setIsUploading] = useState(false);

  // General Chat
  const [messages, setMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [generalThreadId, setGeneralThreadId] = useState(null);
  const [isChatLoading, setIsChatLoading] = useState(false);

  // Document & Threads
  const [currentDoc, setCurrentDoc] = useState(null);
  const [docThreads, setDocThreads] = useState([]);

  // --- MIND MAP STATE ---
  const [isMapOpen, setIsMapOpen] = useState(false);
  const [mapColumns, setMapColumns] = useState([]);
  const [branchingFromId, setBranchingFromId] = useState(null);

  // --- API FETCHING ---
  useEffect(() => { fetchDocuments(); }, []);

  const toggleTheme = () => {
    setIsGlitching(true);
    setTimeout(() => {
        setDarkMode(!darkMode);
        setIsGlitching(false);
    }, 300); // Glitch duration
  };

  const fetchDocuments = async () => {
    try {
      const res = await fetch('/api/documents');
      const data = await res.json();
      setDocuments(data.documents || []);
    } catch (err) { console.error("API Error", err); }
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
    } catch(err) {
        console.error("Upload Error", err);
    } finally {
        setIsUploading(false);
    }
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
            body: JSON.stringify({ text, thread_id: generalThreadId })
        });
        const data = await res.json();

        if (data.thread_id) setGeneralThreadId(data.thread_id);

        setMessages(prev => [...prev, {
            role: 'assistant',
            content: data.response,
            source: data.source
        }]);
    } catch (err) {
        setMessages(prev => [...prev, { role: 'assistant', content: "Error: Could not reach the server." }]);
    } finally {
        setIsChatLoading(false);
    }
  };

  // --- MIND MAP LOGIC ---
  const openThreadInMap = async (threadSummary) => {
    setIsMapOpen(true);
    setMapColumns([]);

    try {
        // Fetch full thread details
        const res = await fetch(`/api/threads/${threadSummary.id}`);
        const data = await res.json();

        const rootThread = data.thread || threadSummary;
        // Ensure root thread has required props for map logic
        rootThread.isLoading = false;

        setMapColumns([rootThread]);
    } catch (err) { console.error(err); }
  };

  const handleDigDeeper = (parentThreadIndex, messageId) => {
    // 1. Create a loading placeholder
    const placeholderBranch = {
        id: `temp-${Date.now()}`,
        title: "Digging Deeper...",
        isLoading: true,
        messages: [],
        parentId: messageId // Track relationship
    };

    // 2. Cut off any branches to the right, append placeholder
    const newColumns = mapColumns.slice(0, parentThreadIndex + 1);
    setMapColumns([...newColumns, placeholderBranch]);

    // 3. Mark the message ID we are branching from so the next send uses the branch endpoint
    setBranchingFromId(messageId);
  };

  const sendMessageInColumn = async (columnIndex, text) => {
    if (!text.trim()) return;

    // Optimistic UI Update
    setMapColumns(prev => {
        const updated = [...prev];
        const column = { ...updated[columnIndex] };
        column.messages = [...(column.messages || []), { role: 'user', content: text, user: 'Me' }];
        updated[columnIndex] = column;
        return updated;
    });

    const activeColumn = mapColumns[columnIndex];
    const isBranching = activeColumn.isLoading === true || activeColumn.id.toString().startsWith('temp-');

    // Determine Parent ID:
    // If we are in a temporary/loading column, we are branching from 'branchingFromId'.
    // If we are just replying to an existing thread column, use that thread's ID.
    const parentId = isBranching ? branchingFromId : null; // Logic depends on backend requirement
    const threadIdToUse = isBranching ? mapColumns[columnIndex - 1].id : activeColumn.id;

    try {
        let res;

        if (isBranching) {
            // Create NEW Branch
            res = await fetch(`/api/threads/${threadIdToUse}/branch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: text,
                    parent_message_id: branchingFromId,
                    user_id: 1
                })
            });
        } else {
            // Reply to EXISTING thread
            res = await fetch(`/api/threads/${threadIdToUse}/messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: text, user: 'Anonymous' })
            });
        }

        if (res.ok) {
            // In a real scenario, the backend returns the new thread/messages.
            // For now, we simulate the "AI Reply" coming back by fetching the updated thread state
            // or just processing the response if your API returns the next message immediately.

            // Note: If we created a branch, we need to replace the "temp" column with the real new thread.
            // Simplified logic: Append AI response manually for UI responsiveness if API doesn't return full thread.

            const data = await res.json(); // Assuming returns { response: "AI text" } or similar

            setMapColumns(prev => {
                const updated = [...prev];
                // If it was a temp branch, solidify it
                if (isBranching) {
                    updated[columnIndex] = {
                        ...updated[columnIndex],
                        id: data.new_thread_id || `branch-${Date.now()}`, // Backend should return this
                        title: "Deep Dive",
                        isLoading: false,
                    };
                }

                // Append AI message
                const column = updated[columnIndex];
                column.messages = [...column.messages, {
                    role: 'assistant',
                    content: data.response || "Analysis complete.", // Fallback
                }];
                return updated;
            });
        }
    } catch (err) { console.error("Reply Error", err); }
  };

  return (
    // DARK MODE WRAPPER
    <div className={cn("w-full h-screen transition-colors duration-200 overflow-hidden", darkMode ? "dark bg-black" : "bg-white")}>
      <GlitchStyles />

      {/* BACKGROUND CONTEXT */}
      <div className={cn(
          "flex h-full w-full font-mono transition-all duration-300",
          isMapOpen ? "opacity-20 pointer-events-none grayscale" : "",
          isGlitching ? "glitching" : "",
          "bg-white text-black dark:bg-black dark:text-white"
        )}>

          {/* SIDEBAR */}
          <nav className={cn(
              "w-20 lg:w-64 border-r-2 flex flex-col transition-colors",
              "border-black bg-gray-50",
              "dark:border-white dark:bg-zinc-900"
            )}>
            <div className={cn(
                "h-16 flex items-center gap-3 px-6 border-b-2 transition-colors",
                "border-black bg-white",
                "dark:border-white dark:bg-black"
            )}>
              <div className={cn(
                  "w-8 h-8 flex items-center justify-center border shadow-[2px_2px_0px_0px_rgba(0,0,0,0.5)] transition-colors",
                  "bg-black text-white border-black",
                  "dark:bg-white dark:text-black dark:border-white"
                )}>
                <Box size={18} />
              </div>
              <span className="font-bold text-lg hidden lg:block tracking-tight">NEXUS_API</span>
            </div>

            <div className="px-4 py-6 space-y-4">
                {/* View Switcher */}
                <button onClick={() => setView('chat')}
                    className={cn(
                        "w-full flex items-center gap-3 px-4 py-3 border-2 transition-all active:translate-x-[2px] active:translate-y-[2px] active:shadow-none",
                        // Light
                        "bg-white text-black border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:bg-gray-100",
                        // Dark
                        "dark:bg-black dark:text-white dark:border-white dark:shadow-[4px_4px_0px_0px_rgba(255,255,255,1)] dark:hover:bg-zinc-900",
                        view === 'chat' && "bg-black text-white dark:bg-white dark:text-black"
                    )}>
                    <Terminal size={18} /> <span className="hidden lg:block font-bold">TERMINAL</span>
                </button>

                <div className={cn("h-px opacity-20 my-4", "bg-black dark:bg-white")} />

                {/* Documents List */}
                <div className="space-y-2">
                    <span className="text-xs font-bold uppercase px-2 opacity-50">Data Sources</span>
                    {documents.map(doc => (
                        <button key={doc.id} onClick={() => openDocument(doc)}
                            className={cn(
                                "w-full flex items-center gap-3 px-3 py-2 text-left truncate border border-transparent transition-all",
                                "hover:border-black hover:bg-white dark:hover:border-white dark:hover:bg-zinc-800",
                                currentDoc?.id === doc.id && view === 'document'
                                    ? "font-bold bg-white border-black dark:bg-zinc-800 dark:border-white"
                                    : "opacity-60 hover:opacity-100"
                            )}>
                            <FileText size={16} /> <span className="hidden lg:block truncate text-sm">{doc.filename}</span>
                        </button>
                    ))}
                </div>

                {/* Upload Button */}
                 <label className={cn(
                     "mt-4 flex items-center justify-center gap-2 w-full py-3 border-2 border-dashed cursor-pointer transition-colors",
                     "border-gray-400 text-gray-500 hover:border-black hover:text-black hover:bg-white",
                     "dark:border-zinc-600 dark:text-zinc-500 dark:hover:border-white dark:hover:text-white dark:hover:bg-zinc-900"
                 )}>
                    {isUploading ? <Loader2 className="animate-spin" size={16}/> : <Upload size={16} />}
                    <span className="text-sm font-bold">UPLOAD_PDF</span>
                    <input type="file" className="hidden" accept="application/pdf" onChange={handleFileUpload} />
                </label>
            </div>

            {/* Theme Toggle Footer */}
            <div className="mt-auto p-4 border-t-2 border-inherit">
                <button onClick={toggleTheme} className={cn(
                    "w-full py-2 flex items-center justify-center gap-2 text-xs font-bold uppercase border-2 transition-all",
                    "border-black hover:bg-black hover:text-white",
                    "dark:border-white dark:hover:bg-white dark:hover:text-black"
                )}>
                    {darkMode ? <Sun size={14} /> : <Moon size={14} />}
                    {darkMode ? "Light_Mode" : "Dark_Mode"}
                </button>
            </div>
          </nav>

          {/* MAIN CONTENT */}
          <main className={cn("flex-1 flex relative transition-colors", "bg-white dark:bg-black")}>
            {view === 'chat' ? (
                // GENERAL CHAT VIEW
                <div className="w-full max-w-4xl mx-auto flex flex-col p-6 lg:p-12">
                    <div className="flex-1 overflow-y-auto space-y-8 pb-4 custom-scrollbar">
                        {messages.length === 0 && (
                             <div className="h-full flex flex-col items-center justify-center opacity-40 text-center space-y-4">
                                <Box size={64} />
                                <h2 className="text-2xl font-bold">READY TO PARSE</h2>
                                <p className="font-sans max-w-md opacity-70">Initialize a request to start extracting data from your uploaded documents.</p>
                            </div>
                        )}

                        {messages.map((msg, i) => (
                            <div key={i} className={cn("flex gap-4", msg.role === 'user' ? "flex-row-reverse" : "")}>
                                <div className={cn(
                                    "p-6 max-w-[80%] border-2 transition-all shadow-[4px_4px_0px_0px_currentColor]",
                                    msg.role === 'user'
                                        ? "bg-black text-white border-black dark:bg-white dark:text-black dark:border-white"
                                        : "bg-white text-black border-black dark:bg-black dark:text-white dark:border-white"
                                )}>
                                    {msg.role === 'assistant' && (
                                        <div className="mb-2 text-xs font-bold uppercase tracking-wider opacity-50 flex items-center gap-2">
                                            <Terminal size={12}/> API_RESPONSE
                                        </div>
                                    )}
                                    <p className="text-sm leading-relaxed whitespace-pre-wrap font-sans">{msg.content}</p>
                                    {msg.source && (
                                        <div className="mt-4 pt-4 border-t border-dashed border-gray-400 dark:border-zinc-600">
                                            <div className="text-xs font-mono opacity-60">SOURCE: {msg.source}</div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}

                        {/* Loading State */}
                        {isChatLoading && (
                           <div className="flex gap-4">
                               <div className={cn(
                                   "p-6 border-2 shadow-[4px_4px_0px_0px_currentColor]",
                                   "bg-white text-black border-black dark:bg-black dark:text-white dark:border-white"
                               )}>
                                   <div className="mb-2 text-xs font-bold uppercase tracking-wider opacity-50 flex items-center gap-2">
                                        <Terminal size={12}/> PROCESSING
                                    </div>
                                   <PixelLoader />
                               </div>
                           </div>
                        )}
                    </div>

                    {/* INPUT AREA */}
                    <form onSubmit={sendChatMessage} className="relative mt-4">
                        <div className="absolute left-4 top-1/2 -translate-y-1/2 font-bold opacity-50 pointer-events-none">
                            $
                        </div>
                        <input
                            value={chatInput}
                            onChange={e => setChatInput(e.target.value)}
                            className={cn(
                                "w-full border-2 px-10 py-5 text-sm focus:outline-none transition-all font-mono placeholder:opacity-40",
                                "bg-gray-50 border-black focus:bg-white focus:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]",
                                "dark:bg-zinc-900 dark:border-white dark:focus:bg-black dark:focus:shadow-[4px_4px_0px_0px_rgba(255,255,255,1)] dark:placeholder:text-gray-400"
                            )}
                            placeholder="Enter command or query..."
                        />
                        <button type="submit" disabled={isChatLoading} className={cn(
                            "absolute right-4 top-1/2 -translate-y-1/2 p-2 border border-transparent rounded-none transition-colors",
                            "hover:bg-black hover:text-white hover:border-black",
                            "dark:hover:bg-white dark:hover:text-black dark:hover:border-white"
                        )}>
                            <ArrowRight size={20} />
                        </button>
                    </form>
                </div>
            ) : (
                // DOCUMENT VIEW
                <div className="w-full h-full flex">
                    {/* PDF Placeholder */}
                    <div className={cn(
                        "w-1/2 h-full border-r-2 flex items-center justify-center flex-col",
                        "border-black bg-gray-100",
                        "dark:border-white dark:bg-zinc-900"
                    )}>
                        {currentDoc ? (
                            <iframe src={`/api/documents/${currentDoc.id}/content`} className="w-full h-full border-none" />
                        ) : (
                            <div className="p-8 border-2 border-dashed border-gray-300 dark:border-zinc-700 text-gray-400 text-center">
                                <FileText size={48} className="mx-auto mb-4"/>
                                <p>PDF_RENDERER_MOUNTED</p>
                            </div>
                        )}
                    </div>

                    {/* Threads List */}
                    <div className={cn("w-1/2 p-0 overflow-y-auto", "bg-white dark:bg-black")}>
                        <div className={cn("h-16 border-b-2 flex items-center px-6", "border-black bg-gray-50", "dark:border-white dark:bg-zinc-900")}>
                            <h3 className="text-sm font-bold uppercase tracking-wider">Active Threads</h3>
                        </div>
                        {docThreads.length === 0 && (
                            <div className="p-8 text-center opacity-50 font-mono text-sm">NO_THREADS_FOUND</div>
                        )}
                        {docThreads.map(thread => (
                            <div key={thread.id} onClick={() => openThreadInMap(thread)}
                                className={cn(
                                    "group relative p-6 border-b cursor-pointer transition-colors",
                                    "border-black hover:bg-black hover:text-white",
                                    "dark:border-white dark:hover:bg-white dark:hover:text-black"
                                )}>
                                <div className="flex justify-between items-start mb-2">
                                    <span className={cn(
                                        "text-xs font-bold border px-2 py-0.5",
                                        "border-black group-hover:border-white",
                                        "dark:border-white dark:group-hover:border-black"
                                    )}>PAGE_{thread.page_number}</span>
                                    <span className="text-xs font-mono opacity-60">ID: {thread.id}</span>
                                </div>
                                <h4 className="font-bold text-lg mb-1">{thread.title}</h4>
                                <div className="flex items-center gap-2 text-xs opacity-60 mt-4 group-hover:opacity-100">
                                    <span>OPEN_MIND_MAP</span> <ArrowRight size={12}/>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
          </main>
      </div>

      {/* --- NEO-BRUTALIST MIND MAP OVERLAY --- */}
      <AnimatePresence>
        {isMapOpen && (
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className={cn(
                    "fixed inset-0 z-50 flex flex-col backdrop-blur-sm",
                    "bg-white/90 dark:bg-black/90"
                )}
            >
                {/* Overlay Header */}
                <div className={cn(
                    "h-20 flex items-center justify-between px-8 border-b-2",
                    "bg-white border-black",
                    "dark:bg-black dark:border-white"
                )}>
                    <div className="flex items-center gap-4">
                        <div className={cn(
                            "px-3 py-1 text-sm font-bold uppercase tracking-wider shadow-[2px_2px_0px_0px_rgba(0,0,0,0.2)]",
                            "bg-black text-white",
                            "dark:bg-white dark:text-black"
                        )}>
                            Mind_Map_View
                        </div>
                        <div className={cn("h-px w-12", "bg-black dark:bg-white")}></div>
                        <span className="font-mono text-sm opacity-60">Exploring Logic Branch</span>
                    </div>
                    <button onClick={() => setIsMapOpen(false)} className={cn(
                        "w-10 h-10 flex items-center justify-center border-2 transition-all active:translate-x-[2px] active:translate-y-[2px] active:shadow-none",
                        "border-black hover:bg-black hover:text-white shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]",
                        "dark:border-white dark:hover:bg-white dark:hover:text-black dark:shadow-[2px_2px_0px_0px_rgba(255,255,255,1)]"
                    )}>
                        <Minimize2 size={20} />
                    </button>
                </div>

                {/* Canvas */}
                <div className={cn("flex-1 overflow-x-auto overflow-y-hidden p-8 flex items-start gap-12 custom-scrollbar", "bg-gray-50 dark:bg-zinc-950")}>

                    {mapColumns.map((col, colIndex) => (
                        <React.Fragment key={col.id || colIndex}>

                            {/* Connector Arrow */}
                            {colIndex > 0 && (
                                <motion.div
                                    initial={{ width: 0, opacity: 0 }}
                                    animate={{ width: 'auto', opacity: 1 }}
                                    className="pt-32"
                                >
                                    <ArrowRight size={32} className="dark:text-white" />
                                </motion.div>
                            )}

                            {/* Column Card */}
                            <MindMapCard
                                title={col.title}
                                isRoot={colIndex === 0}
                                onClose={() => setMapColumns(prev => prev.slice(0, colIndex))}
                            >
                                {col.isLoading ? (
                                    <div className="h-40 flex flex-col items-center justify-center gap-4 border-2 border-dashed border-gray-300 dark:border-zinc-700 opacity-50">
                                        <PixelLoader />
                                        <span className="text-xs font-bold uppercase">Processing_Request...</span>
                                    </div>
                                ) : (
                                    <>
                                        {col.messages?.map((msg, idx) => (
                                            <div key={idx} className="group flex flex-col gap-2">
                                                <div className={cn(
                                                    "p-4 border-2 text-sm font-sans shadow-[3px_3px_0px_0px_currentColor]",
                                                    msg.role === 'assistant'
                                                        ? "bg-white text-black border-black dark:bg-black dark:text-white dark:border-white"
                                                        : "bg-black text-white border-black dark:bg-white dark:text-black dark:border-white"
                                                )}>
                                                    <div className="text-[10px] font-bold uppercase mb-2 opacity-50">
                                                        {msg.role === 'assistant' ? "System_Output" : "User_Input"}
                                                    </div>
                                                    {msg.content}
                                                </div>

                                                {/* DIG DEEPER ACTION */}
                                                {msg.role === 'assistant' && (
                                                    <div className="flex justify-end">
                                                        <button
                                                            onClick={() => handleDigDeeper(colIndex, msg.id)}
                                                            className={cn(
                                                                "text-xs font-bold flex items-center gap-2 px-3 py-1 border border-transparent transition-colors",
                                                                "bg-gray-100 hover:bg-black hover:text-white hover:border-black",
                                                                "dark:bg-zinc-800 dark:hover:bg-white dark:hover:text-black dark:hover:border-white"
                                                            )}
                                                        >
                                                            <GitBranch size={14} /> DIG_DEEPER
                                                        </button>
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </>
                                )}

                                {/* Input for column */}
                                {!col.isLoading && (
                                    <div className="mt-4 pt-4 border-t-2 border-inherit">
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
                                                placeholder="Append query..."
                                                className={cn(
                                                    "w-full border px-3 py-2 text-sm focus:outline-none transition-all font-mono",
                                                    "bg-gray-50 border-black focus:bg-white focus:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]",
                                                    "dark:bg-zinc-900 dark:border-white dark:focus:bg-black dark:focus:shadow-[2px_2px_0px_0px_rgba(255,255,255,1)]"
                                                )}
                                            />
                                        </form>
                                    </div>
                                )}
                            </MindMapCard>
                        </React.Fragment>
                    ))}

                    <div className="w-20 flex-shrink-0" />
                </div>
            </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}