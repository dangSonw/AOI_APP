import { useCallback, useEffect, useState } from 'react';
import { StudioChrome } from '../components/StudioChrome';
import {
  readPhysicalInputs,
  readPhysicalOutputs,
  writePhysicalOutputs,
} from '../services/physical-io-service';
import { readAlgorithmCatalog, readWorkflow } from '../services/workflow-service';
import { readWorkstationPreferences, saveWorkstationPreferences } from '../services/workstation-preference-service';
import type { AuthSession } from '../types/auth';
import type { PhysicalInputState, PhysicalOutputState } from '../types/physical-io';
import type { AlgorithmDefinition, Workflow } from '../types/workflow';
import type { WorkstationPreferences } from '../types/workstation-preferences';
import { createDefaultPreferences } from '../utils/workstation-preferences';
import type { WorkspaceView } from '../types/workspace';
import { CameraManagerPage } from './CameraManagerPage';
import { DashboardPage } from './DashboardPage';
import { DatabasePage } from './DatabasePage';
import { SettingsPage } from './SettingsPage';
import { WorkflowEditorPage } from './WorkflowEditorPage';


const ACTIVE_RECIPE_SLUG = 'rev-c-mainboard';
const DEFAULT_WORKSTATION_ID = 'station-01';

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
  const [catalog, setCatalog] = useState<AlgorithmDefinition[]>([]);
  const [savedPreferences, setSavedPreferences] = useState<WorkstationPreferences>(() => createDefaultPreferences(session.user.id, DEFAULT_WORKSTATION_ID));
  const [draftPreferences, setDraftPreferences] = useState<WorkstationPreferences>(() => createDefaultPreferences(session.user.id, DEFAULT_WORKSTATION_ID));
  const [preferenceError, setPreferenceError] = useState('');
  const [isSavingPreferences, setIsSavingPreferences] = useState(false);

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
      const [nextWorkflow, nextCatalog] = await Promise.all([
        readWorkflow(session.accessToken, ACTIVE_RECIPE_SLUG),
        readAlgorithmCatalog(session.accessToken),
      ]);
      setSavedWorkflow(nextWorkflow);
      setCatalog(nextCatalog);
    } catch (loadError) {
      setWorkflowError(loadError instanceof Error ? loadError.message : 'The saved inspection workflow could not be loaded.');
    }
  }, [session.accessToken]);

  useEffect(() => {
    void loadSavedWorkflow();
  }, [loadSavedWorkflow]);

  useEffect(() => {
    const loadPreferences = async () => {
      setPreferenceError('');
      try {
        const nextPreferences = await readWorkstationPreferences(session.accessToken, DEFAULT_WORKSTATION_ID);
        setSavedPreferences(nextPreferences);
        setDraftPreferences(structuredClone(nextPreferences));
      } catch (loadError) {
        setPreferenceError(loadError instanceof Error ? loadError.message : 'Workstation preferences could not be loaded.');
      }
    };
    void loadPreferences();
  }, [session.accessToken]);

  const isPreferencesDirty = JSON.stringify(savedPreferences) !== JSON.stringify(draftPreferences);
  const savePreferences = async () => {
    setIsSavingPreferences(true);
    setPreferenceError('');
    try {
      const saved = await saveWorkstationPreferences(session.accessToken, draftPreferences);
      setSavedPreferences(saved);
      setDraftPreferences(structuredClone(saved));
    } catch (saveError) {
      setPreferenceError(saveError instanceof Error ? saveError.message : 'Workstation preferences could not be saved.');
      throw saveError;
    } finally {
      setIsSavingPreferences(false);
    }
  };

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
          catalog={catalog}
          preferences={draftPreferences.dashboard}
          onPreferencesChange={(dashboard) => setDraftPreferences((current) => ({ ...current, dashboard }))}
          onOutputToggle={(signalName, currentValue) => void toggleOutput(signalName, currentValue)}
        />
      )}
      {activeView === 'settings' && <SettingsPage preferences={draftPreferences} isDirty={isPreferencesDirty} isSaving={isSavingPreferences} error={preferenceError} onWorkstationIdChange={(workstationId) => setDraftPreferences((current) => ({ ...current, workstationId }))} onSave={savePreferences} />}
      {activeView === 'camera-manager' && <CameraManagerPage preferences={draftPreferences} onChange={setDraftPreferences} />}
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