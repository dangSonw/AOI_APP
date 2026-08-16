import { useState } from 'react';
import type {
  AlgorithmDefinition, DataType, ParameterValue, PortChannel, PortDirection,
  RuntimeBindingMode, WorkflowNode,
} from '../../types/workflow';
import { getNodeInspectorPlugin } from '../../node-plugins/registry';
import { addCustomPort, removeCustomPort, updateCustomPort } from '../../utils/workflow-ports';
import { RuntimeUseBadge } from '../RuntimeUseBadge';


interface NodeInspectorProps {
  node: WorkflowNode | null;
  definition: AlgorithmDefinition | null;
  onChange: (node: WorkflowNode) => void;
}

const DATA_TYPES: DataType[] = [
  'generic', 'boolean', 'image', 'image-set', 'mask', 'roi-set', 'keypoints',
  'contours', 'features', 'detections', 'anomaly-map', 'score', 'transform', 'decision',
];

function CustomPortEditor({ node, onChange }: Pick<NodeInspectorProps, 'node' | 'onChange'> & { node: WorkflowNode }) {
  const [key, setKey] = useState('custom-port');
  const [label, setLabel] = useState('Custom port');
  const [direction, setDirection] = useState<PortDirection>('output');
  const [channel, setChannel] = useState<PortChannel>('control');
  const [dataType, setDataType] = useState<DataType>('generic');
  const [runtimeBinding, setRuntimeBinding] = useState<RuntimeBindingMode>('none');
  const [error, setError] = useState('');

  const commit = () => {
    try {
      onChange(addCustomPort(node, {
        templateKey: key,
        displayLabel: label,
        direction,
        channel,
        dataType: channel === 'control' ? 'generic' : dataType,
        runtimeBinding: channel === 'control' ? 'none' : runtimeBinding,
        runtimeKey: channel === 'data' && runtimeBinding === 'slot' ? key : null,
        passthroughInputPortId: null,
      }));
      setError('');
    } catch (portError) {
      setError(portError instanceof Error ? portError.message : 'Custom port is invalid.');
    }
  };

  return (
    <div className="workflow-custom-port-editor">
      <h4>Add custom port</h4>
      <label className="workflow-field"><span>Port key</span><input value={key} onChange={(event) => setKey(event.target.value)} /></label>
      <label className="workflow-field"><span>Label</span><input value={label} onChange={(event) => setLabel(event.target.value)} /></label>
      <label className="workflow-field"><span>Direction</span><select value={direction} onChange={(event) => setDirection(event.target.value as PortDirection)}><option value="input">Input</option><option value="output">Output</option></select></label>
      <label className="workflow-field"><span>Channel</span><select value={channel} onChange={(event) => setChannel(event.target.value as PortChannel)}><option value="control">Control</option><option value="data">Data</option></select></label>
      {channel === 'data' && <>
        <label className="workflow-field"><span>Data type</span><select value={dataType} onChange={(event) => setDataType(event.target.value as DataType)}>{DATA_TYPES.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <label className="workflow-field"><span>Runtime binding</span><select value={runtimeBinding} onChange={(event) => setRuntimeBinding(event.target.value as RuntimeBindingMode)}><option value="none">None</option><option value="slot">Slot</option></select></label>
      </>}
      {error && <small className="workflow-field-error" role="alert">{error}</small>}
      <button type="button" className="secondary-button" onClick={commit}>Add custom port</button>
    </div>
  );
}

export function NodeInspector({ node, definition, onChange }: NodeInspectorProps) {
  if (!node || !definition) {
    return (
      <aside className="workflow-inspector" aria-label="Node inspector">
        <header className="workflow-region-heading"><div><span className="overline">Selection</span><strong>Node inspector</strong></div></header>
        <div className="workflow-empty"><strong>Select a node</strong><p>Edit its name, parameters, and operator-facing port labels here.</p></div>
      </aside>
    );
  }

  const updateParameter = (key: string, value: ParameterValue) => onChange({
    ...node,
    parameters: { ...node.parameters, [key]: value },
  });

  const CustomInspector = definition.inspectorKind === 'custom' ? getNodeInspectorPlugin(definition.customInspectorKey) : null;

  return (
    <aside className="workflow-inspector" aria-label="Node inspector">
      <header className="workflow-region-heading">
        <div><span className="overline">{definition.category}</span><strong>Node inspector</strong></div>
        <code>{definition.id}</code>
      </header>
      <div className="workflow-inspector__body">
        <RuntimeUseBadge use={definition.use} />
        <label className="workflow-field">
          <span>Display name</span>
          <input value={node.displayName} onChange={(event) => onChange({ ...node, displayName: event.target.value })} />
        </label>
        {definition.inspectorKind === 'none' ? (
          <div data-inspector-content="empty" />
        ) : CustomInspector ? (
          <CustomInspector node={node} definition={definition} updateParameter={updateParameter} />
        ) : (
          <section className="workflow-inspector__section" data-inspector-content="generic">
            <h3>Parameters</h3>
            {definition.parameters.map((parameter) => {
              const value = node.parameters[parameter.key];
              return (
                <label className="workflow-field" key={parameter.key}>
                  <span>{parameter.label}{parameter.required ? ' *' : ''}</span>
                  {parameter.kind === 'boolean' ? (
                    <input type="checkbox" checked={Boolean(value)} onChange={(event) => updateParameter(parameter.key, event.target.checked)} />
                  ) : parameter.kind === 'select' ? (
                    <select value={String(value)} onChange={(event) => updateParameter(parameter.key, event.target.value)}>
                      {parameter.options.map((option) => <option value={String(option)} key={String(option)}>{String(option)}</option>)}
                    </select>
                  ) : parameter.kind === 'json' ? (
                    <textarea value={JSON.stringify(value, null, 2)} onChange={(event) => {
                      try { updateParameter(parameter.key, JSON.parse(event.target.value) as ParameterValue); } catch { /* Keep last valid JSON draft. */ }
                    }} />
                  ) : (
                    <input
                      type={parameter.kind === 'integer' || parameter.kind === 'number' ? 'number' : 'text'}
                      value={String(value ?? '')}
                      min={parameter.minimum ?? undefined}
                      max={parameter.maximum ?? undefined}
                      step={parameter.kind === 'integer' ? 1 : parameter.kind === 'number' ? 'any' : undefined}
                      onChange={(event) => updateParameter(parameter.key, parameter.kind === 'integer' || parameter.kind === 'number' ? Number(event.target.value) : event.target.value)}
                    />
                  )}
                  {(parameter.minimum !== null || parameter.maximum !== null || parameter.description) && (
                    <small>{parameter.description || `Range ${parameter.minimum ?? '—'} to ${parameter.maximum ?? '—'}`}</small>
                  )}
                </label>
              );
            })}
          </section>
        )}
        <section className="workflow-inspector__section">
          <h3>Port labels</h3>
          {node.ports.map((port) => (
            <label className="workflow-field workflow-field--port" key={port.id}>
              <span>{port.direction} · {port.dataType}{port.required ? ' · required' : ''}</span>
              <input
                value={port.displayLabel}
                disabled={port.origin === 'system'}
                onChange={(event) => onChange(updateCustomPort(node, port.id, { displayLabel: event.target.value }))}
              />
              <small>Template: {port.templateKey}</small>
              {port.origin === 'system' && <small>System port · locked</small>}
              {port.origin !== 'system' && !port.variadic && (
                <button type="button" className="text-action" onClick={() => onChange(removeCustomPort(node, port.id))}>Remove custom port</button>
              )}
              {port.variadic && port.variadicInstanceIndex !== 0 && (
                <button
                  type="button"
                  className="text-action"
                  onClick={() => onChange({ ...node, ports: node.ports.filter((candidate) => candidate.id !== port.id) })}
                >
                  Remove port instance
                </button>
              )}
            </label>
          ))}
          {definition.inputs.filter((port) => port.variadic).map((template) => (
            <button
              type="button"
              className="secondary-button"
              key={template.key}
              onClick={() => {
                const existing = node.ports.filter((port) => port.templateKey === template.key);
                onChange({
                  ...node,
                  ports: [...node.ports, {
                    id: crypto.randomUUID(),
                    templateKey: template.key,
                    direction: template.direction,
                    dataType: template.dataType,
                    displayLabel: `${template.label} ${existing.length + 1}`,
                    required: false,
                    variadic: true,
                    variadicInstanceIndex: existing.length,
                    channel: 'data',
                    origin: 'default',
                    runtimeBinding: 'slot',
                    runtimeKey: template.key,
                    passthroughInputPortId: null,
                  }],
                });
              }}
            >
              Add {template.label.toLocaleLowerCase()} input
            </button>
          ))}
          <CustomPortEditor node={node} onChange={onChange} />
        </section>
      </div>
    </aside>
  );
}