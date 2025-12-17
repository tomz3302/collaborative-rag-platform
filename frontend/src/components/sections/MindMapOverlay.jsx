import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Minimize2, ArrowRight, Split } from 'lucide-react';
import { cn } from '../lib/utils';
import { MindMapCard } from '../ui/MindMapCard';
import { PixelLoader } from '../ui/PixelLoader';
import { BranchIndicator } from '../ui/BranchIndicator';
import ReactMarkdown from 'react-markdown';

export const MindMapOverlay = ({
  isOpen,
  setIsMapOpen,
  mapColumns,
  setMapColumns,
  handleDigDeeper,
  sendMessageInColumn,
  onBranchClick
}) => {
  return (
    <AnimatePresence>
        {isOpen && (
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
                            DETAILS
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
                                            <div className={cn("prose max-w-none", msg.role === 'user' ? "prose-invert" : "")}>
                                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                                            </div>
                                        </div>

                                        {/* DIG DEEPER ACTION */}
                                        {msg.role === 'assistant' && !col.isTempBranch && (
                                            <div className="flex justify-end items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                {/* Branch Indicator */}
                                                {msg.forks && msg.forks.length > 0 && (
                                                    <BranchIndicator 
                                                        forks={msg.forks} 
                                                        onBranchClick={onBranchClick}
                                                    />
                                                )}
                                                <button
                                                    onClick={() => handleDigDeeper(colIndex, msg.id, col.id)}
                                                    className="text-xs font-bold flex items-center gap-2 px-3 py-1 border border-transparent transition-colors bg-gray-100 hover:bg-black hover:text-white hover:border-black"
                                                >
                                                    <Split size={14} /> DIG_DEEPER
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
                                            placeholder={col.isTempBranch ? "Ask away!" : "ask daddy clark..."}
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
  );
};