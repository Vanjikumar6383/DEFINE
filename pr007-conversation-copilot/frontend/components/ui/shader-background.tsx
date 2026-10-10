import React, { useEffect, useRef } from 'react';

const ShaderBackground = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Vertex shader source code
  const vsSource = `
    attribute vec4 aVertexPosition;
    void main() {
      gl_Position = aVertexPosition;
    }
  `;

  // Fragment shader source code
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

      float horizontalFade = clamp(0.45 + 0.55 * (1.0 - abs(uv.x - 0.5) * 1.3), 0.28, 1.0);
      float verticalFade = 0.65 + 0.35 * sin(uv.y * 3.14159);

      space.y += random(space.x * warpFrequency + iTime * warpSpeed) * warpAmplitude * (0.5 + horizontalFade);
      space.x += random(space.y * warpFrequency + iTime * warpSpeed + 2.0) * warpAmplitude * horizontalFade;

      vec4 lines = vec4(0.0);
      vec4 bgColor1 = vec4(0.015, 0.02, 0.03, 1.0);
      vec4 bgColor2 = vec4(0.03, 0.038, 0.055, 1.0);

      for(int l = 0; l < 16; l++) {
        float normalizedLineIndex = float(l) / 16.0;
        float offsetTime = iTime * offsetSpeed;
        float offsetPosition = float(l) + space.x * offsetFrequency;
        float rand = random(offsetPosition + offsetTime) * 0.5 + 0.5;
        float halfWidth = mix(minLineWidth, maxLineWidth, rand * horizontalFade) * 0.5;
        float offset = (float(l) - 7.5) * 0.22 + random(offsetPosition + offsetTime * (1.0 + normalizedLineIndex)) * mix(minOffsetSpread, maxOffsetSpread, horizontalFade) * 0.6;
        float linePosition = getPlasmaY(space.x, horizontalFade, offset);

        float smoothL = drawSmoothLine(linePosition, halfWidth, space.y);
        float crispL = drawCrispLine(linePosition, halfWidth * 0.22, space.y);
        float line = smoothL * 0.8 + crispL * 1.5;

        float circleX = mod(float(l) * 1.5 + iTime * lineSpeed * 2.8, 24.0) - 12.0;
        vec2 circlePosition = vec2(circleX, getPlasmaY(circleX, horizontalFade, offset));
        float circle = drawCircle(circlePosition, 0.022, space) * 3.8;

        lines += (line * lineColor + crispL * glowColor * 0.75 + circle * lineColor) * (0.65 + 0.85 * rand);
      }

      float gridVal = drawGrid(space) * 0.06;
      vec4 baseBg = mix(bgColor1, bgColor2, uv.y) * verticalFade;
      baseBg.a = 1.0;

      gl_FragColor = baseBg + lines * 0.65 + vec4(gridVal, gridVal, gridVal * 1.1, 0.0);
    }
  `;

  // Helper function to compile shader
  const loadShader = (gl: WebGLRenderingContext, type: number, source: string) => {
    const shader = gl.createShader(type);
    if (!shader) return null;
    gl.shaderSource(shader, source);
    gl.compileShader(shader);

    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      console.error('Shader compile error: ', gl.getShaderInfoLog(shader));
      gl.deleteShader(shader);
      return null;
    }

    return shader;
  };

  // Initialize shader program
  const initShaderProgram = (gl: WebGLRenderingContext, vsSource: string, fsSource: string) => {
    const vertexShader = loadShader(gl, gl.VERTEX_SHADER, vsSource);
    const fragmentShader = loadShader(gl, gl.FRAGMENT_SHADER, fsSource);
    if (!vertexShader || !fragmentShader) return null;

    const shaderProgram = gl.createProgram();
    if (!shaderProgram) return null;
    gl.attachShader(shaderProgram, vertexShader);
    gl.attachShader(shaderProgram, fragmentShader);
    gl.linkProgram(shaderProgram);

    if (!gl.getProgramParameter(shaderProgram, gl.LINK_STATUS)) {
      console.error('Shader program link error: ', gl.getProgramInfoLog(shaderProgram));
      return null;
    }

    return shaderProgram;
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const gl = canvas.getContext('webgl');
    if (!gl) {
      console.warn('WebGL not supported.');
      return;
    }

    const shaderProgram = initShaderProgram(gl, vsSource, fsSource);
    if (!shaderProgram) return;

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

    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      gl.viewport(0, 0, canvas.width, canvas.height);
    };

    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    let startTime = Date.now();
    let animationFrameId: number;

    const render = () => {
      const currentTime = (Date.now() - startTime) / 1000;

      gl.clearColor(0.0, 0.0, 0.0, 1.0);
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
      animationFrameId = requestAnimationFrame(render);
    };

    animationFrameId = requestAnimationFrame(render);

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <canvas ref={canvasRef} className="fixed top-0 left-0 w-full h-full -z-10" />
  );
};

export default ShaderBackground;
