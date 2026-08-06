import type { NodeUse } from '../types/workflow';


export function RuntimeUseBadge({ use }: { use: NodeUse }) {
  return <span className={`runtime-use runtime-use--${use}`}>{use[0].toUpperCase() + use.slice(1)}</span>;
}