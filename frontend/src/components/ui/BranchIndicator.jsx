import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare } from 'lucide-react';
import { cn } from '../lib/utils';

/**
 * BranchIndicator - Shows a count of conversation branches with hover tooltip
 * 
 * Props:
 * - forks: Array of { branch_id, preview, created_at }
 * - onBranchClick: (branch_id) => void - Called when user clicks a branch preview
 * - className: Additional CSS classes
 */
export const BranchIndicator = ({ forks = [], onBranchClick, className }) => {
  const [isHovered, setIsHovered] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 });
  const closeTimeoutRef = useRef(null);
  const buttonRef = useRef(null);

  if (!forks || forks.length === 0) return null;

  const handleMouseEnter = () => {
    // Clear any pending close timeout
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current);
      closeTimeoutRef.current = null;
    }
    
    // Calculate position based on button location
    if (buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setTooltipPosition({
        top: rect.bottom + 8, // 8px below the button
        left: Math.max(16, rect.left), // Ensure it doesn't go off-screen left
      });
    }
    
    setIsHovered(true);
  };

  const handleMouseLeave = () => {
    // Add a delay before closing to make it easier to navigate to the tooltip
    closeTimeoutRef.current = setTimeout(() => {
      setIsHovered(false);
    }, 300); // 300ms delay
  };

  return (
    <div 
      className={cn("relative inline-flex items-center", className)}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* Branch Count Badge */}
      <button
        ref={buttonRef}
        className={cn(
          "flex items-center gap-1 px-2 py-1 text-xs font-bold border-2 transition-all",
          "bg-gray-100 border-black hover:bg-black hover:text-white",
          "shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]",
          "hover:shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]",
          "active:shadow-none active:translate-x-[2px] active:translate-y-[2px]"
        )}
      >
        <MessageSquare size={12} />
        <span>{forks.length}</span>
      </button>

      {/* Tooltip on Hover - Fixed position to avoid clipping */}
      {isHovered && (
        <div 
          className={cn(
            "fixed z-[9999] w-[400px]",
            "bg-white border-2 border-black shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]"
          )}
          style={{
            top: tooltipPosition.top,
            left: tooltipPosition.left,
          }}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          {/* Tooltip Header */}
          <div className="px-4 py-3 border-b-2 border-black bg-black text-white">
            <div className="text-xs font-bold uppercase tracking-wider flex items-center gap-2">
              <MessageSquare size={14} />
              ALTERNATIVE_PATHS [{forks.length}]
            </div>
          </div>

          {/* Fork Previews */}
          <div className="max-h-[300px] overflow-y-auto custom-scrollbar">
            {forks.map((fork, idx) => (
              <button
                key={fork.branch_id}
                onClick={() => onBranchClick?.(fork.branch_id)}
                className={cn(
                  "w-full text-left px-4 py-4 transition-colors",
                  "hover:bg-gray-100 border-b border-dashed border-gray-300 last:border-b-0",
                  "group"
                )}
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-black text-white text-xs font-bold">
                    {idx + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-sans leading-relaxed group-hover:text-black">
                      "{fork.preview}"
                    </p>
                    {fork.created_at && (
                      <p className="text-[10px] font-mono opacity-50 mt-2">
                        {new Date(fork.created_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>

          {/* Tooltip Footer */}
          <div className="px-4 py-3 border-t-2 border-black bg-gray-50">
            <p className="text-xs font-mono opacity-60">
              // Click to explore branch
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
