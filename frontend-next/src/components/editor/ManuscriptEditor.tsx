'use client';

import { useEffect, useCallback, useRef } from 'react';
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
  type EditorState,
} from 'lexical';
import { $createHeadingNode } from '@lexical/rich-text';
import { useStore } from '@/store';
import { editorConfig } from '@/lib/editor/config';
import { EditorToolbar } from './EditorToolbar';
import { FigureRenderer } from './FigureRenderer';
import { TableRenderer } from './TableRenderer';
import { Skeleton } from '@/components/ui/skeleton';
import { FileText, Loader2 } from 'lucide-react';

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
          // Check if it's a subheading (starts with ## or ###)
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
            // Handle basic markdown formatting
            const cleanText = text
              .replace(/\*\*(.*?)\*\*/g, '$1') // Remove bold markers (we lose formatting, but it's readable)
              .replace(/\*(.*?)\*/g, '$1') // Remove italic markers
              .replace(/^[-*] /gm, '• ') // Convert list items
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
    <div className="flex flex-col items-center justify-center h-full text-center p-8">
      <FileText className="w-16 h-16 text-muted-foreground mb-4" />
      <h2 className="text-xl font-semibold mb-2">No Manuscript Yet</h2>
      <p className="text-muted-foreground max-w-md">
        Create a systematic review using the chat on the left. Once complete,
        your manuscript will appear here for editing and export.
      </p>
    </div>
  );
}

export function ManuscriptEditor() {
  const { editor: editorState, setEditorDirty, setActiveSection } = useStore();
  const { manuscript, isLoading } = editorState;
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleChange = useCallback(
    (editorState: EditorState) => {
      // Mark as dirty when content changes
      setEditorDirty(true);
    },
    [setEditorDirty]
  );

  const scrollToSection = useCallback((sectionId: string) => {
    setActiveSection(sectionId);
    // Scroll to section in editor
    // This would need DOM element references for each section
  }, [setActiveSection]);

  // Show loading state
  if (isLoading) {
    return (
      <div className="h-full flex flex-col">
        <div className="p-4 border-b flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm text-muted-foreground">Loading manuscript...</span>
        </div>
        <EditorSkeleton />
      </div>
    );
  }

  // Show empty state if no manuscript
  if (!manuscript) {
    return <EmptyState />;
  }

  return (
    <div className="h-full flex flex-col min-h-0">
      <LexicalComposer initialConfig={editorConfig}>
        <EditorToolbar />
        <div className="flex-1 min-h-0 overflow-y-auto" ref={scrollRef}>
          <div className="max-w-4xl lg:max-w-5xl xl:max-w-6xl 2xl:max-w-7xl mx-auto p-6 md:p-8 lg:p-10 xl:p-12">
            <RichTextPlugin
              contentEditable={
                <ContentEditable className="editor-content outline-none min-h-[500px]" />
              }
              placeholder={
                <div className="text-muted-foreground absolute top-0 left-0 pointer-events-none">
                  Start writing your manuscript...
                </div>
              }
              ErrorBoundary={LexicalErrorBoundary}
            />
            <ManuscriptLoaderPlugin />
            <HistoryPlugin />
            <ListPlugin />
            <OnChangePlugin onChange={handleChange} />

            {/* Figures */}
            {manuscript.figures.length > 0 && (
              <div className="mt-8 pt-8 border-t">
                <h2 className="text-xl font-serif font-semibold mb-4">Figures</h2>
                {manuscript.figures.map((figure) => (
                  <FigureRenderer key={figure.id} figure={figure} />
                ))}
              </div>
            )}

            {/* Tables */}
            {manuscript.tables.length > 0 && (
              <div className="mt-8 pt-8 border-t">
                <h2 className="text-xl font-serif font-semibold mb-4">Tables</h2>
                {manuscript.tables.map((table) => (
                  <TableRenderer key={table.id} table={table} />
                ))}
              </div>
            )}

            {/* References */}
            {manuscript.references.length > 0 && (
              <div className="mt-8 pt-8 border-t">
                <h2 className="text-xl font-serif font-semibold mb-4">References</h2>
                <ol className="list-decimal list-inside space-y-2 text-sm">
                  {manuscript.references.map((ref, index) => (
                    <li key={ref.id || index} className="text-muted-foreground">
                      {ref.citation}
                      {ref.doi && (
                        <a
                          href={`https://doi.org/${ref.doi}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="ml-2 text-primary hover:underline"
                        >
                          [{ref.doi}]
                        </a>
                      )}
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        </div>
      </LexicalComposer>
    </div>
  );
}
