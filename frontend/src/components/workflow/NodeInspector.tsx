import type { AlgorithmDefinition, ParameterValue, WorkflowNode } from '../../types/workflow';
import { RuntimeUseBadge } from '../RuntimeUseBadge';


interface NodeInspectorProps {
  node: WorkflowNode | null;
  definition: AlgorithmDefinition | null;
  onChange: (node: WorkflowNode) => void;
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
        <section className="workflow-inspector__section">
          <h3>Parameters</h3>
          {definition.parameters.length === 0 && <p className="workflow-hint">This method has no configurable parameters.</p>}
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
        <section className="workflow-inspector__section">
          <h3>Port labels</h3>
          {node.ports.map((port) => (
            <label className="workflow-field workflow-field--port" key={port.id}>
              <span>{port.direction} · {port.dataType}{port.required ? ' · required' : ''}</span>
              <input
                value={port.displayLabel}
                onChange={(event) => onChange({
                  ...node,
                  ports: node.ports.map((candidate) => candidate.id === port.id ? { ...candidate, displayLabel: event.target.value } : candidate),
                })}
              />
              <small>Template: {port.templateKey}</small>
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
                  }],
                });
              }}
            >
              Add {template.label.toLocaleLowerCase()} input
            </button>
          ))}
        </section>
      </div>
    </aside>
  );
}