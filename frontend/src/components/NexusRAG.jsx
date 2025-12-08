import React, { useState, useEffect } from 'react';
import { cn } from './lib/utils';

// Component Imports
import { Sidebar } from './sections/Sidebar';
import { ChatInterface } from './sections/ChatInterface';
import { DocumentInterface } from './sections/DocumentInterface';
import { MindMapOverlay } from './sections/MindMapOverlay';

export default function NexusRAG({ spaceId, onExit }) {
  // --- STATE ---
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

  // --- API FETCHING ---
  useEffect(() => { fetchDocuments(); }, []);

  const fetchDocuments = async () => {
    try {
      const res = await fetch(`/api/documents?space_id=${spaceId}`);
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
        const res = await fetch(`/api/documents/${doc.id}/threads?space_id=${spaceId}`);
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
        const res = await fetch(`/api/chat?space_id=${spaceId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text,
                thread_id: generalThreadId,
                user_id: 1
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
        const res = await fetch(`/api/threads/${threadSummary.id}`);
        const data = await res.json();
        setMapColumns([data.thread]);
    } catch (err) { console.error(err); }
  };

  const handleDigDeeper = (parentThreadIndex, messageId, threadId) => {
    const tempBranchColumn = {
        id: `temp-${Date.now()}`,
        isTempBranch: true,
        sourceThreadId: threadId,
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
            const res = await fetch(`/api/threads/${currentColumn.sourceThreadId}/branch?space_id=${spaceId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: text,
                    parent_message_id: currentColumn.parentMessageId,
                    user_id: 1
                })
            });
            responseData = await res.json();
            newThreadId = responseData.thread_id;
        } else {
            // Existing Thread
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

        // Update State
        setMapColumns(prev => {
            const updated = [...prev];
            const col = { ...updated[columnIndex] };

            if (col.isTempBranch) {
                col.id = newThreadId;
                col.isTempBranch = false;
                col.title = "Branched Thread";
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
                />
            ) : (
                // DOCUMENT MODULE
                <DocumentInterface
                    currentDoc={currentDoc}
                    docThreads={docThreads}
                    openThreadInMap={openThreadInMap}
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
      />

    </div>
  );
}