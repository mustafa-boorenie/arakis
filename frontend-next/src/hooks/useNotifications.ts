'use client';

import { useEffect, useState, useCallback } from 'react';

interface NotificationOptions {
  body?: string;
  icon?: string;
  tag?: string;
  requireInteraction?: boolean;
}

interface UseNotificationsReturn {
  permission: NotificationPermission | 'unsupported';
  requestPermission: () => Promise<boolean>;
  sendNotification: (title: string, options?: NotificationOptions) => void;
  isSupported: boolean;
}

export function useNotifications(): UseNotificationsReturn {
  const [permission, setPermission] = useState<NotificationPermission | 'unsupported'>('default');
  const [isSupported, setIsSupported] = useState(false);

  // Initialize browser notification support on mount
  useEffect(() => {
    if (typeof window !== 'undefined' && 'Notification' in window) {
      setIsSupported(true);
      setPermission(Notification.permission);
    } else {
      setIsSupported(false);
      setPermission('unsupported');
    }
  }, []);

  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (!isSupported) {
      console.warn('Notifications are not supported in this browser');
      return false;
    }

    if (permission === 'granted') {
      return true;
    }

    if (permission === 'denied') {
      console.warn('Notification permission was previously denied');
      return false;
    }

    try {
      const result = await Notification.requestPermission();
      setPermission(result);
      return result === 'granted';
    } catch (error) {
      console.error('Failed to request notification permission:', error);
      return false;
    }
  }, [isSupported, permission]);

  const sendNotification = useCallback(
    (title: string, options?: NotificationOptions) => {
      if (!isSupported) {
        console.warn('Notifications are not supported');
        return;
      }

      if (permission !== 'granted') {
        console.warn('Notification permission not granted');
        return;
      }

      try {
        const notification = new Notification(title, {
          icon: options?.icon || '/favicon.ico',
          badge: '/favicon.ico',
          ...options,
        });

        // Auto close after 5 seconds unless requireInteraction is true
        if (!options?.requireInteraction) {
          setTimeout(() => notification.close(), 5000);
        }

        // Handle notification click
        notification.onclick = () => {
          window.focus();
          notification.close();
        };
      } catch (error) {
        console.error('Failed to send notification:', error);
      }
    },
    [isSupported, permission]
  );

  return {
    permission,
    requestPermission,
    sendNotification,
    isSupported,
  };
}

// Hook to watch workflow status and send notifications on completion
export function useWorkflowNotifications(
  workflowId: string | null,
  status: string | null,
  researchQuestion: string | null
) {
  const { permission, sendNotification, isSupported } = useNotifications();
  const [lastNotifiedStatus, setLastNotifiedStatus] = useState<string | null>(null);

  // Track notification state to prevent duplicate notifications
  useEffect(() => {
    // Don't send notification if:
    // - No workflow ID or status
    // - Already notified for this status
    // - Notifications not supported or permission not granted
    if (!workflowId || !status || !isSupported || permission !== 'granted') {
      return;
    }

    // Only notify on status changes to completed or failed
    if (status === lastNotifiedStatus) {
      return;
    }

    // Only notify for terminal statuses
    if (status === 'completed') {
      sendNotification('Review Completed!', {
        body: researchQuestion
          ? `Your systematic review "${researchQuestion.slice(0, 50)}..." is ready.`
          : 'Your systematic review is ready.',
        tag: `workflow-${workflowId}`,
      });
      setLastNotifiedStatus(status);
    } else if (status === 'failed') {
      sendNotification('Review Failed', {
        body: researchQuestion
          ? `Your review "${researchQuestion.slice(0, 50)}..." encountered an error.`
          : 'Your systematic review encountered an error.',
        tag: `workflow-${workflowId}`,
        requireInteraction: true,
      });
      setLastNotifiedStatus(status);
    } else if (status === 'needs_review') {
      sendNotification('Action Required', {
        body: 'Your systematic review needs your attention.',
        tag: `workflow-${workflowId}`,
        requireInteraction: true,
      });
      setLastNotifiedStatus(status);
    }
  }, [workflowId, status, permission, isSupported, sendNotification, researchQuestion, lastNotifiedStatus]);
}
