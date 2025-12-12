import React from 'react';
import { motion } from 'framer-motion';
import { Terminal, GitBranch, X } from 'lucide-react';
import { cn } from '../lib/utils'; // Make sure this path is correct based on your folder structure

// NOTICE THE 'export const' HERE
export const MindMapCard = ({ title, children, onClose, isRoot, isTemp }) => (
  <motion.div
    initial={{ opacity: 0, x: 20, scale: 0.95 }}
    animate={{ opacity: 1, x: 0, scale: 1 }}
    exit={{ opacity: 0, scale: 0.9 }}
    className={cn(
      "flex-shrink-0 w-[600px] max-h-[90vh] flex flex-col overflow-hidden transition-colors duration-200",
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