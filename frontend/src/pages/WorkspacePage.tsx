import { useCallback, useEffect, useState } from 'react';
import { StudioChrome } from '../components/StudioChrome';
import {
  readPhysicalInputs,
  readPhysicalOutputs,
  writePhysicalOutputs,
} from '../services/physical-io-service';
import { readAlgorithmCatalog, readWorkflow } from '../services/workflow-service';
import { readDeviceSnapshot } from '../services/device-service';
import {
  cancelInspectionRun,
  readLatestInspectionRun,
  readInspectionRun,
  readRecipes,
  startInspectionRun,
} from '../services/inspection-service';
import { readWorkstationPreferences, saveWorkstationPreferences } from '../services/workstation-preference-service';
import type { AuthSession } from '../types/auth';
import type { PhysicalInputState, PhysicalOutputState } from '../types/physical-io';
import type { DeviceSnapshot } from '../types/devices';
import type { InspectionRun } from '../types/inspection';
import type { Workflow } from '../types/workflow';
import type { AlgorithmDefinition } from '../types/workflow';
import type { WorkstationPreferences } from '../types/workstation-preferences';
import { createDefaultPreferences } from '../utils/workstation-preferences';
import type { WorkspaceView } from '../types/workspace';
import { CameraManagerPage } from './CameraManagerPage';
import { DashboardPage } from './DashboardPage';
import { DatabasePage } from './DatabasePage';
import { DatasetPage } from './DatasetPage';
import { HardwarePage } from './HardwarePage';
import { ResearchPage } from './ResearchPage';
import { SettingsPage } from './SettingsPage';
import { WorkflowEditorPage } from './WorkflowEditorPage';


