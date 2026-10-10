// Test updated shader math with corrected smoothstep and spread
const overallSpeed = 0.22;
const gridSmoothWidth = 0.015;
const scale = 3.6;
const minLineWidth = 0.025;
const maxLineWidth = 0.32;
const lineSpeed = 1.0 * overallSpeed;
const lineAmplitude = 1.35;
const lineFrequency = 0.22;
const warpSpeed = 0.2 * overallSpeed;
const warpFrequency = 0.45;
const warpAmplitude = 1.15;
const offsetFrequency = 0.45;
const offsetSpeed = 1.25 * overallSpeed;
const minOffsetSpread = 0.8;
const maxOffsetSpread = 2.4;

function clamp(x, minVal, maxVal) {
  return Math.min(Math.max(x, minVal), maxVal);
}

function smoothstep(edge0, edge1, x) {
  const t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0);
  return t * t * (3.0 - 2.0 * t);
}

function drawCircle(pos, radius, coord) {
  const d = Math.hypot(coord[0] - pos[0], coord[1] - pos[1]);
  return 1.0 - smoothstep(radius, radius + gridSmoothWidth, d);
}

function drawSmoothLine(pos, halfWidth, t) {
  const d = Math.abs(pos - t);
  return 1.0 - smoothstep(0.0, Math.max(halfWidth, 0.001), d);
}

function drawCrispLine(pos, halfWidth, t) {
  const d = Math.abs(pos - t);
  return 1.0 - smoothstep(halfWidth, halfWidth + gridSmoothWidth, d);
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

    const horizontalFade = Math.min(Math.max(0.4 + 0.6 * (1.0 - Math.abs(uvX - 0.5) * 1.2), 0.25), 1.0);

    spaceY += random(spaceX * warpFrequency + iTime * warpSpeed) * warpAmplitude * (0.5 + horizontalFade);
    spaceX += random(spaceY * warpFrequency + iTime * warpSpeed + 2.0) * warpAmplitude * horizontalFade;

    let lines = 0.0;
    for (let l = 0; l < 16; l++) {
      const normalizedLineIndex = l / 16.0;
      const offsetTime = iTime * offsetSpeed;
      const offsetPosition = l + spaceX * offsetFrequency;
      const rand = random(offsetPosition + offsetTime) * 0.5 + 0.5;
      const halfWidth = (minLineWidth + (maxLineWidth - minLineWidth) * (rand * horizontalFade)) * 0.5;
      const offset = (l - 7.5) * 0.22 + random(offsetPosition + offsetTime * (1.0 + normalizedLineIndex)) * (minOffsetSpread + (maxOffsetSpread - minOffsetSpread) * horizontalFade) * 0.6;
      const linePosition = getPlasmaY(spaceX, horizontalFade, offset, iTime);
      const smoothL = drawSmoothLine(linePosition, halfWidth, spaceY);
      const crispL = drawCrispLine(linePosition, halfWidth * 0.22, spaceY);
      lines += smoothL * 0.75 + crispL * 1.5;
    }
    lineTotalAtY += lines;
  }
  console.log(`y=${y} (top is 1080, bottom is 0): total line intensity = ${lineTotalAtY.toFixed(2)}`);
}
