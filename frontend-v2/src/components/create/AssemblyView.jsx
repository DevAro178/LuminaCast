import React from 'react';
import Loader from '../ui/Loader';

export default function AssemblyView() {
  return (
    <div className="col-span-3 bento-card relative h-[400px]">
      <Loader 
        title="ASSEMBLING VIDEO..."
        message="Generating Audio & Captions, stitching final MP4."
      />
    </div>
  );
}
