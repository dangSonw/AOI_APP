const CAMERA_API = 'http://127.0.0.1:9101';
const MOTION_API = 'http://127.0.0.1:9102';
const state = {
  sourceMode: 'test-pattern', selectedImageId: null, emergencyStop: false, webcamStream: null,
  cameraConfigurationDirty: false, motionConfigurationDirty: false,
};

const element = (id) => document.getElementById(id);
const commandId = (prefix) => `${prefix}-${Date.now()}-${crypto.randomUUID().slice(0, 8)}`;

async function api(baseUrl, path, options = {}) {
  const response = await fetch(`${baseUrl}${path}`, options);
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try { detail = (await response.json()).detail ?? detail; } catch { /* Response was not JSON. */ }
    throw new Error(detail);
  }
  return response;
}

function logEvent(device, message) {
  const item = document.createElement('li');
  const now = new Date().toLocaleTimeString();
  item.innerHTML = `<span>${now}</span><strong>${device}</strong><span></span>`;
  item.lastElementChild.textContent = message;
  element('event-log').prepend(item);
}

function showMessage(id, message, isError = false) {
  const output = element(id);
  output.textContent = message;
  output.classList.toggle('message--error', isError);
  logEvent(id.startsWith('camera') ? 'CAMERA' : 'MCU', message);
}

async function refreshHealth() {
  for (const [device, baseUrl] of [['camera', CAMERA_API], ['motion', MOTION_API]]) {
    const output = element(`${device}-health`);
    try {
      const health = await (await api(baseUrl, '/health')).json();
      output.textContent = `${device === 'motion' ? 'MCU' : 'Camera'} · ${health.status}`;
      output.className = `status-chip status-chip--${health.status === 'ready' ? 'ready' : 'fault'}`;
    } catch {
      output.textContent = `${device === 'motion' ? 'MCU' : 'Camera'} · offline`;
      output.className = 'status-chip status-chip--fault';
    }
  }
}

async function configureCamera() {
  await api(CAMERA_API, '/simulation/configuration', {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sourceMode: state.sourceMode === 'test-pattern' ? 'test-pattern' : 'uploaded',
      selectedImageId: state.sourceMode === 'test-pattern' ? null : state.selectedImageId,
      frameDelayMilliseconds: Number(element('frame-delay').value),
      fault: element('camera-fault').value,
    }),
  });
  const preview = element('camera-preview');
  preview.hidden = false;
  element('webcam-preview').hidden = true;
  preview.src = `${CAMERA_API}/simulation/preview?revision=${Date.now()}`;
  element('source-label').textContent = state.sourceMode === 'test-pattern'
    ? 'Built-in test pattern'
    : state.sourceMode === 'webcam'
      ? 'Windows camera frame'
      : 'Uploaded image';
}

async function refreshSimulationConfiguration() {
  const [configuration, images] = await Promise.all([
    api(CAMERA_API, '/simulation/configuration').then((response) => response.json()),
    api(CAMERA_API, '/simulation/images').then((response) => response.json()),
  ]);
  const imageSelect = element('image-select');
  imageSelect.replaceChildren(new Option('Built-in test pattern', ''));
  for (const image of images) imageSelect.add(new Option(image.filename, image.imageId));
  state.selectedImageId = configuration.selectedImageId;
  state.sourceMode = configuration.sourceMode === 'test-pattern'
    ? 'test-pattern'
    : configuration.selectedImageId?.startsWith('webcam-') ? 'webcam' : 'folder';
  imageSelect.value = state.selectedImageId ?? '';
  const sourceInput = document.querySelector(`input[name="camera-source"][value="${state.sourceMode}"]`);
  if (sourceInput) sourceInput.checked = true;
  element('frame-delay').value = configuration.frameDelayMilliseconds;
  element('camera-fault').value = configuration.fault;
  const preview = element('camera-preview');
  preview.hidden = false;
  preview.src = `${CAMERA_API}/simulation/preview?revision=${Date.now()}`;
  element('source-label').textContent = state.sourceMode === 'test-pattern'
    ? 'Built-in test pattern'
    : state.sourceMode === 'webcam' ? 'Windows camera frame' : 'Uploaded image';
}

async function applyCommonCameraConfiguration() {
  await api(CAMERA_API, '/configuration', {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      cameraId: 'top-camera', sensorMode: '3280x2464',
      exposureMicroseconds: Number(element('exposure').value),
      analogGain: Number(element('gain').value),
    }),
  });
  state.cameraConfigurationDirty = false;
  showMessage('camera-message', 'Shared camera configuration applied. AOI Studio will receive it automatically.');
}

async function applyCommonMotionConfiguration() {
  await api(MOTION_API, '/configuration', {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      maximumVelocityMillimetersPerSecond: Number(element('motion-velocity').value),
      maximumAccelerationMillimetersPerSecondSquared: Number(element('motion-acceleration').value),
      settleMilliseconds: Number(element('motion-settle').value),
    }),
  });
  state.motionConfigurationDirty = false;
  showMessage('motion-message', 'Shared motion profile applied. AOI Studio will receive it automatically.');
}

