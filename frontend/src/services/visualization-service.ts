import { apiBlobRequest } from './api-client';
import { parseVisualizationPayload, type VisualizationPayload } from '../types/visualization';

export const MAX_VISUALIZATION_ARTIFACT_BYTES = 2 * 1024 * 1024;

export type VisualizationArtifact =
  | { kind: 'structured'; payload: VisualizationPayload }
  | { kind: 'media'; blob: Blob; mediaType: 'image/png' | 'image/svg+xml' };

export async function readVisualizationArtifact(accessToken: string, artifactEndpoint: string): Promise<VisualizationArtifact> {
  if (!/^\/api\/v1\/research\/artifacts\/\d+$/.test(artifactEndpoint)) throw new Error('Artifact endpoint is invalid.');
  const blob = await apiBlobRequest(artifactEndpoint, accessToken);
  if (blob.size > MAX_VISUALIZATION_ARTIFACT_BYTES) throw new Error('Artifact exceeds the 2 MB limit.');
  const mediaType = blob.type.split(';', 1)[0].toLowerCase();
  if (mediaType === 'image/png' || mediaType === 'image/svg+xml') {
    return { kind: 'media', blob, mediaType };
  }
  if (mediaType && mediaType !== 'application/json') throw new Error('Artifact media type is unsupported.');
  try {
    return { kind: 'structured', payload: parseVisualizationPayload(JSON.parse(await blob.text())) };
  } catch (error) {
    if (error instanceof Error && error.message.startsWith('Visualization')) throw error;
    throw new Error('Artifact is malformed.');
  }
}