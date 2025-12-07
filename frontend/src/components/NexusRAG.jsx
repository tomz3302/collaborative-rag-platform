import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquare, FileText, X, GitBranch, ArrowRight,
  Upload, Terminal, Box, Minimize2, Loader2
} from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

// --- UTILS ---
function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// --- COMPONENTS ---

const PixelLoader = () => (
  <div className="flex items-center gap-2 h-6">
    <div className="w-2 h-2 bg-black animate-[bounce_1s_infinite_0ms]"></div>
    <div className="w-2 h-2 bg-black animate-[bounce_1s_infinite_200ms]"></div>
    <div className="w-2 h-2 bg-black animate-[bounce_1s_infinite_400ms]"></div>
  </div>
);

// Mind Map Card (Light Mode Only)
const MindMapCard = ({ title, children, onClose, isRoot, isTemp }) => (
  <motion.div
    initial={{ opacity: 0, x: 20, scale: 0.95 }}
    animate={{ opacity: 1, x: 0, scale: 1 }}
    exit={{ opacity: 0, scale: 0.9 }}
    className={cn(
      "flex-shrink-0 w-[400px] max-h-[80vh] flex flex-col overflow-hidden transition-colors duration-200",
      "border-2 bg-white text-black border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]"
    )}
  >
    {/* Header */}
    <div className="h-14 flex items-center justify-between px-4 border-b-2 border-inherit bg-gray-50">
      <div className="flex items-center gap-2">
        {isRoot ? <Terminal size={18} /> : <GitBranch size={18} />}
        <span className="text-sm font-bold uppercase tracking-wider truncate max-w-[200px]">
          {isTemp ? "New Branch..." : title}
        </span>
      </div>
      {!isRoot && (
        <button onClick={onClose} className="hover:bg-black hover:text-white transition-colors p-1 border border-transparent hover:border-inherit">
          <X size={16} />
        </button>
      )}
    </div>

    {/* Content */}
    <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar bg-white relative">
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
  const [generalThreadId, setGeneralThreadId] = useState(null); // Stores ID after first message
  const [isChatLoading, setIsChatLoading] = useState(false);

  // Document & Threads
  const [currentDoc, setCurrentDoc] = useState(null);
  const [docThreads, setDocThreads] = useState([]);

  // --- MIND MAP STATE ---
  const [isMapOpen, setIsMapOpen] = useState(false);
  const [mapColumns, setMapColumns] = useState([]);

  // --- API FETCHING ---
  useEffect(() => { fetchDocuments(); }, []);

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

  // --- 1) GENERAL CHAT LOGIC ---
  const sendChatMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const text = chatInput;
    setChatInput('');

    // Optimistic UI
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setIsChatLoading(true);

    try {
        // Send request. If generalThreadId is null, API creates new thread.
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text,
                thread_id: generalThreadId,
                user_id: 1 // Default as per doc
            })
        });
        const data = await res.json();

        // SAVE THE THREAD ID FOR NEXT TIME
        if (data.thread_id) {
            setGeneralThreadId(data.thread_id);
        }

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
        const res = await fetch(`/api/threads/${threadSummary.id}`);
        const data = await res.json();
        setMapColumns([data.thread]);
    } catch (err) { console.error(err); }
  };

  // --- 2) BRANCHING PREPARATION ---
  const handleDigDeeper = (parentThreadIndex, messageId, threadId) => {
    // We do NOT call API yet. We create a "Pending" column.

    const tempBranchColumn = {
        id: `temp-${Date.now()}`, // Temporary ID
        isTempBranch: true,       // Flag to identify logic
        sourceThreadId: threadId, // The thread we are branching FROM
        parentMessageId: messageId, // The message we are branching FROM
        messages: [],             // Empty initially
        title: "New Branch",
        isLoading: false
    };

    // Remove any existing columns to the right of this one, add temp column
    const newColumns = mapColumns.slice(0, parentThreadIndex + 1);
    setMapColumns([...newColumns, tempBranchColumn]);
  };

  // --- 3) SENDING IN MIND MAP (HANDLES BRANCHING) ---
  const sendMessageInColumn = async (columnIndex, text) => {
    if (!text.trim()) return;

    const currentColumn = mapColumns[columnIndex];

    // Add User Message Optimistically
    setMapColumns(prev => {
        const updated = [...prev];
        const col = { ...updated[columnIndex] };
        col.messages = [...(col.messages || []), { role: 'user', content: text, user: 'Me' }];
        col.isLoading = true; // Show loader
        updated[columnIndex] = col;
        return updated;
    });

    try {
        let responseData = {};
        let newThreadId = currentColumn.id;

        if (currentColumn.isTempBranch) {
            // === SCENARIO: CREATING NEW BRANCH ===
            // Call the /branch endpoint
            const res = await fetch(`/api/threads/${currentColumn.sourceThreadId}/branch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: text,
                    parent_message_id: currentColumn.parentMessageId,
                    user_id: 1
                })
            });
            responseData = await res.json();

            // The API response should contain the NEW thread ID and the response
            newThreadId = responseData.thread_id;
        } else {
            // === SCENARIO: CONTINUING EXISTING THREAD ===
            // Call the /messages endpoint (Backend doesn't return response text usually for POST message,
            // but for RAG it might. Assuming standard chat behavior or reusing chat endpoint if architecture allows.
            // Based on API doc provided: POST /messages returns status.
            // *Correction*: The API doc for POST /messages just returns success.
            // However, typically in RAG chat UIs, we expect a response.
            // If the POST /messages doesn't trigger AI, we might need to hit /chat with thread_id.
            // Assuming for this RAG, POST /chat with thread_id is the way to continue conversation with AI response.

            const res = await fetch('/api/chat', {
                 method: 'POST',
                 headers: { 'Content-Type': 'application/json' },
                 body: JSON.stringify({
                     text: text,
                     thread_id: currentColumn.id,
                     user_id: 1
                 })
            });
            responseData = await res.json();
            newThreadId = responseData.thread_id;
        }

        // Update State with AI Response and correct Thread ID
        setMapColumns(prev => {
            const updated = [...prev];
            const col = { ...updated[columnIndex] };

            // If it was temp, it's now a real thread. Save the ID.
            if (col.isTempBranch) {
                col.id = newThreadId;
                col.isTempBranch = false;
                col.title = "Branched Thread"; // Or generic title
            }

            col.isLoading = false;
            col.messages = [...col.messages, {
                role: 'assistant',
                content: responseData.response || "Message processed.", // Handle API response
                id: Date.now() // specific ID for key
            }];

            updated[columnIndex] = col;
            return updated;
        });

    } catch (err) {
        console.error("Error sending message:", err);
        setMapColumns(prev => {
            const updated = [...prev];
            updated[columnIndex].isLoading = false;
            return updated;
        });
    }
  };

  return (
    // Light Mode Wrapper
    <div className="w-full h-screen bg-white transition-colors duration-200 overflow-hidden font-mono text-black">

      {/* BACKGROUND & SIDEBAR */}
      <div className={cn(
          "flex h-full w-full transition-all duration-300",
          isMapOpen ? "opacity-20 pointer-events-none grayscale" : ""
        )}>

          {/* SIDEBAR */}
          <nav className="w-20 lg:w-64 border-r-2 flex flex-col border-black bg-gray-50">
            <div className="h-16 flex items-center gap-3 px-6 border-b-2 border-black bg-white">
              <div className="w-8 h-8 flex items-center justify-center border shadow-[2px_2px_0px_0px_rgba(0,0,0,0.5)] bg-black text-white border-black">
                <Box size={18} />
              </div>
              <span className="font-bold text-lg hidden lg:block tracking-tight">NEXUS_API</span>
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

                {/* Upload Button - Pinned to Bottom */}
                <label className="mt-auto flex items-center justify-center gap-2 w-full py-3 border-2 border-dashed cursor-pointer transition-colors border-gray-400 text-gray-500 hover:border-black hover:text-black hover:bg-white">
                    {isUploading ? <Loader2 className="animate-spin" size={16}/> : <Upload size={16} />}
                    <span className="text-sm font-bold">UPLOAD_PDF</span>
                    <input type="file" className="hidden" accept="application/pdf" onChange={handleFileUpload} />
                </label>
            </div>
          </nav>

          {/* MAIN CONTENT */}
          <main className="flex-1 flex relative bg-white">
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
                                        ? "bg-black text-white border-black"
                                        : "bg-white text-black border-black"
                                )}>
                                    {msg.role === 'assistant' && (
                                        <div className="mb-2 text-xs font-bold uppercase tracking-wider opacity-50 flex items-center gap-2">
                                            <Terminal size={12}/> API_RESPONSE
                                        </div>
                                    )}
                                    <p className="text-sm leading-relaxed whitespace-pre-wrap font-sans">{msg.content}</p>
                                    {msg.source && (
                                        <div className="mt-4 pt-4 border-t border-dashed border-gray-400">
                                            <div className="text-xs font-mono opacity-60">SOURCE: {msg.source}</div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}

                        {isChatLoading && (
                           <div className="flex gap-4">
                               <div className="p-6 border-2 shadow-[4px_4px_0px_0px_currentColor] bg-white text-black border-black">
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
                            className="w-full border-2 px-10 py-5 text-sm focus:outline-none transition-all font-mono placeholder:opacity-40 bg-gray-50 border-black focus:bg-white focus:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]"
                            placeholder="Enter command or query..."
                        />
                        <button type="submit" disabled={isChatLoading} className="absolute right-4 top-1/2 -translate-y-1/2 p-2 border border-transparent rounded-none transition-colors hover:bg-black hover:text-white hover:border-black">
                            <ArrowRight size={20} />
                        </button>
                    </form>
                </div>
            ) : (
                // DOCUMENT VIEW
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
                            <h3 className="text-sm font-bold uppercase tracking-wider">Active Threads</h3>
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
                className="fixed inset-0 z-50 flex flex-col backdrop-blur-sm bg-white/90"
            >
                {/* Overlay Header */}
                <div className="h-20 flex items-center justify-between px-8 border-b-2 bg-white border-black">
                    <div className="flex items-center gap-4">
                        <div className="px-3 py-1 text-sm font-bold uppercase tracking-wider shadow-[2px_2px_0px_0px_rgba(0,0,0,0.2)] bg-black text-white">
                            Mind_Map_View
                        </div>
                        <div className="h-px w-12 bg-black"></div>
                        <span className="font-mono text-sm opacity-60">Exploring Logic Branch</span>
                    </div>
                    <button onClick={() => setIsMapOpen(false)} className="w-10 h-10 flex items-center justify-center border-2 transition-all active:translate-x-[2px] active:translate-y-[2px] active:shadow-none border-black hover:bg-black hover:text-white shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                        <Minimize2 size={20} />
                    </button>
                </div>

                {/* Canvas */}
                <div className="flex-1 overflow-x-auto overflow-y-hidden p-8 flex items-start gap-12 custom-scrollbar bg-gray-50">

                    {mapColumns.map((col, colIndex) => (
                        <React.Fragment key={col.id || colIndex}>

                            {/* Connector Arrow */}
                            {colIndex > 0 && (
                                <motion.div
                                    initial={{ width: 0, opacity: 0 }}
                                    animate={{ width: 'auto', opacity: 1 }}
                                    className="pt-32"
                                >
                                    <ArrowRight size={32} className="text-black" />
                                </motion.div>
                            )}

                            {/* Column Card */}
                            <MindMapCard
                                title={col.title}
                                isRoot={colIndex === 0}
                                isTemp={col.isTempBranch}
                                onClose={() => setMapColumns(prev => prev.slice(0, colIndex))}
                            >
                                {col.isTempBranch && !col.messages?.length && (
                                    <div className="h-full flex flex-col justify-end pb-4">
                                        <div className="text-sm opacity-60 font-mono mb-2">
                                            // Start a new branch from context...
                                        </div>
                                    </div>
                                )}

                                {col.messages?.map((msg, idx) => (
                                    <div key={idx} className="group flex flex-col gap-2">
                                        <div className={cn(
                                            "p-4 border-2 text-sm font-sans shadow-[3px_3px_0px_0px_currentColor]",
                                            msg.role === 'assistant'
                                                ? "bg-white text-black border-black"
                                                : "bg-black text-white border-black"
                                        )}>
                                            <div className="text-[10px] font-bold uppercase mb-2 opacity-50">
                                                {msg.role === 'assistant' ? "System_Output" : "User_Input"}
                                            </div>
                                            {msg.content}
                                        </div>

                                        {/* DIG DEEPER ACTION */}
                                        {msg.role === 'assistant' && !col.isTempBranch && (
                                            <div className="flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                                                <button
                                                    // Pass index, message ID, and Thread ID
                                                    onClick={() => handleDigDeeper(colIndex, msg.id, col.id)}
                                                    className="text-xs font-bold flex items-center gap-2 px-3 py-1 border border-transparent transition-colors bg-gray-100 hover:bg-black hover:text-white hover:border-black"
                                                >
                                                    <GitBranch size={14} /> DIG_DEEPER
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                ))}

                                {col.isLoading && (
                                    <div className="flex justify-center p-4">
                                        <PixelLoader />
                                    </div>
                                )}

                                {/* Input for column */}
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
                                            placeholder={col.isTempBranch ? "Enter new branch query..." : "Append query..."}
                                            autoFocus={col.isTempBranch}
                                            className="w-full border px-3 py-2 text-sm focus:outline-none transition-all font-mono bg-gray-50 border-black focus:bg-white focus:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
                                        />
                                    </form>
                                </div>
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