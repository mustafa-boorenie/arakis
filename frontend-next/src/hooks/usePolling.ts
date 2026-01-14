'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

interface UsePollingOptions<T> {
  enabled: boolean;
  interval: number;
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
  shouldStop?: (data: T) => boolean;
}

interface UsePollingResult<T> {
  data: T | null;
  error: Error | null;
  isPolling: boolean;
  refetch: () => Promise<void>;
}

export function usePolling<T>(
  fetcher: () => Promise<T>,
  options: UsePollingOptions<T>
): UsePollingResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);

  const poll = useCallback(async () => {
    if (!mountedRef.current) return;

    try {
      const result = await fetcher();
      if (!mountedRef.current) return;

      setData(result);
      setError(null);
      options.onSuccess?.(result);

      if (options.shouldStop?.(result)) {
        setIsPolling(false);
        return;
      }

      // Schedule next poll
      timeoutRef.current = setTimeout(poll, options.interval);
    } catch (err) {
      if (!mountedRef.current) return;
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      options.onError?.(error);
      setIsPolling(false);
    }
  }, [fetcher, options]);

  const refetch = useCallback(async () => {
    await poll();
  }, [poll]);

  useEffect(() => {
    mountedRef.current = true;

    if (!options.enabled) {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      setIsPolling(false);
      return;
    }

    setIsPolling(true);
    poll();

    return () => {
      mountedRef.current = false;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [options.enabled, poll]);

  return { data, error, isPolling, refetch };
}
