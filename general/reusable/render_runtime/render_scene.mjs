#!/usr/bin/env node
/**
 * AIVideoEdit deterministic scene renderer.
 *
 * User/agent-facing name and contract are AIVideoEdit-native. The underlying
 * rendering package is an implementation dependency and may be swapped later.
 */
import { mkdirSync, statSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import process from 'node:process';
import { createRenderJob, executeRenderJob } from 'aivideoedit-render-core';
import { assertRuntimeOptIn } from './runtime_opt_in.mjs';

function usage(msg) {
  if (msg) console.error(`ERROR: ${msg}`);
  console.error(`Usage:
  node render_scene.mjs <composition.html> <output> [options]

Options:
  --width N             default 1920
  --height N            default 1080
  --fps 24|30|60        default 30
  --quality draft|standard|high
  --format mp4|webm|mov|gif|png-sequence|hls
  --transparent         choose mov unless --format is given
  --video-frame-format auto|jpg|png
  --json                progress/result as JSON lines
`);
  process.exit(2);
}

function parse(argv) {
  if (argv.length < 2) usage();
  const out = {
    inputPath: resolve(argv[0]),
    outputPath: resolve(argv[1]),
    width: 1920,
    height: 1080,
    fps: 30,
    quality: 'standard',
    format: null,
    videoFrameFormat: 'auto',
    transparent: false,
    json: false,
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    const need = () => argv[++i] ?? usage(`missing value for ${a}`);
    if (a === '--width') out.width = Number(need());
    else if (a === '--height') out.height = Number(need());
    else if (a === '--fps') out.fps = Number(need());
    else if (a === '--quality') out.quality = need();
    else if (a === '--format') out.format = need();
    else if (a === '--video-frame-format') out.videoFrameFormat = need();
    else if (a === '--transparent') out.transparent = true;
    else if (a === '--json') out.json = true;
    else usage(`unknown option: ${a}`);
  }
  if (![24, 30, 60].includes(out.fps)) usage('--fps must be 24, 30, or 60');
  if (!['draft', 'standard', 'high'].includes(out.quality)) usage('invalid --quality');
  if (!['auto', 'jpg', 'png'].includes(out.videoFrameFormat)) usage('invalid --video-frame-format');
  const allowed = ['mp4', 'webm', 'mov', 'gif', 'png-sequence', 'hls'];
  if (out.format && !allowed.includes(out.format)) usage('invalid --format');
  if (out.transparent && !out.format) out.format = 'mov';
  if (!out.format) out.format = 'mp4';
  if (out.transparent && !['webm', 'mov', 'png-sequence'].includes(out.format)) {
    usage('--transparent requires webm, mov, or png-sequence');
  }
  return out;
}

const cfg = parse(process.argv.slice(2));
try {
  if (!statSync(cfg.inputPath).isFile()) usage('composition input is not a file');
} catch {
  usage(`composition not found: ${cfg.inputPath}`);
}

let projectRoot;
try {
  projectRoot = assertRuntimeOptIn(cfg.inputPath);
} catch (err) {
  usage(err.message);
}

mkdirSync(cfg.format === 'png-sequence' || cfg.format === 'hls' ? cfg.outputPath : dirname(cfg.outputPath), { recursive: true });

const renderConfig = {
  inputPath: cfg.inputPath,
  outputPath: cfg.outputPath,
  width: cfg.width,
  height: cfg.height,
  fps: cfg.fps,
  quality: cfg.quality,
  format: cfg.format,
  videoFrameFormat: cfg.videoFrameFormat,
};

const job = createRenderJob(renderConfig);
const started = Date.now();
let lastBucket = -1;
const result = await executeRenderJob(job, (p) => {
  const percent = Math.max(0, Math.min(100, Math.round((p.percent ?? 0) * 100)));
  const bucket = Math.floor(percent / 5);
  if (bucket === lastBucket) return;
  lastBucket = bucket;
  if (cfg.json) console.log(JSON.stringify({ type: 'progress', percent }));
  else process.stderr.write(`render ${percent}%\n`);
});

const summary = {
  schema: 'aivideoedit.render-result.v1',
  project_root: projectRoot,
  input: cfg.inputPath,
  output: result.outputPath ?? cfg.outputPath,
  format: cfg.format,
  fps: cfg.fps,
  dimensions: [cfg.width, cfg.height],
  elapsed_sec: Math.round((Date.now() - started) / 10) / 100,
};
console.log(cfg.json ? JSON.stringify({ type: 'result', ...summary }) : JSON.stringify(summary, null, 2));
