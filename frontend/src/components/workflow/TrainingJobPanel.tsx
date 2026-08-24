import type { TrainingJob } from '../../types/training-job';
import { TERMINAL_TRAINING_JOB_STATUSES } from '../../types/training-job';

interface TrainingJobPanelProps {
  job: TrainingJob | null;
  error: string;
  isStarting: boolean;
  isCancelling: boolean;
  onStart: () => void;
  onCancel: () => void;
  onOpenRun: (runId: string) => void;
}

export function createTrainingJobActions(start: () => Promise<TrainingJob>) {
  let pending: Promise<TrainingJob> | null = null;
  return {
    start: () => {
      if (pending) return pending;
      pending = start().finally(() => { pending = null; });
      return pending;
    },
  };
}

export function TrainingJobPanel({
  job, error, isStarting, isCancelling, onStart, onCancel, onOpenRun,
}: TrainingJobPanelProps) {
  const isActive = Boolean(job && !TERMINAL_TRAINING_JOB_STATUSES.has(job.status));
  const progressPercent = job?.progress?.fraction === null || job?.progress?.fraction === undefined
    ? null : Math.round(job.progress.fraction * 100);

  return (
    <section className="workflow-inspector__section training-job-panel" aria-labelledby="training-job-heading">
      <h3 id="training-job-heading">Training job</h3>
      <div aria-live="polite">
        {!job && <p>No training job has been started.</p>}
        {job && <p><strong>Status:</strong> {job.status}</p>}
        {job?.progress && (
          <>
            <div
              role="progressbar"
              aria-label="Training progress"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progressPercent ?? undefined}
              aria-valuetext={progressPercent === null ? `${job.progress.processedUnits} units processed` : `${progressPercent}%`}
            >
              {progressPercent === null ? `${job.progress.processedUnits} processed` : `${progressPercent}%`}
            </div>
            {job.progress.message && <p>{job.progress.message}</p>}
          </>
        )}
        {(error || job?.error) && <p className="workflow-field-error" role="alert">{error || job?.error}</p>}
      </div>
      <div className="training-job-panel__actions">
        <button type="button" className="primary-button" disabled={isStarting || isActive} onClick={onStart}>
          {isStarting ? 'Starting…' : 'Start job'}
        </button>
        {isActive && (
          <button type="button" className="secondary-button" disabled={isCancelling} onClick={onCancel}>
            {isCancelling ? 'Cancelling…' : 'Cancel job'}
          </button>
        )}
        {job && <button type="button" className="text-action" onClick={() => onOpenRun(job.id)}>Open run</button>}
      </div>
    </section>
  );
}