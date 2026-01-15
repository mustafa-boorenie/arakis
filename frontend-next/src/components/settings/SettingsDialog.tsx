'use client';

import { useState, useEffect } from 'react';
import { Settings, Check, X, ExternalLink, Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { API_BASE_URL } from '@/lib/api/client';

interface RetrievalSource {
  name: string;
  active: boolean;
  requires_api_key: boolean;
  api_key_configured: boolean;
  description?: string;
  coverage?: string;
}

interface SettingsData {
  sources: RetrievalSource[];
  total: number;
  active: number;
  inactive: number;
}

export function SettingsDialog() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<SettingsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      loadSettings();
    }
  }, [open]);

  const loadSettings = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/settings/retrieval-sources`);
      if (!response.ok) throw new Error('Failed to load settings');
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button
          className="w-full flex items-center gap-3 px-3 py-2 text-sm hover:bg-sidebar-accent rounded-lg transition-colors text-left"
        >
          <Settings className="w-4 h-4" />
          Settings
        </button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            PDF Retrieval Sources
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="text-center py-8 text-red-500">
            {error}
          </div>
        ) : data ? (
          <div className="space-y-4">
            {/* Summary */}
            <div className="flex items-center gap-4 p-4 bg-muted/50 rounded-lg">
              <div className="text-center">
                <div className="text-2xl font-bold">{data.active}</div>
                <div className="text-xs text-muted-foreground">Active</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-muted-foreground">{data.inactive}</div>
                <div className="text-xs text-muted-foreground">Inactive</div>
              </div>
              <div className="flex-1 text-right text-sm text-muted-foreground">
                {data.total} sources configured
              </div>
            </div>

            {/* Sources List */}
            <div className="space-y-2">
              {data.sources.map((source) => (
                <div
                  key={source.name}
                  className={`flex items-center gap-3 p-3 rounded-lg border ${
                    source.active
                      ? 'bg-green-500/5 border-green-500/20'
                      : 'bg-muted/30 border-muted'
                  }`}
                >
                  {/* Status Icon */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    source.active
                      ? 'bg-green-500/20 text-green-600'
                      : 'bg-muted text-muted-foreground'
                  }`}>
                    {source.active ? (
                      <Check className="w-4 h-4" />
                    ) : (
                      <X className="w-4 h-4" />
                    )}
                  </div>

                  {/* Source Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium capitalize">
                        {source.name.replace('_', ' ')}
                      </span>
                      {source.requires_api_key && !source.api_key_configured && (
                        <span className="text-xs px-1.5 py-0.5 bg-amber-500/20 text-amber-600 rounded">
                          API key required
                        </span>
                      )}
                    </div>
                    {source.description && (
                      <div className="text-sm text-muted-foreground truncate">
                        {source.description}
                      </div>
                    )}
                  </div>

                  {/* Coverage */}
                  {source.coverage && (
                    <div className="text-xs text-muted-foreground text-right">
                      {source.coverage}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Help Text */}
            <div className="p-4 bg-blue-500/5 border border-blue-500/20 rounded-lg">
              <h4 className="font-medium text-sm mb-2">Configure API Keys</h4>
              <p className="text-sm text-muted-foreground mb-3">
                Add API keys to your backend <code className="px-1 py-0.5 bg-muted rounded text-xs">.env</code> file to enable more sources:
              </p>
              <div className="space-y-1 text-xs font-mono bg-muted/50 p-3 rounded">
                <div><span className="text-blue-500">ELSEVIER_API_KEY</span>=your_key</div>
                <div><span className="text-blue-500">CORE_API_KEY</span>=your_key</div>
                <div><span className="text-blue-500">SEMANTIC_SCHOLAR_API_KEY</span>=your_key</div>
              </div>
              <a
                href="https://dev.elsevier.com/apikey/manage"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-blue-500 hover:underline mt-3"
              >
                Get Elsevier API key
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
