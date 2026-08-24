import { useEffect, useState } from 'react';
import type {
  AlgorithmDefinition, DataType, ParameterValue, PortChannel, PortDirection,
  RuntimeBindingMode, WorkflowNode,
} from '../../types/workflow';
import { getNodeInspectorPlugin } from '../../node-plugins/registry';
import { addCustomPort, removeCustomPort, updateCustomPort } from '../../utils/workflow-ports';
import { RuntimeUseBadge } from '../RuntimeUseBadge';
import { readRegisteredModels } from '../../services/research-service';
import type { RegisteredModel } from '../../types/research';
import type { NodePluginPlatformContext } from '../../node-plugins/types';
import { cancelTrainingJob, createTrainingJob, readTrainingJob } from '../../services/training-job-service';


interface NodeInspectorProps {
  node: WorkflowNode | null;
  definition: AlgorithmDefinition | null;
  onChange: (node: WorkflowNode) => void;
  accessToken?: string;
  recipeSlug?: string;
  workflowRevision?: number;
  onOpenRun?: (runId: string) => void;
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

function ModelReferenceField({
  accessToken, value, onChange,
}: {
  accessToken?: string;
  value: ParameterValue | undefined;
  onChange: (value: ParameterValue) => void;
}) {
  const [models, setModels] = useState<RegisteredModel[]>([]);
  const [error, setError] = useState('');
  const [taskFilter, setTaskFilter] = useState('');
  const [frameworkFilter, setFrameworkFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [aliasFilter, setAliasFilter] = useState('');

  useEffect(() => {
    if (!accessToken) return;
    void readRegisteredModels(accessToken).then(setModels).catch((loadError: unknown) => {
      setError(loadError instanceof Error ? loadError.message : 'Models could not be loaded.');
    });
  }, [accessToken]);

  const current = value && typeof value === 'object' && !Array.isArray(value)
    && 'modelName' in value && 'alias' in value
    ? `${String(value.modelName)}:${String(value.alias)}` : '';
  const candidates = models.flatMap((model) => ['candidate', 'champion'].flatMap((alias) => {
    const versionNumber = model.aliases[alias];
    const version = model.versions.find((item) => item.version === versionNumber);
    const compatibility = version?.compatibility ?? {};
    const matchesFilter = version
      && (!taskFilter || compatibility.task === taskFilter)
      && (!frameworkFilter || compatibility.framework === frameworkFilter)
      && (!statusFilter || compatibility.status === statusFilter)
      && (!aliasFilter || alias === aliasFilter);
    return matchesFilter && version.artifactVerified && version.validationEvidence.passed === true
      ? [{ model, alias, version }] : [];
  }));
  const filterOptions = (key: 'task' | 'framework' | 'status') => Array.from(new Set(models.flatMap((model) => model.versions.map((version) => version.compatibility[key]).filter((value): value is string => Boolean(value))))).sort();

  return (
    <>
      <label className="workflow-field"><span>Filter by task</span><select aria-label="Filter by task" value={taskFilter} onChange={(event) => setTaskFilter(event.target.value)}><option value="">All tasks</option>{filterOptions('task').map((option) => <option key={option} value={option}>{option}</option>)}</select></label>
      <label className="workflow-field"><span>Filter by framework</span><select aria-label="Filter by framework" value={frameworkFilter} onChange={(event) => setFrameworkFilter(event.target.value)}><option value="">All frameworks</option>{filterOptions('framework').map((option) => <option key={option} value={option}>{option}</option>)}</select></label>
      <label className="workflow-field"><span>Filter by status</span><select aria-label="Filter by status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">All statuses</option>{filterOptions('status').map((option) => <option key={option} value={option}>{option}</option>)}</select></label>
      <label className="workflow-field"><span>Filter by alias</span><select aria-label="Filter by alias" value={aliasFilter} onChange={(event) => setAliasFilter(event.target.value)}><option value="">All aliases</option><option value="candidate">Candidate</option><option value="champion">Champion</option></select></label>
      <select
        aria-label="Model reference"
        value={current}
        disabled={!accessToken}
        onChange={(event) => {
          const [modelName, alias] = event.target.value.split(':', 2);
          if (modelName && alias) onChange({ modelName, alias });
        }}
      >
        <option value="">Select a promoted, verified model</option>
        {candidates.map(({ model, alias, version }) => (
          <option key={`${model.name}:${alias}`} value={`${model.name}:${alias}`}>
            {model.name} · {alias} · v{version.version}
          </option>
        ))}
      </select>
      {!accessToken && <small className="workflow-field-error">Model selection requires an authenticated workflow session.</small>}
      {accessToken && !error && candidates.length === 0 && <small className="workflow-field-error">No validated, promoted model with a verified artifact matches the selected filters.</small>}
      {error && <small className="workflow-field-error" role="alert">{error}</small>}
      {current && <small>Portable alias reference; it resolves to an immutable model version at execution.</small>}
      {current && !models.some((model) => Object.entries(model.aliases).some(([alias, version]) => `${model.name}:${alias}` === current && model.versions.some((item) => item.version === version && item.artifactVerified && item.validationEvidence.passed === true))) && <small className="workflow-field-error">The selected model alias is unresolved, unvalidated, or has an unavailable artifact.</small>}
    </>
  );
}

export function NodeInspector({
  node, definition, onChange, accessToken, recipeSlug, workflowRevision, onOpenRun,
}: NodeInspectorProps) {
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
  const context: NodePluginPlatformContext | undefined = accessToken && recipeSlug && workflowRevision && node
    ? {
      accessToken,
      recipeSlug,
      workflowRevision,
      nodeInstanceId: node.id,
      training: {
        create: (request) => createTrainingJob(accessToken, {
          ...request, recipeSlug, workflowRevision, nodeInstanceId: node.id,
        }),
        read: (runId) => readTrainingJob(accessToken, runId),
        cancel: (runId) => cancelTrainingJob(accessToken, runId),
        openRun: onOpenRun ?? (() => undefined),
      },
    }
    : undefined;

  return (
    <aside className="workflow-inspector" aria-label="Node inspector">
      <header className="workflow-region-heading">
        <div><span className="overline">{definition.category}</span><strong>Node inspector</strong></div>
        <code>{definition.id}</code>
      </header>
      <div className="workflow-inspector__body">
        <RuntimeUseBadge use={definition.use} />
        <label className="workflow-field">
          <span>{definition.id === 'input-pin' || definition.id === 'output-pin' ? 'Pin name' : 'Display name'}</span>
          <input value={node.displayName} onChange={(event) => onChange({ ...node, displayName: event.target.value })} />
          {(definition.id === 'input-pin' || definition.id === 'output-pin') && (
            <small>Input Pin and Output Pin names are trimmed and case-sensitive.</small>
          )}
        </label>
        {definition.inspectorKind === 'none' ? (
          <div data-inspector-content="empty" />
        ) : CustomInspector ? (
          <CustomInspector node={node} definition={definition} updateParameter={updateParameter} context={context} />
        ) : (
          <section className="workflow-inspector__section" data-inspector-content="generic">
            <h3>Parameters</h3>
            {definition.parameters.filter((parameter) => parameter.key !== 'implementation').map((parameter) => {
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
                  ) : parameter.kind === 'model-reference' ? (
                    <ModelReferenceField accessToken={accessToken} value={value} onChange={(nextValue) => updateParameter(parameter.key, nextValue)} />
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