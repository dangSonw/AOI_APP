import { useCallback, useEffect, useState } from 'react';
import { StudioChrome } from '../components/StudioChrome';
import {
  readPhysicalInputs,
  readPhysicalOutputs,
  writePhysicalOutputs,
} from '../services/physical-io-service';
import { readWorkflow } from '../services/workflow-service';
import type { AuthSession } from '../types/auth';
import type { PhysicalInputState, PhysicalOutputState } from '../types/physical-io';
import type { Workflow } from '../types/workflow';
import type { WorkspaceView } from '../types/workspace';
import { CameraManagerPage } from './CameraManagerPage';
import { DashboardPage } from './DashboardPage';
import { DatabasePage } from './DatabasePage';
import { SettingsPage } from './SettingsPage';
import { WorkflowEditorPage } from './WorkflowEditorPage';


const ACTIVE_RECIPE_SLUG = 'rev-c-mainboard';

interface WorkspacePageProps {
  session: AuthSession;
  onSignOut: () => void;
}

export function WorkspacePage({ session, onSignOut }: WorkspacePageProps) {
  const [activeView, setActiveView] = useState<WorkspaceView>('dashboard');
  const [inputs, setInputs] = useState<PhysicalInputState | null>(null);
  const [outputs, setOutputs] = useState<PhysicalOutputState | null>(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [savedWorkflow, setSavedWorkflow] = useState<Workflow | null>(null);
  const [workflowError, setWorkflowError] = useState('');
  const [isWorkflowDirty, setIsWorkflowDirty] = useState(false);

  const loadPhysicalState = useCallback(async () => {
    setError('');
    setIsLoading(true);
    try {
      const [nextInputs, nextOutputs] = await Promise.all([
        readPhysicalInputs(session.accessToken),
        readPhysicalOutputs(session.accessToken),
      ]);
      setInputs(nextInputs);
      setOutputs(nextOutputs);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Physical I/O state could not be loaded.');
    } finally {
      setIsLoading(false);
    }
  }, [session.accessToken]);

  useEffect(() => {
    void loadPhysicalState();
  }, [loadPhysicalState]);

  const loadSavedWorkflow = useCallback(async () => {
    setWorkflowError('');
    try {
      setSavedWorkflow(await readWorkflow(session.accessToken, ACTIVE_RECIPE_SLUG));
    } catch (loadError) {
      setWorkflowError(loadError instanceof Error ? loadError.message : 'The saved inspection workflow could not be loaded.');
    }
  }, [session.accessToken]);

  useEffect(() => {
    void loadSavedWorkflow();
  }, [loadSavedWorkflow]);

  useEffect(() => {
    const viewTitles: Record<WorkspaceView, string> = {
      dashboard: 'Inspection workspace',
      settings: 'Settings',
      'camera-manager': 'Camera manager',
      database: 'Inspection database',
      'workflow-editor': 'Workflow editor',
    };
    document.title = `${viewTitles[activeView]} | AOI Studio`;
  }, [activeView]);

  const toggleOutput = async (signalName: string, currentValue: boolean) => {
    if (!outputs) {
      return;
    }

    try {
      const nextOutputs = await writePhysicalOutputs(session.accessToken, {
        ...outputs.signals,
        [signalName]: !currentValue,
      });
      setOutputs(nextOutputs);
    } catch (writeError) {
      setError(writeError instanceof Error ? writeError.message : 'The output signal could not be written.');
    }
  };

  const isMachineReady = Boolean(inputs && !inputs.machine.emergencyStop && inputs.machine.doorClosed);

  const requestViewChange = useCallback((nextView: WorkspaceView) => {
    if (nextView === activeView) return;
    if (activeView === 'workflow-editor' && isWorkflowDirty
      && !window.confirm('Discard unsaved workflow changes and leave the editor?')) {
      return;
    }
    setActiveView(nextView);
  }, [activeView, isWorkflowDirty]);

  return (
    <StudioChrome
      session={session}
      activeView={activeView}
      isMachineReady={isMachineReady}
      isRunning={isRunning}
      onViewChange={requestViewChange}
      onRunToggle={() => setIsRunning((currentValue) => !currentValue)}
      onRefresh={() => void loadPhysicalState()}
      onSignOut={onSignOut}
    >
      {activeView === 'dashboard' && (
        <DashboardPage
          inputs={inputs}
          outputs={outputs}
          isLoading={isLoading}
          error={error}
          isRunning={isRunning}
          workflow={savedWorkflow}
          workflowError={workflowError}
          onConfigureWorkflow={() => requestViewChange('workflow-editor')}
          onOutputToggle={(signalName, currentValue) => void toggleOutput(signalName, currentValue)}
        />
      )}
      {activeView === 'settings' && <SettingsPage />}
      {activeView === 'camera-manager' && <CameraManagerPage />}
      {activeView === 'database' && <DatabasePage />}
      {activeView === 'workflow-editor' && (
        <WorkflowEditorPage
          accessToken={session.accessToken}
          recipeSlug={ACTIVE_RECIPE_SLUG}
          onBack={() => requestViewChange('dashboard')}
          onDirtyChange={setIsWorkflowDirty}
          onWorkflowSaved={setSavedWorkflow}
        />
      )}
    </StudioChrome>
  );
}