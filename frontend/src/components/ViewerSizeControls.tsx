import type { ViewerPreference } from '../types/workstation-preferences';
import { updateViewerSize } from '../utils/workstation-preferences';


interface ViewerSizeControlsProps {
  label: string;
  viewer: ViewerPreference;
  onChange: (viewer: ViewerPreference) => void;
}

export function ViewerSizeControls({ label, viewer, onChange }: ViewerSizeControlsProps) {
  const resize = (widthDelta: number, heightDelta: number) => onChange(
    updateViewerSize(viewer, viewer.widthUnits + widthDelta, viewer.heightUnits + heightDelta),
  );
  return (
    <span className="viewer-size-controls" aria-label={`${label} size controls`}>
      <button type="button" onClick={() => resize(-1, 0)} aria-label={`Make ${label} narrower`}>W−</button>
      <button type="button" onClick={() => resize(1, 0)} aria-label={`Make ${label} wider`}>W＋</button>
      <button type="button" onClick={() => resize(0, -1)} aria-label={`Make ${label} shorter`}>H−</button>
      <button type="button" onClick={() => resize(0, 1)} aria-label={`Make ${label} taller`}>H＋</button>
    </span>
  );
}