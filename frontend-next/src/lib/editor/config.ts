// Lexical editor configuration

import type { InitialConfigType } from '@lexical/react/LexicalComposer';
import { HeadingNode, QuoteNode } from '@lexical/rich-text';
import { ListNode, ListItemNode } from '@lexical/list';
import { TableNode, TableRowNode, TableCellNode } from '@lexical/table';
import { CodeNode } from '@lexical/code';
import { LinkNode } from '@lexical/link';

// Modern theme for systematic review manuscripts (using Inter font)
export const academicTheme = {
  // Root container
  root: 'editor-root prose prose-slate max-w-none focus:outline-none font-sans',

  // Headings with modern styling
  heading: {
    h1: 'text-3xl font-sans font-bold mb-6 mt-8 text-foreground tracking-tight',
    h2: 'text-2xl font-sans font-semibold mb-4 mt-6 text-foreground border-b pb-2',
    h3: 'text-xl font-sans font-semibold mb-3 mt-5 text-foreground',
    h4: 'text-lg font-sans font-medium mb-2 mt-4 text-foreground',
    h5: 'text-base font-sans font-medium mb-2 mt-3 text-foreground',
  },

  // Paragraphs - clean modern style
  paragraph: 'font-sans text-base leading-7 mb-4 text-foreground',

  // Lists
  list: {
    ul: 'list-disc ml-6 mb-4 space-y-1',
    ol: 'list-decimal ml-6 mb-4 space-y-1',
    nested: {
      listitem: 'list-none ml-6',
    },
    listitem: 'mb-1',
  },

  // Text formatting
  text: {
    bold: 'font-bold',
    italic: 'italic',
    underline: 'underline',
    strikethrough: 'line-through',
    code: 'bg-muted px-1.5 py-0.5 rounded text-sm font-mono',
  },

  // Links
  link: 'text-primary underline hover:text-primary/80',

  // Quotes
  quote: 'border-l-4 border-primary/30 pl-4 my-4 italic text-muted-foreground',

  // Tables
  table: 'border-collapse w-full my-6',
  tableCell: 'border border-border px-3 py-2 text-sm',
  tableCellHeader: 'border border-border px-3 py-2 text-sm font-semibold bg-muted',
  tableRow: '',

  // Code blocks
  code: 'bg-muted p-4 rounded-lg my-4 overflow-x-auto font-mono text-sm',
};

// Editor configuration
export const editorConfig: InitialConfigType = {
  namespace: 'ArakisManuscriptEditor',
  theme: academicTheme,
  nodes: [
    HeadingNode,
    QuoteNode,
    ListNode,
    ListItemNode,
    TableNode,
    TableRowNode,
    TableCellNode,
    CodeNode,
    LinkNode,
  ],
  onError: (error: Error) => {
    console.error('Lexical Editor Error:', error);
  },
  editable: true,
};

// Read-only configuration
export const readOnlyConfig: InitialConfigType = {
  ...editorConfig,
  editable: false,
};
