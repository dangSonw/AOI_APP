import type { NodeInspectorPluginProps } from './types';

export function CameraAcquisitionInspector({ node, updateParameter }: NodeInspectorPluginProps) {
  return (
    <section className="workflow-inspector__section" data-inspector-content="custom">
      <h3>Camera acquisition profile</h3>
      <label className="workflow-field">
        <span>Camera ID</span>
        <input value={String(node.parameters.cameraId ?? '')} onChange={(event) => updateParameter('cameraId', event.target.value)} />
      </label>
      <p className="workflow-hint">Configuration requests use authenticated application services. Live capture stays in Hardware.</p>
    </section>
  );
}
