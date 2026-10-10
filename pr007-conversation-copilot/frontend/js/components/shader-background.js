/**
 * Silver-White Shader Background (WebGL + Robust Canvas2D Fallback)
 * Exclusive to the Nimad Copilot Dashboard screen.
 * Renders glowing, metallic silver & platinum fluid wave lines and particle nodes.
 */
export function initShaderBackground(canvasId = 'shader-background-canvas') {
  let canvas = document.getElementById(canvasId);
  if (!canvas) {
    canvas = document.createElement('canvas');
    canvas.id = canvasId;
    canvas.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:1;pointer-events:none;display:block;opacity:0.72;';
    document.body.prepend(canvas);
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // 1. Try WebGL Renderer
  // ─────────────────────────────────────────────────────────────────────────────
  let gl = null;
  try {
    gl = canvas.getContext('webgl', { alpha: true, antialias: true, premultipliedAlpha: false }) ||
         canvas.getContext('experimental-webgl', { alpha: true, antialias: true });
  } catch (err) {
    console.warn('WebGL initialization error, falling back to 2D canvas:', err);
  }

  if (gl) {
    const webglCleanup = initWebGLShader(gl, canvas);
    if (webglCleanup) {
      console.info('Nimad Dashboard: Silver-White WebGL Shader active.');
      return webglCleanup;
    }
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // 2. High-Performance Canvas2D Fallback (Runs if WebGL is unavailable or fails)
  // ─────────────────────────────────────────────────────────────────────────────
  console.info('Nimad Dashboard: Starting Silver-White Canvas2D wave animation fallback.');
  return initCanvas2DFallback(canvas);
}

function initWebGLShader(gl, canvas) {
  const vsSource = `
    attribute vec2 aVertexPosition;
    void main() {
      gl_Position = vec4(aVertexPosition, 0.0, 1.0);
    }
  `;

  const fsSource = `
    #ifdef GL_FRAGMENT_PRECISION_HIGH
    precision highp float;
    #else
    precision mediump float;
    #endif

    uniform vec2 iResolution;
    uniform float iTime;

    const float overallSpeed = 0.24;
    const float gridSmoothWidth = 0.015;
    const float axisWidth = 0.045;
    const float majorLineWidth = 0.035;
    const float minorLineWidth = 0.018;
    const float majorLineFrequency = 4.0;
    const float minorLineFrequency = 1.0;
    const float scale = 3.6;

    const vec4 lineColor = vec4(0.97, 0.985, 1.0, 1.0);
    const vec4 glowColor = vec4(0.82, 0.88, 0.98, 1.0);
    const vec4 silverTone = vec4(0.65, 0.72, 0.85, 1.0);

    const float minLineWidth = 0.024;
    const float maxLineWidth = 0.32;
    const float lineSpeed = 1.0 * overallSpeed;
    const float lineAmplitude = 1.4;
    const float lineFrequency = 0.22;
    const float warpSpeed = 0.22 * overallSpeed;
    const float warpFrequency = 0.45;
    const float warpAmplitude = 1.15;
    const float offsetFrequency = 0.42;
    const float offsetSpeed = 1.25 * overallSpeed;
    const float minOffsetSpread = 0.85;
    const float maxOffsetSpread = 2.4;

    // Mathematically safe distance falloff (always edge0 < edge1)
    float drawCircle(vec2 pos, float radius, vec2 coord) {
      float d = length(coord - pos);
      return 1.0 - smoothstep(radius, radius + gridSmoothWidth, d);
    }

    float drawSmoothLine(float pos, float halfWidth, float t) {
      float d = abs(pos - t);
      return 1.0 - smoothstep(0.0, max(halfWidth, 0.002), d);
    }

    float drawCrispLine(float pos, float halfWidth, float t) {
      float d = abs(pos - t);
      return 1.0 - smoothstep(halfWidth, halfWidth + gridSmoothWidth, d);
    }

    float drawPeriodicLine(float freq, float width, float t) {
      return drawCrispLine(freq * 0.5, width, abs(mod(t, freq) - freq * 0.5));
    }

    float drawGridLines(float axis) {
      return drawCrispLine(0.0, axisWidth, axis)
            + drawPeriodicLine(majorLineFrequency, majorLineWidth, axis)
            + drawPeriodicLine(minorLineFrequency, minorLineWidth, axis);
    }

    float drawGrid(vec2 space) {
      return min(1.0, drawGridLines(space.x) + drawGridLines(space.y));
    }

    float random(float t) {
      return (cos(t) + cos(t * 1.3 + 1.3) + cos(t * 1.4 + 1.4)) / 3.0;
    }

    float getPlasmaY(float x, float horizontalFade, float offset) {
      return random(x * lineFrequency + iTime * lineSpeed) * horizontalFade * lineAmplitude + offset;
    }

    void main() {
      vec2 fragCoord = gl_FragCoord.xy;
      vec2 uv = fragCoord.xy / iResolution.xy;
      vec2 space = (fragCoord - iResolution.xy * 0.5) / iResolution.x * 2.0 * scale;

      // Ensure waves remain fully visible across both the top hero and lower screen
      float horizontalFade = clamp(0.45 + 0.55 * (1.0 - abs(uv.x - 0.5) * 1.3), 0.28, 1.0);
      float verticalFade = 0.65 + 0.35 * sin(uv.y * 3.14159);

      space.y += random(space.x * warpFrequency + iTime * warpSpeed) * warpAmplitude * (0.5 + horizontalFade);
      space.x += random(space.y * warpFrequency + iTime * warpSpeed + 2.0) * warpAmplitude * horizontalFade;

      vec4 lines = vec4(0.0);
      vec4 bgColor1 = vec4(0.015, 0.02, 0.03, 1.0);
      vec4 bgColor2 = vec4(0.03, 0.038, 0.055, 1.0);

      for (int l = 0; l < 16; l++) {
        float normalizedLineIndex = float(l) / 16.0;
        float offsetTime = iTime * offsetSpeed;
        float offsetPosition = float(l) + space.x * offsetFrequency;
        float rand = random(offsetPosition + offsetTime) * 0.5 + 0.5;
        float halfWidth = mix(minLineWidth, maxLineWidth, rand * horizontalFade) * 0.5;
        float offset = (float(l) - 7.5) * 0.22 + random(offsetPosition + offsetTime * (1.0 + normalizedLineIndex)) * mix(minOffsetSpread, maxOffsetSpread, horizontalFade) * 0.6;
        float linePosition = getPlasmaY(space.x, horizontalFade, offset);

        float smoothL = drawSmoothLine(linePosition, halfWidth, space.y);
        float crispL = drawCrispLine(linePosition, halfWidth * 0.22, space.y);
        float lineIntensity = smoothL * 0.8 + crispL * 1.5;

        // Floating silver particle nodes along the wave trajectories
        float circleX = mod(float(l) * 1.5 + iTime * lineSpeed * 2.8, 24.0) - 12.0;
        vec2 circlePosition = vec2(circleX, getPlasmaY(circleX, horizontalFade, offset));
        float circle = drawCircle(circlePosition, 0.022, space) * 3.8;

        lines += (lineIntensity * lineColor + crispL * glowColor * 0.75 + circle * lineColor) * (0.65 + 0.85 * rand);
      }

      float gridVal = drawGrid(space) * 0.06;

      vec4 baseBg = mix(bgColor1, bgColor2, uv.y) * verticalFade;
      baseBg.a = 1.0;

      // Soft ambient silver-metallic bloom
      vec4 ambientSilver = silverTone * 0.035 * verticalFade;

      gl_FragColor = baseBg + lines * 0.65 + ambientSilver + vec4(gridVal, gridVal, gridVal * 1.1, 0.0);
    }
  `;

  const loadShader = (type, source) => {
    const shader = gl.createShader(type);
    if (!shader) return null;
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      console.warn('WebGL shader compile error:', gl.getShaderInfoLog(shader));
      gl.deleteShader(shader);
      return null;
    }
    return shader;
  };

  const vertexShader = loadShader(gl.VERTEX_SHADER, vsSource);
  const fragmentShader = loadShader(gl.FRAGMENT_SHADER, fsSource);
  if (!vertexShader || !fragmentShader) return null;

  const shaderProgram = gl.createProgram();
  if (!shaderProgram) return null;
  gl.attachShader(shaderProgram, vertexShader);
  gl.attachShader(shaderProgram, fragmentShader);
  gl.linkProgram(shaderProgram);

  if (!gl.getProgramParameter(shaderProgram, gl.LINK_STATUS)) {
    console.warn('WebGL program link error:', gl.getProgramInfoLog(shaderProgram));
    return null;
  }

  const positionBuffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
  const positions = [
    -1.0, -1.0,
     1.0, -1.0,
    -1.0,  1.0,
     1.0,  1.0,
  ];
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(positions), gl.STATIC_DRAW);

  const programInfo = {
    program: shaderProgram,
    attribLocations: {
      vertexPosition: gl.getAttribLocation(shaderProgram, 'aVertexPosition'),
    },
    uniformLocations: {
      resolution: gl.getUniformLocation(shaderProgram, 'iResolution'),
      time: gl.getUniformLocation(shaderProgram, 'iTime'),
    },
  };

  let animationId;
  const startTime = Date.now();

  const resizeCanvas = () => {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.floor((window.innerWidth || 1920) * dpr);
    const h = Math.floor((window.innerHeight || 1080) * dpr);
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    gl.viewport(0, 0, canvas.width, canvas.height);
  };

  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  const render = () => {
    const currentTime = (Date.now() - startTime) / 1000;
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(0.01, 0.015, 0.02, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT);

    gl.useProgram(programInfo.program);
    gl.uniform2f(programInfo.uniformLocations.resolution, canvas.width, canvas.height);
    gl.uniform1f(programInfo.uniformLocations.time, currentTime);

    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.vertexAttribPointer(
      programInfo.attribLocations.vertexPosition,
      2,
      gl.FLOAT,
      false,
      0,
      0
    );
    gl.enableVertexAttribArray(programInfo.attribLocations.vertexPosition);

    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    animationId = requestAnimationFrame(render);
  };

  animationId = requestAnimationFrame(render);

  return () => {
    window.removeEventListener('resize', resizeCanvas);
    if (animationId) cancelAnimationFrame(animationId);
  };
}

