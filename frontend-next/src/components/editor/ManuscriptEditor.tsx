'use client';

import { useEffect, useCallback, useRef, useState } from 'react';
import { LexicalComposer } from '@lexical/react/LexicalComposer';
import { RichTextPlugin } from '@lexical/react/LexicalRichTextPlugin';
import { ContentEditable } from '@lexical/react/LexicalContentEditable';
import { HistoryPlugin } from '@lexical/react/LexicalHistoryPlugin';
import { ListPlugin } from '@lexical/react/LexicalListPlugin';
import { LexicalErrorBoundary } from '@lexical/react/LexicalErrorBoundary';
import { OnChangePlugin } from '@lexical/react/LexicalOnChangePlugin';
import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import {
  $getRoot,
  $createParagraphNode,
  $createTextNode,
} from 'lexical';
import { $createHeadingNode } from '@lexical/rich-text';
import { useStore } from '@/store';
import { editorConfig } from '@/lib/editor/config';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  ArrowLeft,
  Check,
  Sparkles,
  Share2,
  Bold,
  Italic,
  Underline,
  Link2,
  Image,
  Table,
  ChevronDown,
  Copy,
  Download,
  MessageSquare,
  BarChart3,
  BookOpen,
  FileText,
  Loader2,
  Send,
} from 'lucide-react';

// Plugin to load manuscript content
function ManuscriptLoaderPlugin() {
  const [editor] = useLexicalComposerContext();
  const { editor: editorState } = useStore();
  const { manuscript } = editorState;

  useEffect(() => {
    if (!manuscript) return;

    editor.update(() => {
      const root = $getRoot();
      root.clear();

      // Add title
      const titleNode = $createHeadingNode('h1');
      titleNode.append($createTextNode(manuscript.manuscript.title || 'Untitled'));
      root.append(titleNode);

      // Helper to add section
      const addSection = (title: string, content: string, headingLevel: 'h2' = 'h2') => {
        if (!content) return;

        // Add heading
        const heading = $createHeadingNode(headingLevel);
        heading.append($createTextNode(title));
        root.append(heading);

        // Parse content and add paragraphs
        const paragraphs = content.split('\n\n').filter(Boolean);
        paragraphs.forEach((text) => {
          if (text.startsWith('### ')) {
            const subheading = $createHeadingNode('h4');
            subheading.append($createTextNode(text.replace('### ', '')));
            root.append(subheading);
          } else if (text.startsWith('## ')) {
            const subheading = $createHeadingNode('h3');
            subheading.append($createTextNode(text.replace('## ', '')));
            root.append(subheading);
          } else {
            const para = $createParagraphNode();
            const cleanText = text
              .replace(/\*\*(.*?)\*\*/g, '$1')
              .replace(/\*(.*?)\*/g, '$1')
              .replace(/^[-*] /gm, '• ')
              .trim();
            para.append($createTextNode(cleanText));
            root.append(para);
          }
        });
      };

      // Add all sections
      addSection('Abstract', manuscript.manuscript.abstract);
      addSection('Introduction', manuscript.manuscript.introduction);
      addSection('Methods', manuscript.manuscript.methods);
      addSection('Results', manuscript.manuscript.results);
      addSection('Discussion', manuscript.manuscript.discussion);
      addSection('Conclusions', manuscript.manuscript.conclusions);
    });
  }, [editor, manuscript]);

  return null;
}

// Editor loading skeleton
function EditorSkeleton() {
  return (
    <div className="p-8 space-y-6">
      <Skeleton className="h-10 w-3/4" />
      <Skeleton className="h-6 w-24" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-2/3" />
      <Skeleton className="h-6 w-32 mt-8" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}

// Empty state
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center p-8 bg-gray-50">
      <FileText className="w-16 h-16 text-gray-300 mb-4" />
      <h2 className="text-xl font-semibold text-gray-900 mb-2">No Manuscript Yet</h2>
      <p className="text-gray-500 max-w-md">
        Create a systematic review using the chat on the left. Once complete,
        your manuscript will appear here for editing and export.
      </p>
    </div>
  );
}