async function refreshCommonConfiguration() {
  const [camera, motion] = await Promise.all([
    api(CAMERA_API, '/configuration').then((response) => response.json()),
    api(MOTION_API, '/configuration').then((response) => response.json()),
  ]);
  if (!state.cameraConfigurationDirty) {
    element('exposure').value = camera.exposureMicroseconds;
    element('gain').value = camera.analogGain;
  }
  if (!state.motionConfigurationDirty) {
    element('motion-velocity').value = motion.maximumVelocityMillimetersPerSecond;
    element('motion-acceleration').value = motion.maximumAccelerationMillimetersPerSecondSquared;
    element('motion-settle').value = motion.settleMilliseconds;
  }
}

async function uploadImage(file, imageId) {
  const pngBlob = await normalizeImageToPng(file);
  const response = await api(
    CAMERA_API,
    `/simulation/images/${encodeURIComponent(imageId)}?filename=${encodeURIComponent(`${imageId}.png`)}`,
    { method: 'PUT', headers: { 'Content-Type': 'image/png' }, body: pngBlob },
  );
  return response.json();
}

async function normalizeImageToPng(file) {
  if (file.type === 'image/png') return file;
  const bitmap = await createImageBitmap(file);
  const canvas = document.createElement('canvas');
  canvas.width = bitmap.width;
  canvas.height = bitmap.height;
  canvas.getContext('2d').drawImage(bitmap, 0, 0);
  bitmap.close();
  return new Promise((resolve, reject) => canvas.toBlob(
    (blob) => blob ? resolve(blob) : reject(new Error('The image could not be converted to PNG.')),
    'image/png',
  ));
}

function safeImageId(filename, index) {
  const stem = filename.replace(/\.[^.]+$/, '').toLowerCase().replace(/[^a-z0-9._-]+/g, '-').replace(/^-|-$/g, '');
  return `${stem || 'image'}-${index + 1}`.slice(0, 120);
}

async function chooseFolder(files) {
  const accepted = Array.from(files).filter((file) => file.type.startsWith('image/'));
  if (!accepted.length) throw new Error('The selected folder does not contain supported images.');
  const imageSelect = element('image-select');
  imageSelect.replaceChildren();
  for (const [index, file] of accepted.entries()) {
    const imageId = safeImageId(file.name, index);
    const source = await uploadImage(file, imageId);
    imageSelect.add(new Option(file.webkitRelativePath || file.name, source.imageId));
  }
  state.sourceMode = 'folder';
  state.selectedImageId = imageSelect.value;
  document.querySelector('input[name="camera-source"][value="folder"]').checked = true;
  await configureCamera();
  showMessage('camera-message', `Loaded ${accepted.length} image source${accepted.length === 1 ? '' : 's'}.`);
}

async function startWindowsCamera() {
  if (state.webcamStream) state.webcamStream.getTracks().forEach((track) => track.stop());
  state.webcamStream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false });
  const video = element('webcam-preview');
  video.srcObject = state.webcamStream;
  video.hidden = false;
  element('camera-preview').hidden = true;
  element('upload-webcam-button').disabled = false;
  state.sourceMode = 'webcam';
  document.querySelector('input[name="camera-source"][value="webcam"]').checked = true;
  if (!video.videoWidth) {
    await new Promise((resolve) => video.addEventListener('loadeddata', resolve, { once: true }));
  }
  await useWebcamFrame();
  video.hidden = false;
  element('camera-preview').hidden = true;
  showMessage('camera-message', 'Windows camera is active and its current frame is feeding the virtual camera.');
}

async function useWebcamFrame() {
  const video = element('webcam-preview');
  if (!video.videoWidth) throw new Error('The Windows camera has not produced a frame yet.');
  const canvas = element('webcam-canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
  const imageId = `webcam-${Date.now()}`;
  const source = await uploadImage(blob, imageId);
  state.selectedImageId = source.imageId;
  await configureCamera();
  showMessage('camera-message', `Webcam frame ${source.width}×${source.height} loaded into the virtual camera.`);
}

async function captureFrame() {
  await configureCamera();
  const requestId = commandId('console-capture');
  const response = await api(CAMERA_API, '/captures', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      requestId, cameraId: 'top-camera', recipeId: 'simulator-console',
      expectedPosition: currentPosition(), sensorMode: state.sourceMode,
      exposureMicroseconds: Number(element('exposure').value), analogGain: Number(element('gain').value),
    }),
  });
  const result = await response.json();
  element('frame-size').textContent = `${result.width}×${result.height} · ${result.byteLength} B`;
  showMessage('camera-message', `Captured ${result.captureId}; SHA-256 ${result.sha256.slice(0, 12)}…`);
}

function currentPosition() {
  return {
    xMillimeters: Number(element('x-output').value),
    yMillimeters: Number(element('y-output').value),
    zMillimeters: Number(element('z-coordinate-output').value),
  };
}

