import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import type { HeightmapPayload } from '../../types/visualization';
import { createHeightmapModel, updateHeightmapView, type HeightmapView } from './heightmap-model';

const INITIAL_VIEW: HeightmapView = { yaw: 45, pitch: 35, zoom: 1 };

export default function HeightmapCanvas({ payload, title }: { payload: HeightmapPayload; title: string }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    } catch {
      setError('Interactive 3D is unavailable. Use the heightmap summary below.');
      return;
    }
    const { positions, indices } = createHeightmapModel(payload);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setIndex(new THREE.BufferAttribute(indices, 1));
    geometry.computeVertexNormals();
    const material = new THREE.MeshStandardMaterial({ color: 0x2f81f7, roughness: 0.72, metalness: 0.05, side: THREE.DoubleSide });
    const mesh = new THREE.Mesh(geometry, material);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f172a);
    scene.add(mesh, new THREE.HemisphereLight(0xffffff, 0x334155, 2.2));
    const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 10_000);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    host.append(renderer.domElement);
    let view = INITIAL_VIEW, dragging = false, lastX = 0, lastY = 0, contextLost = false;
    const radius = Math.max(payload.columns * payload.xSpacing, payload.rows * payload.ySpacing, 1) * 1.4;
    const render = () => {
      if (contextLost) return;
      const yaw = THREE.MathUtils.degToRad(view.yaw), pitch = THREE.MathUtils.degToRad(view.pitch), distance = radius / view.zoom;
      camera.position.set(Math.cos(pitch) * Math.sin(yaw) * distance, Math.cos(pitch) * Math.cos(yaw) * distance, Math.sin(pitch) * distance);
      camera.lookAt(0, 0, 0);
      renderer.render(scene, camera);
    };
    const resize = () => {
      const width = Math.max(host.clientWidth, 1), height = Math.max(host.clientHeight, 1);
      renderer.setSize(width, height, false); camera.aspect = width / height; camera.updateProjectionMatrix(); render();
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { renderer.domElement.blur(); return; }
      const next = updateHeightmapView(view, event.key);
      if (next !== view) { event.preventDefault(); view = next; render(); }
    };
    const onPointerDown = (event: PointerEvent) => { dragging = true; lastX = event.clientX; lastY = event.clientY; renderer.domElement.setPointerCapture(event.pointerId); };
    const onPointerMove = (event: PointerEvent) => {
      if (!dragging) return;
      view = { ...view, yaw: view.yaw + (event.clientX - lastX) * 0.35, pitch: Math.max(5, Math.min(85, view.pitch + (event.clientY - lastY) * 0.35)) };
      lastX = event.clientX; lastY = event.clientY; render();
    };
    const onPointerUp = () => { dragging = false; };
    const onWheel = (event: WheelEvent) => { event.preventDefault(); view = { ...view, zoom: Math.max(0.5, Math.min(3, view.zoom - event.deltaY * 0.001)) }; render(); };
    const onLost = (event: Event) => { event.preventDefault(); contextLost = true; setError('The 3D context was lost. Use the heightmap summary below.'); };
    const onRestored = () => { contextLost = false; setError(''); render(); };
    const canvas = renderer.domElement;
    canvas.tabIndex = 0; canvas.setAttribute('role', 'img'); canvas.setAttribute('aria-label', `Interactive 3D heightmap for ${title}`);
    canvas.addEventListener('keydown', onKeyDown); canvas.addEventListener('pointerdown', onPointerDown); canvas.addEventListener('pointermove', onPointerMove);
    canvas.addEventListener('pointerup', onPointerUp); canvas.addEventListener('pointercancel', onPointerUp); canvas.addEventListener('wheel', onWheel, { passive: false });
    canvas.addEventListener('webglcontextlost', onLost); canvas.addEventListener('webglcontextrestored', onRestored);
    const observer = new ResizeObserver(resize); observer.observe(host); resize();
    return () => {
      observer.disconnect(); canvas.removeEventListener('keydown', onKeyDown); canvas.removeEventListener('pointerdown', onPointerDown); canvas.removeEventListener('pointermove', onPointerMove);
      canvas.removeEventListener('pointerup', onPointerUp); canvas.removeEventListener('pointercancel', onPointerUp); canvas.removeEventListener('wheel', onWheel);
      canvas.removeEventListener('webglcontextlost', onLost); canvas.removeEventListener('webglcontextrestored', onRestored);
      geometry.dispose(); material.dispose(); renderer.dispose(); renderer.forceContextLoss(); canvas.remove();
    };
  }, [payload, title]);

  return <div className="heightmap-viewer__canvas" ref={hostRef}>{error && <div className="structured-viewer__status structured-viewer__status--error" role="alert">{error}</div>}</div>;
}