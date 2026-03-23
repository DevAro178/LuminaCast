import React, { useState } from 'react';
import useStore from '../../store/useStore';
import Button from '../ui/Button';

export default function OutlineReview() {
  const outlineData = useStore(state => state.outlineData);
  const approveOutline = useStore(state => state.approveOutline);
  const isGenerating = useStore(state => state.isGenerating);
  
  // Local state for edits before approval
  const [editedItems, setEditedItems] = useState([...outlineData]);

  const handleTitleChange = (id, newTitle) => {
    setEditedItems(prev => prev.map(item => 
      item.id === id ? { ...item, title: newTitle } : item
    ));
  };

  const handleDescChange = (id, newDesc) => {
    setEditedItems(prev => prev.map(item => 
      item.id === id ? { ...item, description: newDesc } : item
    ));
  };

  const handleApprove = () => {
    approveOutline(editedItems);
  };

  // Group by chapter
  const chapters = editedItems.filter(i => i.type === 'chapter').sort((a,b) => a.chapter_index - b.chapter_index);

  return (
    <div className="col-span-3 flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex justify-between items-end mb-6">
        <div>
          <h2 className="text-3xl font-black tracking-tight mb-2">Review Script Outline</h2>
          <p className="text-textSecondary">
            Review the chapters and sections before AI expands them into full scenes. Edit titles or descriptions to guide the expansion.
          </p>
        </div>
        <div className="flex gap-4">
          <Button 
            variant="primary" 
            onClick={handleApprove}
            disabled={isGenerating}
            className="shadow-[0_0_20px_rgba(var(--accent-rgb),0.3)]"
          >
            {isGenerating ? "EXPANDING..." : "APPROVE & EXPAND SCRIPT"}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto pr-4 space-y-6 custom-scrollbar">
        {chapters.map((chapter) => (
          <div key={chapter.id} className="bento-card bg-surface/40 border border-white/5 space-y-4">
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-3">
                <span className="text-xs font-black text-accent bg-accent/10 px-2 py-1 rounded">
                  CH {chapter.chapter_index + 1}
                </span>
                <input 
                  type="text"
                  value={chapter.title}
                  onChange={(e) => handleTitleChange(chapter.id, e.target.value)}
                  className="bg-transparent text-xl font-bold outline-none flex-1 border-b border-white/0 focus:border-white/20 transition-all font-sans"
                  placeholder="Chapter Title"
                />
              </div>
              <textarea 
                value={chapter.description || ''}
                onChange={(e) => handleDescChange(chapter.id, e.target.value)}
                className="bg-white/5 text-sm text-textSecondary outline-none w-full resize-none p-3 rounded-lg border border-transparent focus:border-white/10 transition-all font-sans"
                rows={2}
                placeholder="Chapter Summary (optional)"
              />
            </div>

            <div className="pl-8 border-l-2 border-white/5 space-y-3">
              {editedItems
                .filter(i => i.type === 'section' && i.chapter_index === chapter.chapter_index)
                .sort((a,b) => a.section_index - b.section_index)
                .map(section => (
                  <div key={section.id} className="bg-surface/30 p-3 rounded-xl border border-white/5">
                    <input 
                      type="text"
                      value={section.title}
                      onChange={(e) => handleTitleChange(section.id, e.target.value)}
                      className="bg-transparent text-sm font-bold w-full outline-none mb-1 text-white"
                      placeholder="Section Title"
                    />
                    <textarea 
                      value={section.description || ''}
                      onChange={(e) => handleDescChange(section.id, e.target.value)}
                      className="bg-transparent text-xs text-textSecondary w-full outline-none resize-none"
                      rows={2}
                      placeholder="Section exact talking point"
                    />
                  </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