/**
 * Robust 2D Canvas Fallback that renders an animated silver-white wavefield
 */
function initCanvas2DFallback(canvas) {
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  let animationId;
  let width = (canvas.width = window.innerWidth || 1920);
  let height = (canvas.height = window.innerHeight || 1080);

  const resize = () => {
    width = canvas.width = window.innerWidth || 1920;
    height = canvas.height = window.innerHeight || 1080;
  };
  window.addEventListener('resize', resize);

  const startTime = Date.now();

  const render2D = () => {
    const t = (Date.now() - startTime) * 0.001;

    // Background gradient with deep silver-slate base
    const bgGrad = ctx.createLinearGradient(0, 0, 0, height);
    bgGrad.addColorStop(0, '#020306');
    bgGrad.addColorStop(0.5, '#05070d');
    bgGrad.addColorStop(1, '#020306');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, width, height);

    // Subtle silver grid lines
    ctx.strokeStyle = 'rgba(180, 195, 220, 0.035)';
    ctx.lineWidth = 1;
    const gridSize = 80;
    for (let x = 0; x < width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y < height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // 12 silver-white undulating waves across the screen
    const waveCount = 12;
    for (let i = 0; i < waveCount; i++) {
      const progress = i / waveCount;
      const baseAlpha = 0.18 + 0.36 * Math.sin(progress * Math.PI);
      const yOffset = height * (0.2 + 0.6 * progress);

      ctx.beginPath();
      ctx.lineWidth = 1.2 + 1.8 * Math.sin(t * 0.5 + i);

      // Silver-white gradient for wave stroke
      const lineGrad = ctx.createLinearGradient(0, 0, width, 0);
      lineGrad.addColorStop(0, 'rgba(180, 195, 220, 0.0)');
      lineGrad.addColorStop(0.2, `rgba(220, 230, 245, ${baseAlpha * 0.6})`);
      lineGrad.addColorStop(0.5, `rgba(255, 255, 255, ${baseAlpha * 0.95})`);
      lineGrad.addColorStop(0.8, `rgba(200, 215, 235, ${baseAlpha * 0.6})`);
      lineGrad.addColorStop(1, 'rgba(180, 195, 220, 0.0)');
      ctx.strokeStyle = lineGrad;

      for (let x = 0; x <= width; x += 30) {
        const nx = x / width;
        const wave1 = Math.sin(nx * 4.5 + t * 0.6 + i * 0.45) * 55;
        const wave2 = Math.cos(nx * 7.5 - t * 0.4 + i * 0.8) * 35;
        const wave3 = Math.sin(nx * 12.0 + t * 0.8) * 15;
        const y = yOffset + wave1 + wave2 + wave3;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Glowing silver node traveling along wave
      const nodeX = ((t * 80 + i * 140) % (width + 200)) - 100;
      if (nodeX >= 0 && nodeX <= width) {
        const nx = nodeX / width;
        const nodeY = yOffset + Math.sin(nx * 4.5 + t * 0.6 + i * 0.45) * 55 + Math.cos(nx * 7.5 - t * 0.4 + i * 0.8) * 35;
        const rad = ctx.createRadialGradient(nodeX, nodeY, 0, nodeX, nodeY, 18);
        rad.addColorStop(0, 'rgba(255, 255, 255, 0.9)');
        rad.addColorStop(0.3, 'rgba(210, 225, 250, 0.5)');
        rad.addColorStop(1, 'rgba(180, 200, 230, 0.0)');
        ctx.fillStyle = rad;
        ctx.beginPath();
        ctx.arc(nodeX, nodeY, 18, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    animationId = requestAnimationFrame(render2D);
  };

  animationId = requestAnimationFrame(render2D);

  return () => {
    window.removeEventListener('resize', resize);
    if (animationId) cancelAnimationFrame(animationId);
  };
}
