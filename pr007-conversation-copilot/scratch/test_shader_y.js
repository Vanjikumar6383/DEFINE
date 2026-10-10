// Test shader distribution across Y coordinates (from top to bottom of screen)
const overallSpeed = 0.22;
const gridSmoothWidth = 0.015;
const scale = 4.2;
const minLineWidth = 0.012;
const maxLineWidth = 0.22;
const lineSpeed = 1.0 * overallSpeed;
const lineAmplitude = 1.0;
const lineFrequency = 0.2;
const warpSpeed = 0.2 * overallSpeed;
const warpFrequency = 0.5;
const warpAmplitude = 1.0;
const offsetFrequency = 0.5;
const offsetSpeed = 1.33 * overallSpeed;
const minOffsetSpread = 0.6;
const maxOffsetSpread = 2.0;
const linesPerGroup = 16;

function clamp(x, minVal, maxVal) {
  return Math.min(Math.max(x, minVal), maxVal);
}

function smoothstep(edge0, edge1, x) {
  if (edge0 === edge1) return x < edge0 ? 0 : 1;
  const t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0);
  return t * t * (3.0 - 2.0 * t);
}

function drawCircle(pos, radius, coord) {
  const len = Math.hypot(coord[0] - pos[0], coord[1] - pos[1]);
  return smoothstep(radius + gridSmoothWidth, radius, len);
}

function drawSmoothLine(pos, halfWidth, t) {
  return smoothstep(halfWidth, 0.0, Math.abs(pos - t));
}

function drawCrispLine(pos, halfWidth, t) {
  return smoothstep(halfWidth + gridSmoothWidth, halfWidth, Math.abs(pos - t));
}

function random(t) {
  return (Math.cos(t) + Math.cos(t * 1.3 + 1.3) + Math.cos(t * 1.4 + 1.4)) / 3.0;
}

function getPlasmaY(x, horizontalFade, offset, iTime) {
  return random(x * lineFrequency + iTime * lineSpeed) * horizontalFade * lineAmplitude + offset;
}

const width = 1920;
const height = 1080;
const iTime = 1.0;

for (let y = 0; y <= height; y += 100) {
  let lineTotalAtY = 0;
  for (let x = 0; x < width; x += 40) {
    const uvX = x / width;
    const uvY = y / height;
    let spaceX = (x - width / 2.0) / width * 2.0 * scale;
    let spaceY = (y - height / 2.0) / width * 2.0 * scale;

    const horizontalFade = 1.0 - (Math.cos(uvX * 6.28) * 0.5 + 0.5);

    spaceY += random(spaceX * warpFrequency + iTime * warpSpeed) * warpAmplitude * (0.5 + horizontalFade);
    spaceX += random(spaceY * warpFrequency + iTime * warpSpeed + 2.0) * warpAmplitude * horizontalFade;

    let lines = 0.0;
    for (let l = 0; l < linesPerGroup; l++) {
      const normalizedLineIndex = l / linesPerGroup;
      const offsetTime = iTime * offsetSpeed;
      const offsetPosition = l + spaceX * offsetFrequency;
      const rand = random(offsetPosition + offsetTime) * 0.5 + 0.5;
      const halfWidth = (minLineWidth + (maxLineWidth - minLineWidth) * (rand * horizontalFade)) / 2.0;
      const offset = random(offsetPosition + offsetTime * (1.0 + normalizedLineIndex)) * (minOffsetSpread + (maxOffsetSpread - minOffsetSpread) * horizontalFade);
      const linePosition = getPlasmaY(spaceX, horizontalFade, offset, iTime);
      const line = drawSmoothLine(linePosition, halfWidth, spaceY) * 0.7 + drawCrispLine(linePosition, halfWidth * 0.18, spaceY) * 1.25;
      lines += line;
    }
    lineTotalAtY += lines;
  }
  // In WebGL: y=0 is BOTTOM, y=1080 is TOP
  console.log(`WebGL y=${y} (screen top is 1080, screen bottom is 0): total line intensity = ${lineTotalAtY.toFixed(2)}`);
}
