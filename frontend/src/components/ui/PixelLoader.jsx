import React from 'react';

export const PixelLoader = () => (
  <div className="flex items-center gap-2 h-6">
    <div className="w-2 h-2 bg-black animate-[bounce_1s_infinite_0ms]"></div>
    <div className="w-2 h-2 bg-black animate-[bounce_1s_infinite_200ms]"></div>
    <div className="w-2 h-2 bg-black animate-[bounce_1s_infinite_400ms]"></div>
  </div>
);