function renderMotion(motion) {
  const { xMillimeters: x, yMillimeters: y, zMillimeters: z } = motion.position;
  element('x-output').value = x.toFixed(3);
  element('y-output').value = y.toFixed(3);
  element('z-coordinate-output').value = z.toFixed(3);
  element('z-output').value = `${z.toFixed(3)} mm`;
  element('z-progress').value = z;
  element('gantry-head').style.left = `${Math.max(0, Math.min(100, x / 3))}%`;
  element('gantry-head').style.top = `${Math.max(0, Math.min(100, y / 2))}%`;
  element('machine-state').textContent = motion.state.replaceAll('-', ' ').toUpperCase();
  element('door-closed').checked = motion.doorClosed;
  element('communication-connected').checked = motion.communicationConnected;
  state.emergencyStop = motion.emergencyStop;
  element('emergency-stop').setAttribute('aria-pressed', String(state.emergencyStop));
  if (motion.fault) showMessage('motion-message', motion.fault, true);
}

async function refreshMotion() {
  const motion = await (await api(MOTION_API, '/state')).json();
  renderMotion(motion);
}

async function motionCommand(path, body) {
  try {
    const response = await api(MOTION_API, path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const result = await response.json();
    await refreshMotion();
    showMessage('motion-message', `${path.split('/').at(-1)} command completed at revision ${result.stateRevision ?? '—'}.`);
  } catch (error) { showMessage('motion-message', error.message, true); }
}

async function updateInterlocks() {
  try {
    const response = await api(MOTION_API, '/simulation/interlocks', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doorClosed: element('door-closed').checked, emergencyStop: state.emergencyStop, communicationConnected: element('communication-connected').checked }),
    });
    renderMotion(await response.json());
  } catch (error) { showMessage('motion-message', error.message, true); }
}

document.querySelectorAll('input[name="camera-source"]').forEach((input) => input.addEventListener('change', async () => {
  try {
    if (input.value === 'test-pattern') { state.sourceMode = 'test-pattern'; state.selectedImageId = null; await configureCamera(); }
    if (input.value === 'webcam') await startWindowsCamera();
  } catch (error) { showMessage('camera-message', error.message, true); }
}));
element('folder-input').addEventListener('change', (event) => chooseFolder(event.target.files).catch((error) => showMessage('camera-message', error.message, true)));
element('webcam-button').addEventListener('click', () => startWindowsCamera().catch((error) => showMessage('camera-message', error.message, true)));
element('upload-webcam-button').addEventListener('click', () => useWebcamFrame().catch((error) => showMessage('camera-message', error.message, true)));
element('image-select').addEventListener('change', async (event) => { state.selectedImageId = event.target.value; state.sourceMode = 'folder'; await configureCamera(); });
element('capture-button').addEventListener('click', () => captureFrame().catch((error) => showMessage('camera-message', error.message, true)));
element('apply-camera-configuration').addEventListener('click', () => applyCommonCameraConfiguration().catch((error) => showMessage('camera-message', error.message, true)));
element('apply-motion-configuration').addEventListener('click', () => applyCommonMotionConfiguration().catch((error) => showMessage('motion-message', error.message, true)));
for (const id of ['exposure', 'gain']) element(id).addEventListener('input', () => { state.cameraConfigurationDirty = true; });
for (const id of ['motion-velocity', 'motion-acceleration', 'motion-settle']) element(id).addEventListener('input', () => { state.motionConfigurationDirty = true; });
element('home-button').addEventListener('click', () => motionCommand('/commands/home', { commandId: commandId('home') }));
element('stop-button').addEventListener('click', () => motionCommand('/commands/stop', { commandId: commandId('stop') }));
element('clear-fault-button').addEventListener('click', () => motionCommand('/commands/clear-fault', { commandId: commandId('clear') }));
element('reset-button').addEventListener('click', () => motionCommand('/simulation/reset', {}));
document.querySelectorAll('[data-jog-axis]').forEach((button) => button.addEventListener('click', () => motionCommand('/commands/jog', {
  commandId: commandId('jog'), axis: button.dataset.jogAxis,
  distanceMillimeters: Number(element('jog-step').value) * Number(button.dataset.jogDirection),
  maximumVelocityMillimetersPerSecond: 20,
})));
element('door-closed').addEventListener('change', updateInterlocks);
element('communication-connected').addEventListener('change', updateInterlocks);
element('emergency-stop').addEventListener('click', () => { state.emergencyStop = !state.emergencyStop; updateInterlocks(); });
element('motion-fault').addEventListener('change', async (event) => {
  try {
    const response = await api(MOTION_API, '/simulation/fault', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ fault: event.target.value }) });
    renderMotion(await response.json());
  } catch (error) { showMessage('motion-message', error.message, true); }
});
element('clear-log').addEventListener('click', () => element('event-log').replaceChildren());

async function initialize() {
  await refreshHealth();
  try { await refreshSimulationConfiguration(); } catch (error) { showMessage('camera-message', error.message, true); }
  try { await refreshMotion(); } catch (error) { showMessage('motion-message', error.message, true); }
  try { await refreshCommonConfiguration(); } catch (error) { showMessage('motion-message', error.message, true); }
  setInterval(refreshHealth, 3000);
  setInterval(() => refreshMotion().catch(() => undefined), 500);
  setInterval(() => refreshCommonConfiguration().catch(() => undefined), 1000);
}

initialize();