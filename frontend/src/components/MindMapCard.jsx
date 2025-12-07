import React from 'react';
import { motion } from 'framer-motion';
import { Terminal, GitBranch, X } from 'lucide-react';
import { cn } from '../utils/utils';

const MindMapCard = ({ title, children, onClose, isRoot }) => (
  <motion.div
    initial={{ opacity: 0, x: 20, scale: 0.95 }}
    animate={{ opacity: 1, x: 0, scale: 1 }}
    exit={{ opacity: 0, scale: 0.9 }}
    className={cn(
      "flex-shrink-0 w-[400px] max-h-[80vh] flex flex-col overflow-hidden",
      // Neo-Brutalist Styling
      "bg-white text-black border-2 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]"
    )}
  >
    {/* Header */}
    <div className="h-14 flex items-center justify-between px-4 border-b-2 border-black bg-gray-50">
      <div className="flex items-center gap-2">
        {isRoot ? <Terminal size={18} className="text-black" /> : <GitBranch size={18} className="text-black" />}
        <span className="text-sm font-bold uppercase tracking-wider truncate max-w-[200px]">{title}</span>
      </div>
      {!isRoot && (
        <button onClick={onClose} className="hover:bg-black hover:text-white transition-colors p-1 border border-transparent hover:border-black">
          <X size={16} />
        </button>
      )}
    </div>

    {/* Content */}
    <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar bg-white">
      {children}
    </div>
  </motion.div>
);

export default MindMapCard;