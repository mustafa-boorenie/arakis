'use client';

import { useState, useEffect } from 'react';
import { useStore } from '@/store';
import { api } from '@/lib/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Search,
  Plus,
  Bell,
  HelpCircle,
  FileText,
  MoreVertical,
} from 'lucide-react';
import type { WorkflowResponse } from '@/types';

interface DocumentCardProps {
  workflow: WorkflowResponse;
  isSelected: boolean;
  onSelect: (id: string) => void;
  onClick: () => void;
}

function DocumentCard({ workflow, isSelected, onSelect, onClick }: DocumentCardProps) {
  const truncate = (text: string, length: number) => {
    if (text.length <= length) return text;
    return text.slice(0, length) + '...';
  };

  return (
    <div
      className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer group"
      onClick={onClick}
    >
      {/* Header with checkbox and menu */}
      <div className="flex items-start justify-between mb-3">
        <div
          onClick={(e) => {
            e.stopPropagation();
            onSelect(workflow.id);
          }}
          className={`
            w-5 h-5 rounded border-2 flex items-center justify-center cursor-pointer
            transition-colors
            ${isSelected
              ? 'bg-purple-600 border-purple-600'
              : 'border-gray-300 hover:border-purple-400'
            }
          `}
        >
          {isSelected && (
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          )}
        </div>
        <button
          onClick={(e) => e.stopPropagation()}
          className="p-1 text-gray-400 hover:text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <MoreVertical className="w-4 h-4" />
        </button>
      </div>

      {/* Document Icon */}
      <div className="w-10 h-10 bg-purple-50 rounded-lg flex items-center justify-center mb-3">
        <FileText className="w-5 h-5 text-purple-600" />
      </div>

      {/* Title */}
      <h3 className="font-semibold text-gray-900 text-sm mb-1">
        {workflow.research_question ? truncate(workflow.research_question, 40) : 'New Document'}
      </h3>

      {/* Description */}
      <p className="text-xs text-gray-500 line-clamp-2">
        {workflow.inclusion_criteria
          ? `Systematic review of ${truncate(workflow.inclusion_criteria, 50)}`
          : 'Systematic review document'
        }
      </p>

      {/* Status Badge */}
      <div className="mt-3">
        <span className={`
          text-xs px-2 py-0.5 rounded-full
          ${workflow.status === 'completed'
            ? 'bg-green-100 text-green-700'
            : workflow.status === 'running'
              ? 'bg-blue-100 text-blue-700'
              : workflow.status === 'failed'
                ? 'bg-red-100 text-red-700'
                : 'bg-gray-100 text-gray-600'
          }
        `}>
          {workflow.status}
        </span>
      </div>
    </div>
  );
}

export function DocumentsList() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [workflows, setWorkflows] = useState<WorkflowResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const user = useStore((state) => state.auth.user);
  const {
    setCurrentWorkflow,
    setManuscript,
    setLayoutMode,
    setViewMode,
    setChatStage,
    setEditorLoading,
    updateFormData,
    clearMessages,
    resetChat,
  } = useStore();

  // Load workflows on mount
  useEffect(() => {
    const loadWorkflows = async () => {
      setIsLoading(true);
      try {
        const response = await api.listWorkflows();
        setWorkflows(response.workflows);
      } catch (error) {
        console.error('Failed to load workflows:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadWorkflows();
  }, []);

  // Filter workflows based on search
  const filteredWorkflows = workflows.filter((w) =>
    w.research_question?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    w.inclusion_criteria?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id)
        ? prev.filter((i) => i !== id)
        : [...prev, id]
    );
  };

  const handleWorkflowClick = async (workflow: WorkflowResponse) => {
    clearMessages();
    setCurrentWorkflow(workflow);

    updateFormData({
      research_question: workflow.research_question,
      inclusion_criteria: workflow.inclusion_criteria || '',
      exclusion_criteria: workflow.exclusion_criteria || '',
      databases: workflow.databases || ['pubmed'],
    });

    if (workflow.status === 'completed') {
      setEditorLoading(true);
      try {
        const manuscript = await api.getManuscript(workflow.id);
        setManuscript(manuscript);
        setLayoutMode('split-view');
        setViewMode('viewing-workflow');
        setChatStage('complete');
      } catch (error) {
        console.error('Failed to load manuscript:', error);
        setManuscript(null);
        setLayoutMode('chat-fullscreen');
        setViewMode('viewing-workflow');
        setChatStage('complete');
      } finally {
        setEditorLoading(false);
      }
    } else {
      setLayoutMode('chat-fullscreen');
      setViewMode('viewing-workflow');
      setChatStage(workflow.status === 'running' ? 'creating' : 'confirm');
      setManuscript(null);
    }
  };

  const handleNewDocument = () => {
    resetChat();
    setLayoutMode('chat-fullscreen');
    setViewMode('new-review');
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-100">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">AI Writer</h1>
          <p className="text-sm text-gray-500">
            {workflows.length} {workflows.length === 1 ? 'Document' : 'Documents'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button className="relative p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
            <Bell className="w-5 h-5" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
          </button>
          <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
            <HelpCircle className="w-5 h-5" />
          </button>
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center text-white text-sm font-medium">
            {user?.full_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
          </div>
        </div>
      </header>

      {/* Toolbar */}
      <div className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-100">
        {/* Search */}
        <div className="relative w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            type="text"
            placeholder="Search Project or Studies"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-gray-50 border-gray-200"
          />
        </div>

        {/* New Document Button */}
        <Button
          onClick={handleNewDocument}
          className="bg-purple-600 hover:bg-purple-700 text-white"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Document
        </Button>
      </div>

      {/* Documents Grid */}
      <div className="flex-1 overflow-auto p-6">
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-200 p-4 animate-pulse">
                <div className="w-5 h-5 bg-gray-200 rounded mb-3" />
                <div className="w-10 h-10 bg-gray-200 rounded-lg mb-3" />
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
                <div className="h-3 bg-gray-200 rounded w-full mb-1" />
                <div className="h-3 bg-gray-200 rounded w-2/3" />
              </div>
            ))}
          </div>
        ) : filteredWorkflows.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500">
            <FileText className="w-12 h-12 mb-4 text-gray-300" />
            <p className="text-lg font-medium">No documents found</p>
            <p className="text-sm">Start a new systematic review to get started</p>
            <Button
              onClick={handleNewDocument}
              className="mt-4 bg-purple-600 hover:bg-purple-700 text-white"
            >
              <Plus className="w-4 h-4 mr-2" />
              New Document
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredWorkflows.map((workflow) => (
              <DocumentCard
                key={workflow.id}
                workflow={workflow}
                isSelected={selectedIds.includes(workflow.id)}
                onSelect={handleSelect}
                onClick={() => handleWorkflowClick(workflow)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
