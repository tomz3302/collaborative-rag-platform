import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { cn } from './lib/utils';
import { apiFetch } from '../utils/api';

// Component Imports
import { Sidebar } from './sections/Sidebar';
import { ChatInterface } from './sections/ChatInterface';
import { DocumentInterface } from './sections/DocumentInterface';
import { MindMapOverlay } from './sections/MindMapOverlay';
import { PixelLoader } from './ui/PixelLoader';

export default function ClarkRAG() {
  const { spaceId } = useParams();
  const navigate = useNavigate();

  // --- STATE ---
  const [view, setView] = useState('chat'); // 'chat' | 'document'
  const [documents, setDocuments] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);

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

  // --- API FETCHING ---
  useEffect(() => { 
      if (spaceId) fetchDocuments(); 
  }, [spaceId]);

  const handleExit = () => {
      localStorage.removeItem('activeSpaceId');
      navigate('/');
  };

  const fetchDocuments = async () => {
    setIsLoadingDocs(true);
    try {
      const res = await apiFetch(`/api/documents?space_id=${spaceId}`);
      const data = await res.json();
      setDocuments(data.documents || []);
    } catch (err) { console.error("API Error", err); }
    finally {
      setIsLoadingDocs(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
        await apiFetch(`/api/upload?space_id=${spaceId}`, { method: 'POST', body: formData });
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
        const res = await apiFetch(`/api/documents/${doc.id}/threads?space_id=${spaceId}`);
        const data = await res.json();
        setDocThreads(data.threads || []);
    } catch (err) { console.error(err); }
  };

  // --- GENERAL CHAT LOGIC ---
  const sendChatMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const text = chatInput;
    setChatInput('');

    // Optimistic UI
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setIsChatLoading(true);

    try {
        const res = await apiFetch(`/api/chat?space_id=${spaceId}`, {
            method: 'POST',
            body: JSON.stringify({
                text,
                thread_id: generalThreadId
            })
        });
        const data = await res.json();

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
        const res = await apiFetch(`/api/threads/${threadSummary.id}`);
        const data = await res.json();
        setMapColumns([data.thread]);
    } catch (err) { console.error(err); }
  };

  // Open a specific branch in the Mind Map (adds as new column to the right)
  const openBranchInMap = async (branchId) => {
    try {
        // Use the new endpoint that returns only branch messages
        const res = await apiFetch(`/api/branches/${branchId}/messages`);
        const data = await res.json();
        
        // Extract thread_id from the first message (all messages in a branch have same thread_id)
        const threadId = data.messages.length > 0 ? data.messages[0].thread_id : null;
        
        // Create a column for the branch view
        const branchColumn = {
            id: branchId,
            title: `Branch #${branchId}`,
            messages: data.messages || [],
            isTempBranch: false,
            isLoading: false,
            branchId: branchId, // Track for branch continuation
            threadId: threadId  // Track actual thread ID for branching from branches
        };
        
        // Add as a new column to the right instead of replacing all columns
        setMapColumns(prev => [...prev, branchColumn]);
    } catch (err) { 
        console.error("Error loading branch:", err); 
    }
  };

  const handleDigDeeper = (parentThreadIndex, messageId, threadId) => {
    const parentColumn = mapColumns[parentThreadIndex];
    
    // Use the actual thread_id from the column if it's a branch, otherwise use the passed threadId
    const actualThreadId = parentColumn.threadId || threadId;
    
    const tempBranchColumn = {
        id: `temp-${Date.now()}`,
        isTempBranch: true,
        sourceThreadId: actualThreadId,
        parentMessageId: messageId,
        messages: [],
        title: "New Branch",
        isLoading: false
    };

    const newColumns = mapColumns.slice(0, parentThreadIndex + 1);
    setMapColumns([...newColumns, tempBranchColumn]);
  };

  const sendMessageInColumn = async (columnIndex, text) => {
    if (!text.trim()) return;

    const currentColumn = mapColumns[columnIndex];

    // Add User Message Optimistically
    setMapColumns(prev => {
        const updated = [...prev];
        const col = { ...updated[columnIndex] };
        col.messages = [...(col.messages || []), { role: 'user', content: text, user: 'Me' }];
        col.isLoading = true;
        updated[columnIndex] = col;
        return updated;
    });

    try {
        let responseData = {};
        let newThreadId = currentColumn.id;

        if (currentColumn.isTempBranch) {
            // New Branch
            const res = await apiFetch(`/api/threads/${currentColumn.sourceThreadId}/branch?space_id=${spaceId}`, {
                method: 'POST',
                body: JSON.stringify({
                    content: text,
                    parent_message_id: currentColumn.parentMessageId
                })
            });
            responseData = await res.json();
            newThreadId = responseData.thread_id;
        } else {
            // Existing Thread or Branch Continuation
            const res = await apiFetch(`/api/chat?space_id=${spaceId}`, {
                 method: 'POST',
                 body: JSON.stringify({
                     text: text,
                     thread_id: currentColumn.id,
                     branch_id: currentColumn.branchId || null
                 })
            });
            responseData = await res.json();
            newThreadId = responseData.thread_id;
        }

        // Update State
        setMapColumns(prev => {
            const updated = [...prev];
            const col = { ...updated[columnIndex] };

            if (col.isTempBranch) {
                col.id = newThreadId;
                col.isTempBranch = false;
                col.isBranchColumn = true; // Mark as a branch column to keep input visible
                col.title = "Branched Thread";
                col.branchId = responseData.branch_id; // Store for branch continuation
            }

            col.isLoading = false;
            col.messages = [...col.messages, {
                role: 'assistant',
                content: responseData.response || "Message processed.",
                id: Date.now()
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

      {/* LOADING STATE */}
      {isLoadingDocs ? (
        <div className="w-full h-full flex flex-col items-center justify-center gap-4">
          <PixelLoader />
          <p className="text-sm text-gray-600">Loading space documents...</p>
        </div>
      ) : (
        <>
          {/* BACKGROUND & SIDEBAR */}
          <div className={cn(
              "flex h-full w-full transition-all duration-300",
              isMapOpen ? "opacity-20 pointer-events-none grayscale" : ""
            )}>

              {/* SIDEBAR MODULE */}
              <Sidebar
                view={view}
                setView={setView}
                documents={documents}
                currentDoc={currentDoc}
                openDocument={openDocument}
                isUploading={isUploading}
                handleFileUpload={handleFileUpload}
                onExit={handleExit}
              />

          {/* MAIN CONTENT AREA */}
          <main className="flex-1 flex relative bg-white">
            {view === 'chat' ? (
                // CHAT MODULE
                <ChatInterface
                    messages={messages}
                    isChatLoading={isChatLoading}
                    chatInput={chatInput}
                    setChatInput={setChatInput}
                    sendChatMessage={sendChatMessage}
                    onBranchClick={openBranchInMap}
                />
            ) : (
                // DOCUMENT MODULE
                <DocumentInterface
                    currentDoc={currentDoc}
                    docThreads={docThreads}
                    openThreadInMap={openThreadInMap}
                    spaceId={spaceId}
                />
            )}
          </main>
      </div>

          {/* MIND MAP OVERLAY MODULE */}
          <MindMapOverlay
            isOpen={isMapOpen}
            setIsMapOpen={setIsMapOpen}
            mapColumns={mapColumns}
            setMapColumns={setMapColumns}
            handleDigDeeper={handleDigDeeper}
            sendMessageInColumn={sendMessageInColumn}
            onBranchClick={openBranchInMap}
          />
        </>
      )}

    </div>
  );
}