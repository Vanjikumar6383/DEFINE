// Simulate shader-background.js fragment shader for 1920x1080 canvas

const overallSpeed = 0.22;
const gridSmoothWidth = 0.015;
const axisWidth = 0.05;
const majorLineWidth = 0.025;
const minorLineWidth = 0.0125;
const majorLineFrequency = 5.0;
const minorLineFrequency = 1.0;
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
  // GLSL standard: if edge0 >= edge1, undefined or:
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

let maxLineVal = 0;
let minLineVal = 999;
let nonZeroCount = 0;

for (let y = 0; y < height; y += 40) {
  for (let x = 0; x < width; x += 40) {
    const uvX = x / width;
    const uvY = y / height;
    let spaceX = (x - width / 2.0) / width * 2.0 * scale;
    let spaceY = (y - height / 2.0) / width * 2.0 * scale;

    const horizontalFade = 1.0 - (Math.cos(uvX * 6.28) * 0.5 + 0.5);
    const verticalFade = 1.0 - (Math.cos(uvY * 6.28) * 0.5 + 0.5);

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

      const circleX = ((l + iTime * lineSpeed) % 25.0) - 12.0;
      const circlePosition = [circleX, getPlasmaY(circleX, horizontalFade, offset, iTime)];
      const circle = drawCircle(circlePosition, 0.014, [spaceX, spaceY]) * 4.5;

      lines += (line + circle) * (0.65 + 0.85 * rand);
    }
    if (lines > 0.001) nonZeroCount++;
    if (lines > maxLineVal) maxLineVal = lines;
    if (lines < minLineVal) minLineVal = lines;
  }
}

console.log({ maxLineVal, minLineVal, nonZeroCount });
