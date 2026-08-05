import { useCallback, useEffect, useState } from 'react';
import { StudioChrome } from '../components/StudioChrome';
import {
  readPhysicalInputs,
  readPhysicalOutputs,
  writePhysicalOutputs,
} from '../services/physical-io-service';
import type { AuthSession } from '../types/auth';
import type { PhysicalInputState, PhysicalOutputState } from '../types/physical-io';
import type { WorkspaceView } from '../types/workspace';
import { CameraManagerPage } from './CameraManagerPage';
import { DashboardPage } from './DashboardPage';
import { DatabasePage } from './DatabasePage';
import { SettingsPage } from './SettingsPage';

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

  useEffect(() => {
    const viewTitles: Record<WorkspaceView, string> = {
      dashboard: 'Inspection workspace',
      settings: 'Settings',
      'camera-manager': 'Camera manager',
      database: 'Inspection database',
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

  return (
    <StudioChrome
      session={session}
      activeView={activeView}
      isMachineReady={isMachineReady}
      isRunning={isRunning}
      onViewChange={setActiveView}
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
          onOutputToggle={(signalName, currentValue) => void toggleOutput(signalName, currentValue)}
        />
      )}
      {activeView === 'settings' && <SettingsPage />}
      {activeView === 'camera-manager' && <CameraManagerPage />}
      {activeView === 'database' && <DatabasePage />}
    </StudioChrome>
  );
}