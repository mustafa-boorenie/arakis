'use client';

/* eslint-disable react-hooks/set-state-in-effect */
import { useEffect, useRef, useState, useCallback, useMemo } from 'react';

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
  const [stopped, setStopped] = useState(false);
  const mountedRef = useRef(true);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Memoize isPolling to avoid issues
  const isPolling = useMemo(() => {
    return options.enabled && !stopped;
  }, [options.enabled, stopped]);

  const clearPollingInterval = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const executePoll = useCallback(async (): Promise<boolean> => {
    try {
      const result = await fetcher();

      setData(result);
      setError(null);
      options.onSuccess?.(result);

      if (options.shouldStop?.(result)) {
        setStopped(true);
        return false;
      }
      return true;
    } catch (err) {
      const pollError = err instanceof Error ? err : new Error(String(err));
      setError(pollError);
      options.onError?.(pollError);
      setStopped(true);
      return false;
    }
  }, [fetcher, options]);

  const refetch = useCallback(async () => {
    setStopped(false);
    await executePoll();
  }, [executePoll]);

  useEffect(() => {
    mountedRef.current = true;
    setStopped(false);

    if (!options.enabled) {
      clearPollingInterval();
      return;
    }

    // Initial fetch
    const initialFetch = async () => {
      const shouldContinue = await executePoll();
      if (!shouldContinue) {
        clearPollingInterval();
      }
    };
    initialFetch();

    // Set up interval for subsequent polls
    intervalRef.current = setInterval(async () => {
      if (!mountedRef.current) {
        clearPollingInterval();
        return;
      }
      const continuePolling = await executePoll();
      if (!continuePolling) {
        clearPollingInterval();
      }
    }, options.interval);

    return () => {
      mountedRef.current = false;
      clearPollingInterval();
    };
  }, [options.enabled, options.interval, executePoll, clearPollingInterval]);

  return { data, error, isPolling, refetch };
}
