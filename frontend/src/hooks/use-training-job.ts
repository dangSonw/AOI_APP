import { useCallback, useEffect, useRef, useState } from 'react';
import type { TrainingJob, TrainingJobCreate } from '../types/training-job';
import { TERMINAL_TRAINING_JOB_STATUSES } from '../types/training-job';

const DEFAULT_POLL_INTERVAL_MS = 1000;
const MIN_POLL_INTERVAL_MS = 250;
const MAX_POLL_INTERVAL_MS = 10_000;

interface TrainingJobPollerOptions {
  runId: string;
  read: (runId: string) => Promise<TrainingJob>;
  onJob: (job: TrainingJob) => void;
  onError: (message: string) => void;
  intervalMs?: number;
}

export interface TrainingJobPoller {
  start: () => void;
  stop: () => void;
}

export function createTrainingJobPoller(options: TrainingJobPollerOptions): TrainingJobPoller {
  const intervalMs = Math.min(MAX_POLL_INTERVAL_MS, Math.max(MIN_POLL_INTERVAL_MS, options.intervalMs ?? DEFAULT_POLL_INTERVAL_MS));
  let timeout: ReturnType<typeof setTimeout> | null = null;
  let isStopped = true;
  let isReading = false;

  const stop = () => {
    isStopped = true;
    if (timeout !== null) clearTimeout(timeout);
    timeout = null;
  };
  const schedule = (delay: number) => {
    if (!isStopped) timeout = setTimeout(() => void poll(), delay);
  };
  const poll = async () => {
    if (isStopped || isReading) return;
    isReading = true;
    try {
      const job = await options.read(options.runId);
      if (isStopped) return;
      options.onJob(job);
      if (TERMINAL_TRAINING_JOB_STATUSES.has(job.status)) stop();
      else schedule(intervalMs);
    } catch (error) {
      if (!isStopped) options.onError(error instanceof Error ? error.message : 'Training progress could not be refreshed.');
    } finally {
      isReading = false;
    }
  };

  return {
    start: () => {
      if (!isStopped) return;
      isStopped = false;
      schedule(0);
    },
    stop,
  };
}

interface UseTrainingJobOptions {
  create: (request: TrainingJobCreate) => Promise<TrainingJob>;
  read: (runId: string) => Promise<TrainingJob>;
  cancel: (runId: string) => Promise<TrainingJob>;
  pollIntervalMs?: number;
}

export function useTrainingJob({ create, read, cancel, pollIntervalMs }: UseTrainingJobOptions) {
  const [job, setJob] = useState<TrainingJob | null>(null);
  const [error, setError] = useState('');
  const [isStarting, setIsStarting] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const startPromise = useRef<Promise<TrainingJob> | null>(null);

  useEffect(() => {
    if (!job || TERMINAL_TRAINING_JOB_STATUSES.has(job.status)) return;
    const poller = createTrainingJobPoller({ runId: job.id, read, onJob: setJob, onError: setError, intervalMs: pollIntervalMs });
    poller.start();
    return poller.stop;
  }, [job?.id, job?.status, pollIntervalMs, read]);

  const start = useCallback((request: TrainingJobCreate) => {
    if (startPromise.current) return startPromise.current;
    setIsStarting(true);
    setError('');
    const pending = create(request).then((created) => {
      setJob(created);
      return created;
    }).catch((startError: unknown) => {
      setError(startError instanceof Error ? startError.message : 'The training job could not be started.');
      throw startError;
    }).finally(() => {
      setIsStarting(false);
      startPromise.current = null;
    });
    startPromise.current = pending;
    return pending;
  }, [create]);

  const cancelCurrent = useCallback(async () => {
    if (!job || isCancelling || TERMINAL_TRAINING_JOB_STATUSES.has(job.status)) return null;
    setIsCancelling(true);
    setError('');
    try {
      const cancelled = await cancel(job.id);
      setJob(cancelled);
      return cancelled;
    } catch (cancelError) {
      setError(cancelError instanceof Error ? cancelError.message : 'The training job could not be cancelled.');
      return null;
    } finally {
      setIsCancelling(false);
    }
  }, [cancel, isCancelling, job]);

  return { job, error, isStarting, isCancelling, start, cancel: cancelCurrent };
}