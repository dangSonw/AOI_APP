import { useMemo } from 'react';
import type { NodeInspectorPluginProps } from './types';

type ColorFeature = { label: string; color: [number, number, number] };

const DEFAULT_FEATURE: ColorFeature = { label: 'new-feature', color: [128, 128, 128] };

function readFeatures(value: unknown): ColorFeature[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (!item || typeof item !== 'object') return [];
    const record = item as { label?: unknown; color?: unknown };
    if (typeof record.label !== 'string' || !Array.isArray(record.color) || record.color.length !== 3) return [];
    const color = record.color.map(Number);
    if (color.some((channel) => !Number.isFinite(channel))) return [];
    return [{ label: record.label, color: [color[0], color[1], color[2]] as [number, number, number] }];
  });
}

export function KnnImageSegmentationInspector({ node, updateParameter }: NodeInspectorPluginProps) {
  const features = readFeatures(node.parameters.trainingSamples);
  const labels = useMemo(() => [...new Set(features.map((feature) => feature.label))], [features]);
  const foreground = Array.isArray(node.parameters.foregroundLabels)
    ? node.parameters.foregroundLabels.filter((value): value is string => typeof value === 'string')
    : [];

  const updateFeature = (index: number, patch: Partial<ColorFeature>) => {
    const next = features.map((feature, featureIndex) => featureIndex === index ? { ...feature, ...patch } : feature);
    updateParameter('trainingSamples', next);
    const nextLabel = patch.label;
    if (nextLabel && foreground.includes(features[index]?.label)) {
      updateParameter('foregroundLabels', foreground.map((label) => label === features[index].label ? nextLabel : label));
    }
  };

  const toggleForeground = (label: string, checked: boolean) => {
    const next = checked ? [...new Set([...foreground, label])] : foreground.filter((item) => item !== label);
    updateParameter('foregroundLabels', next.length ? next : [label]);
  };

  return (
    <section className="workflow-inspector__section" data-inspector-content="custom">
      <h3>KNN settings</h3>
      <label className="workflow-field">
        <span>K neighbors *</span>
        <input type="number" min={1} max={1000} value={Number(node.parameters.neighbors ?? 3)} onChange={(event) => updateParameter('neighbors', Number(event.target.value))} />
        <small>Must not exceed the number of color features.</small>
      </label>
      <label className="workflow-field">
        <span>Distance metric *</span>
        <select value={String(node.parameters.distanceMetric ?? 'euclidean')} onChange={(event) => updateParameter('distanceMetric', event.target.value)}>
          <option value="euclidean">Euclidean</option>
          <option value="manhattan">Manhattan</option>
        </select>
      </label>
      <label className="workflow-field">
        <span>Distance-weighted vote *</span>
        <input type="checkbox" checked={Boolean(node.parameters.distanceWeighted)} onChange={(event) => updateParameter('distanceWeighted', event.target.checked)} />
      </label>
      <label className="workflow-field">
        <span>Minimum confidence *</span>
        <input type="number" min={0} max={1} step="any" value={Number(node.parameters.minimumConfidence ?? 0.5)} onChange={(event) => updateParameter('minimumConfidence', Number(event.target.value))} />
      </label>
      <h3>KNN color features</h3>
      <p className="workflow-hint">Name each visual feature and set its BGR reference color. Choose which names produce the object mask.</p>
      <div className="workflow-feature-list">
        {features.map((feature, index) => (
          <fieldset className="workflow-feature-card" key={`${feature.label}-${index}`}>
            <legend>Feature {index + 1}</legend>
            <label className="workflow-field">
              <span>Feature name</span>
              <input value={feature.label} onChange={(event) => updateFeature(index, { label: event.target.value })} />
            </label>
            <div className="workflow-feature-color-fields" aria-label={`BGR values for feature ${index + 1}`}>
              {(['B', 'G', 'R'] as const).map((channel, channelIndex) => (
                <label className="workflow-field" key={channel}>
                  <span>{channel}</span>
                  <input
                    type="number"
                    min={0}
                    max={255}
                    value={feature.color[channelIndex]}
                    onChange={(event) => {
                      const color = [...feature.color] as [number, number, number];
                      color[channelIndex] = Math.max(0, Math.min(255, Number(event.target.value)));
                      updateFeature(index, { color });
                    }}
                  />
                </label>
              ))}
            </div>
            {features.length > 2 && <button type="button" className="text-action" onClick={() => updateParameter('trainingSamples', features.filter((_, featureIndex) => featureIndex !== index))}>Remove feature</button>}
          </fieldset>
        ))}
      </div>
      <button type="button" className="secondary-button" onClick={() => updateParameter('trainingSamples', [...features, { ...DEFAULT_FEATURE, label: `feature-${features.length + 1}` }])}>Add color feature</button>
      <fieldset className="workflow-feature-card">
        <legend>Foreground features</legend>
        <p className="workflow-hint">Selected names are rendered white in the output mask.</p>
        {labels.map((label) => (
          <label className="workflow-field" key={label}>
            <span>{label}</span>
            <input type="checkbox" checked={foreground.includes(label)} onChange={(event) => toggleForeground(label, event.target.checked)} />
          </label>
        ))}
      </fieldset>
    </section>
  );
}