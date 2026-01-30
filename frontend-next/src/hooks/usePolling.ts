'use client';

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';

interface UsePollingOptions<T> {
  enabled: boolean;
  interval: number;
  /** Faster interval when actively processing (optional) */
  activeInterval?: number;
  /** Function to determine if actively processing (uses activeInterval if true) */
  isActive?: (data: T) => boolean;
  /** Add random jitter (0-500ms) to prevent thundering herd */
  jitter?: boolean;
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
  const [currentInterval, setCurrentInterval] = useState(options.interval);
  const mountedRef = useRef(true);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Add jitter (0-500ms) to prevent thundering herd
  const getJitter = useCallback(() => {
    return options.jitter ? Math.random() * 500 : 0;
  }, [options.jitter]);

  // Memoize isPolling to avoid issues
  const isPolling = useMemo(() => {
    return options.enabled && !stopped;
  }, [options.enabled, stopped]);

  const clearPollingInterval = useCallback(() => {
    if (intervalRef.current) {
      clearTimeout(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const executePoll = useCallback(async (): Promise<boolean> => {
    try {
      const result = await fetcher();

      setData(result);
      setError(null);
      options.onSuccess?.(result);

      // Adjust polling interval based on activity
      if (options.activeInterval && options.isActive) {
        const isActiveNow = options.isActive(result);
        const newInterval = isActiveNow ? options.activeInterval : options.interval;
        if (newInterval !== currentInterval) {
          setCurrentInterval(newInterval);
        }
      }

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
  }, [fetcher, options, currentInterval]);

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

    // Set up polling with dynamic interval and jitter
    const scheduleNextPoll = (isInitial = false) => {
      // For initial fetch, poll immediately; otherwise use interval + jitter
      const delay = isInitial ? 0 : currentInterval + getJitter();
      intervalRef.current = setTimeout(async () => {
        if (!mountedRef.current) {
          return;
        }
        const continuePolling = await executePoll();
        if (continuePolling && mountedRef.current) {
          scheduleNextPoll(false);
        }
      }, delay);
    };

    scheduleNextPoll(true);

    return () => {
      mountedRef.current = false;
      clearPollingInterval();
    };
  }, [options.enabled, currentInterval, executePoll, clearPollingInterval, getJitter]);

  return { data, error, isPolling, refetch };
}
