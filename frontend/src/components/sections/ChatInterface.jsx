import React from 'react';
import { BookOpenCheck, Terminal, ArrowRight } from 'lucide-react';
import { cn } from '../lib/utils';
import { PixelLoader } from '../ui/PixelLoader';
import { BranchIndicator } from '../ui/BranchIndicator';
import ReactMarkdown from 'react-markdown';

export const ChatInterface = ({
  messages,
  isChatLoading,
  chatInput,
  setChatInput,
  sendChatMessage,
  onBranchClick
}) => {
  return (
    <div className="w-full max-w-4xl mx-auto flex flex-col p-6 lg:p-12">
        <div className="flex-1 overflow-y-auto space-y-8 pb-4 custom-scrollbar">
            {messages.length === 0 && (
                 <div className="h-full flex flex-col items-center justify-center opacity-40 text-center space-y-4">
                    <div className="relative">
                      <div className="absolute -inset-2 bg-blue-500 rounded-full blur-md opacity-25"></div>
                      <BookOpenCheck size={64} className="relative" />
                    </div>
                    <h2 className="text-2xl font-bold">KNOWLEDGE BASE IS READY</h2>
                    <p className="font-sans max-w-md opacity-70">Ask a question to search across all course materials. See what your classmates are asking.</p>
                </div>
            )}

            {messages.map((msg, i) => (
                <div key={msg.id || i} className={cn("flex gap-4", msg.role === 'user' ? "flex-row-reverse" : "")}>
                    <div className={cn(
                        "p-6 max-w-[80%] border-2 transition-all shadow-[4px_4px_0px_0px_currentColor]",
                        msg.role === 'user'
                            ? "bg-black text-white border-black"
                            : "bg-white text-black border-black"
                    )}>
                        {msg.role === 'assistant' && (
                            <div className="mb-2 text-xs font-bold uppercase tracking-wider opacity-50 flex items-center gap-2">
                                <Terminal size={12}/> RESPONSE
                            </div>
                        )}
                        <div className={cn("text-sm leading-relaxed font-sans prose max-w-none", msg.role === 'user' ? "prose-invert" : "")}>
                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>
                        {msg.source && (
                            <div className="mt-4 pt-4 border-t border-dashed border-gray-400">
                                <div className="text-xs font-mono opacity-60">SOURCE: {msg.source}</div>
                            </div>
                        )}
                        
                        {/* Branch Indicator - Show if message has forks */}
                        {msg.forks && msg.forks.length > 0 && (
                            <div className="mt-4 pt-4 border-t border-dashed border-gray-400">
                                <BranchIndicator 
                                    forks={msg.forks} 
                                    onBranchClick={onBranchClick}
                                />
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
                autoComplete="off"
                className="w-full border-2 px-10 py-5 text-sm focus:outline-none transition-all font-mono placeholder:opacity-40 bg-gray-50 border-black focus:bg-white focus:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]"
                placeholder="Ask Clark..."
            />
            <button type="submit" disabled={isChatLoading} className="absolute right-4 top-1/2 -translate-y-1/2 p-2 border border-transparent rounded-none transition-colors hover:bg-black hover:text-white hover:border-black">
                <ArrowRight size={20} />
            </button>
        </form>
    </div>
  );
};