// Toolbar component
function EditorToolbarNew() {
  const [activeTab, setActiveTab] = useState('chat');

  const formatButtons = [
    { icon: Bold, label: 'Bold' },
    { icon: Italic, label: 'Italic' },
    { icon: Underline, label: 'Underline' },
    { icon: Link2, label: 'Link' },
    { icon: Image, label: 'Image' },
    { icon: Table, label: 'Table' },
  ];

  const actionTabs = [
    { id: 'copy', label: 'Copy', icon: Copy },
    { id: 'export', label: 'Export', icon: Download },
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'analysis', label: 'Analysis', icon: BarChart3 },
    { id: 'library', label: 'Library', icon: BookOpen },
  ];

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-gray-200">
      {/* Format Toolbar */}
      <div className="flex items-center gap-1">
        {/* Heading Dropdown */}
        <button className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded">
          H1
          <ChevronDown className="w-3 h-3" />
        </button>

        <div className="w-px h-6 bg-gray-200 mx-2" />

        {formatButtons.map((btn) => (
          <button
            key={btn.label}
            className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
            title={btn.label}
          >
            <btn.icon className="w-4 h-4" />
          </button>
        ))}

        <div className="w-px h-6 bg-gray-200 mx-2" />

        {/* ADA Dropdown */}
        <button className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded">
          ADA
          <ChevronDown className="w-3 h-3" />
        </button>
      </div>

      {/* Action Tabs */}
      <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
        {actionTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`
              flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors
              ${activeTab === tab.id
                ? 'bg-purple-600 text-white'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-200'
              }
            `}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function ManuscriptEditor() {
  const { editor: editorStore, setEditorDirty, setLayoutMode, setViewMode } = useStore();
  const { manuscript, isLoading } = editorStore;
  const scrollRef = useRef<HTMLDivElement>(null);
  const [wordCount] = useState(340);
  const [aiPrompt, setAiPrompt] = useState('');

  const handleChange = useCallback(
    () => {
      setEditorDirty(true);
    },
    [setEditorDirty]
  );

  const handleBack = () => {
    setLayoutMode('chat-fullscreen');
    setViewMode('viewing-workflow');
  };

  // Show loading state
  if (isLoading) {
    return (
      <div className="h-full flex flex-col bg-white">
        <div className="p-4 border-b flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm text-gray-500">Loading manuscript...</span>
        </div>
        <EditorSkeleton />
      </div>
    );
  }

  // Show empty state if no manuscript
  if (!manuscript) {
    return <EmptyState />;
  }

  const documentTitle = manuscript.manuscript.title || 'New Document';

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <div className="flex items-center gap-4">
          <button
            onClick={handleBack}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>

          <div>
            <h1 className="text-sm font-medium text-gray-900">{documentTitle}</h1>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>{wordCount} words</span>
              <span className="flex items-center gap-1 text-green-600">
                <Check className="w-3 h-3" />
                Saved
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-2">
            <Sparkles className="w-4 h-4 text-purple-600" />
            AI Generate
          </Button>
          <Button variant="outline" size="sm" className="gap-2">
            <Share2 className="w-4 h-4" />
            Share
          </Button>
        </div>
      </header>

      {/* Toolbar */}
      <EditorToolbarNew />

      {/* Editor Content */}
      <div className="flex-1 min-h-0 overflow-hidden flex">
        <div className="flex-1 overflow-y-auto" ref={scrollRef}>
          <LexicalComposer initialConfig={editorConfig}>
            <div className="max-w-3xl mx-auto p-8">
              {/* Section Headers */}
              <div className="space-y-8">
                <div>
                  <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
                    Title and Abstract
                  </h2>
                  <div className="bg-gray-50 rounded-lg p-4 min-h-[100px]">
                    <RichTextPlugin
                      contentEditable={
                        <ContentEditable className="editor-content outline-none min-h-[80px] text-gray-700" />
                      }
                      placeholder={
                        <div className="text-gray-400 absolute top-0 left-0 pointer-events-none">
                          Enter your title and abstract...
                        </div>
                      }
                      ErrorBoundary={LexicalErrorBoundary}
                    />
                  </div>
                </div>

                <div>
                  <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
                    Introduction
                  </h2>
                  <div className="bg-gray-50 rounded-lg p-4 min-h-[100px]">
                    <div className="text-gray-400 text-sm">
                      Click to add introduction content...
                    </div>
                  </div>
                </div>

                <div>
                  <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
                    Methods
                  </h2>
                  <div className="bg-gray-50 rounded-lg p-4 min-h-[100px]">
                    <div className="text-gray-400 text-sm">
                      Click to add methods content...
                    </div>
                  </div>
                </div>
              </div>

              <ManuscriptLoaderPlugin />
              <HistoryPlugin />
              <ListPlugin />
              <OnChangePlugin onChange={handleChange} />
            </div>
          </LexicalComposer>
        </div>
      </div>

      {/* AI Chat Input */}
      <div className="border-t border-gray-200 p-4 bg-white">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center gap-2 bg-gray-50 rounded-lg border border-gray-200 px-4 py-2">
            <Input
              type="text"
              placeholder="Ask AI for Help"
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              className="flex-1 border-none bg-transparent shadow-none focus-visible:ring-0"
            />
            <button
              className="p-2 text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
              disabled={!aiPrompt.trim()}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
