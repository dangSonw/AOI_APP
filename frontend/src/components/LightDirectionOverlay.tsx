import type { PhotometricLight } from '../types/workstation-preferences';


export function LightDirectionOverlay({ light }: { light: PhotometricLight }) {
  const length = 18 + light.elevation * 0.28;
  return (
    <svg className="light-direction-overlay" viewBox="0 0 100 100" aria-label={`Azimuth ${light.azimuth} degrees, elevation ${light.elevation} degrees`}>
      <circle cx="50" cy="50" r="4" />
      <g transform={`rotate(${light.azimuth} 50 50)`}>
        <line x1="50" y1="50" x2={50 + length} y2="50" style={{ strokeWidth: 2 + light.elevation / 45 }} />
        <path d={`M ${47 + length} 46 L ${50 + length} 50 L ${47 + length} 54`} />
      </g>
      <text x="4" y="94">A {light.azimuth}° · E {light.elevation}°</text>
    </svg>
  );
}