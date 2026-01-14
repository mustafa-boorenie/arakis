'use client';

import { useStore } from '@/store';
import { WorkflowHistory } from './WorkflowHistory';
import { ExportMenu } from './ExportMenu';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ChatContainer } from '@/components/chat';
import { MessageSquare, History, PlusCircle, FileText } from 'lucide-react';

export function Sidebar() {
  const { resetChat, workflow } = useStore();

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-primary" />
          <span className="font-semibold">Arakis</span>
        </div>
        <div className="flex items-center gap-1">
          <ExportMenu />
          <Button variant="ghost" size="icon" onClick={resetChat} title="New Review">
            <PlusCircle className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="chat" className="flex-1 flex flex-col min-h-0">
        <TabsList className="w-full justify-start rounded-none border-b px-2 h-10">
          <TabsTrigger value="chat" className="gap-1.5 text-xs">
            <MessageSquare className="w-3.5 h-3.5" />
            Chat
          </TabsTrigger>
          <TabsTrigger value="history" className="gap-1.5 text-xs">
            <History className="w-3.5 h-3.5" />
            History
            {workflow.history.length > 0 && (
              <span className="ml-1 text-[10px] bg-muted px-1.5 rounded-full">
                {workflow.history.length}
              </span>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="chat" className="flex-1 m-0 min-h-0 overflow-hidden">
          <div className="h-full overflow-hidden">
            <ChatContainer />
          </div>
        </TabsContent>

        <TabsContent value="history" className="flex-1 m-0 min-h-0">
          <WorkflowHistory />
        </TabsContent>
      </Tabs>
    </div>
  );
}