const ACTIVE_RECIPE_SLUG = 'rev-c-mainboard';
const DEFAULT_WORKSTATION_ID = 'station-01';
const WORKSPACE_SHORTCUT_VIEWS: WorkspaceView[] = ['dashboard', 'database', 'research', 'hardware', 'settings'];

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
  const [inspectionRun, setInspectionRun] = useState<InspectionRun | null>(null);
  const [runError, setRunError] = useState('');
  const [isRunControlBusy, setIsRunControlBusy] = useState(false);
  const [savedWorkflow, setSavedWorkflow] = useState<Workflow | null>(null);
  const [algorithmCatalog, setAlgorithmCatalog] = useState<AlgorithmDefinition[]>([]);
  const [workflowError, setWorkflowError] = useState('');
  const [isWorkflowDirty, setIsWorkflowDirty] = useState(false);
  const [savedPreferences, setSavedPreferences] = useState<WorkstationPreferences>(() => createDefaultPreferences(session.user.id, DEFAULT_WORKSTATION_ID));
  const [draftPreferences, setDraftPreferences] = useState<WorkstationPreferences>(() => createDefaultPreferences(session.user.id, DEFAULT_WORKSTATION_ID));
  const [preferenceError, setPreferenceError] = useState('');
  const [isSavingPreferences, setIsSavingPreferences] = useState(false);
  const [deviceSnapshot, setDeviceSnapshot] = useState<DeviceSnapshot | null>(null);
  const [deviceError, setDeviceError] = useState('');
  const [isLoadingDevices, setIsLoadingDevices] = useState(false);

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

  const loadDevices = useCallback(async () => {
    setIsLoadingDevices(true);
    try {
      const nextSnapshot = await readDeviceSnapshot(session.accessToken);
      setDeviceSnapshot(nextSnapshot);
      setDeviceError('');
    } catch (loadError) {
      setDeviceSnapshot(null);
      setDeviceError(loadError instanceof Error ? loadError.message : 'Device adapters could not be loaded.');
    } finally {
      setIsLoadingDevices(false);
    }
  }, [session.accessToken]);

  useEffect(() => {
    if (activeView !== 'hardware' && activeView !== 'settings') return;
    void loadDevices();
    const interval = window.setInterval(() => void loadDevices(), activeView === 'hardware' ? 1000 : 5000);
    return () => window.clearInterval(interval);
  }, [activeView, loadDevices]);

  const loadSavedWorkflow = useCallback(async () => {
    setWorkflowError('');
    try {
      const [nextWorkflow, nextCatalog] = await Promise.all([
        readWorkflow(session.accessToken, ACTIVE_RECIPE_SLUG),
        readAlgorithmCatalog(session.accessToken),
      ]);
      setSavedWorkflow(nextWorkflow);
      setAlgorithmCatalog(nextCatalog);
    } catch (loadError) {
      setWorkflowError(loadError instanceof Error ? loadError.message : 'The saved inspection workflow could not be loaded.');
    }
  }, [session.accessToken]);

  useEffect(() => {
    void loadSavedWorkflow();
  }, [loadSavedWorkflow]);

  useEffect(() => {
    const restoreActiveRun = async () => {
      try {
        const run = await readLatestInspectionRun(session.accessToken);
        setInspectionRun(run);
        setIsRunning(Boolean(run && ['queued', 'precheck', 'capturing', 'executing'].includes(run.status)));
      } catch (loadError) {
        setRunError(loadError instanceof Error ? loadError.message : 'Inspection runtime state could not be restored.');
      }
    };
    void restoreActiveRun();
  }, [session.accessToken]);

  useEffect(() => {
    if (!inspectionRun || !['queued', 'precheck', 'capturing', 'executing'].includes(inspectionRun.status)) return;
    const interval = window.setInterval(async () => {
      try {
        const nextRun = await readInspectionRun(session.accessToken, inspectionRun.id);
        setInspectionRun(nextRun);
        setIsRunning(['queued', 'precheck', 'capturing', 'executing'].includes(nextRun.status));
        if (['completed', 'faulted', 'cancelled'].includes(nextRun.status)) window.clearInterval(interval);
      } catch (loadError) {
        setRunError(loadError instanceof Error ? loadError.message : 'Inspection progress could not be refreshed.');
      }
    }, 500);
    return () => window.clearInterval(interval);
  }, [inspectionRun?.id, inspectionRun?.status, session.accessToken]);

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
  const selectWorkstation = async (workstationId: string) => {
    setPreferenceError('');
    try {
      const nextPreferences = await readWorkstationPreferences(session.accessToken, workstationId);
      setSavedPreferences(nextPreferences);
      setDraftPreferences(structuredClone(nextPreferences));
    } catch (loadError) {
      setPreferenceError(loadError instanceof Error ? loadError.message : 'Workstation preferences could not be loaded.');
      throw loadError;
    }
  };
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
      hardware: 'Hardware',
      'camera-manager': 'Camera manager',
      database: 'Inspection database',
      dataset: 'Dataset manager',
      'workflow-editor': 'Workflow editor',
      research: 'Research workspace',
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

  const toggleInspectionRun = async () => {
    setRunError('');
    setIsRunControlBusy(true);
    try {
      if (isRunning && inspectionRun) {
        const cancelled = await cancelInspectionRun(session.accessToken, inspectionRun.id);
        setInspectionRun(cancelled);
        setIsRunning(!['completed', 'faulted', 'cancelled'].includes(cancelled.status));
        return;
      }
      if (!isMachineReady) throw new Error('Machine safety inputs must be ready before inspection starts.');
      const recipes = await readRecipes(session.accessToken);
      const recipe = recipes.find((item) => item.slug === ACTIVE_RECIPE_SLUG);
      if (!recipe) throw new Error('Active Rev C mainboard recipe is unavailable.');
      const timestamp = new Date().toISOString().replace(/\D/g, '').slice(0, 17);
      const started = await startInspectionRun(session.accessToken, {
        boardSerial: `AUTO-${timestamp}`,
        lot: '',
        recipeId: recipe.id,
        threshold: 0.5,
      });
      setInspectionRun(started);
      setIsRunning(true);
    } catch (runFailure) {
      setRunError(runFailure instanceof Error ? runFailure.message : 'Inspection run control failed.');
    } finally {
      setIsRunControlBusy(false);
    }
  };

  const requestViewChange = useCallback((nextView: WorkspaceView) => {
    if (nextView === activeView) return;
    if (activeView === 'workflow-editor' && isWorkflowDirty
      && !window.confirm('Discard unsaved workflow changes and leave the editor?')) {
      return;
    }
    setActiveView(nextView);
  }, [activeView, isWorkflowDirty]);

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      if ((!event.ctrlKey && !event.metaKey) || event.altKey) return;
      const target = event.target;
      if (target instanceof HTMLElement && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))) return;
      let nextView: WorkspaceView | undefined;
      if (event.key === 'Tab') {
        const currentIndex = WORKSPACE_SHORTCUT_VIEWS.indexOf(activeView);
        const offset = event.shiftKey ? -1 : 1;
        nextView = WORKSPACE_SHORTCUT_VIEWS[(Math.max(currentIndex, 0) + offset + WORKSPACE_SHORTCUT_VIEWS.length) % WORKSPACE_SHORTCUT_VIEWS.length];
      } else if (/^[1-5]$/.test(event.key)) {
        nextView = WORKSPACE_SHORTCUT_VIEWS[Number(event.key) - 1];
      }
      if (nextView) {
        event.preventDefault();
        requestViewChange(nextView);
      }
    };
    window.addEventListener('keydown', handleShortcut);
    return () => window.removeEventListener('keydown', handleShortcut);
  }, [activeView, requestViewChange]);

  return (
    <StudioChrome
      session={session}
      activeView={activeView}
      isMachineReady={isMachineReady}
      isRunning={isRunning}
      isRunControlBusy={isRunControlBusy}
      onViewChange={requestViewChange}
      onRunToggle={() => void toggleInspectionRun()}
      onRefresh={() => void loadPhysicalState()}
      onSignOut={onSignOut}
    >
      {activeView === 'dashboard' && (
        <DashboardPage
          accessToken={session.accessToken}
          inputs={inputs}
          outputs={outputs}
          isLoading={isLoading}
          error={error}
          isRunning={isRunning}
          inspectionRun={inspectionRun}
          runError={runError}
          workflow={savedWorkflow}
          algorithmCatalog={algorithmCatalog}
          workflowError={workflowError}
          onConfigureWorkflow={() => requestViewChange('workflow-editor')}
          preferences={draftPreferences.dashboard}
          onPreferencesChange={(dashboard) => setDraftPreferences((current) => ({ ...current, dashboard }))}
          onOutputToggle={(signalName, currentValue) => void toggleOutput(signalName, currentValue)}
        />
      )}
      {activeView === 'settings' && <SettingsPage accessToken={session.accessToken} deviceSnapshot={deviceSnapshot} preferences={draftPreferences} isDirty={isPreferencesDirty} isSaving={isSavingPreferences} error={preferenceError || deviceError} onWorkstationSelect={selectWorkstation} onPreferencesChange={setDraftPreferences} onSave={savePreferences} onOpenHardware={() => requestViewChange('hardware')} />}
      {activeView === 'hardware' && <HardwarePage accessToken={session.accessToken} snapshot={deviceSnapshot} error={deviceError} isLoading={isLoadingDevices} onRefresh={loadDevices} />}
      {activeView === 'camera-manager' && <CameraManagerPage preferences={draftPreferences} onChange={setDraftPreferences} />}
      {activeView === 'database' && <DatabasePage accessToken={session.accessToken} />}
      {activeView === 'dataset' && <DatasetPage accessToken={session.accessToken} />}
      {activeView === 'research' && <ResearchPage accessToken={session.accessToken} />}
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