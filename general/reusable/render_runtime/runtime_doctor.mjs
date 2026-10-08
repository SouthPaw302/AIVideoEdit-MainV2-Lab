#!/usr/bin/env node
import { accessSync, constants } from 'node:fs';
import { execFileSync } from 'node:child_process';
import process from 'node:process';

function cmd(name, args = ['--version']) {
  try {
    return execFileSync(name, args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  } catch {
    return null;
  }
}

const major = Number(process.versions.node.split('.')[0]);
const ffmpeg = cmd('ffmpeg', ['-version']);
const ffprobe = cmd('ffprobe', ['-version']);
let renderCore = false;
let renderCli = false;
let transitionCore = false;
for (const [key, path] of [
  ['renderCore', './node_modules/aivideoedit-render-core/package.json'],
  ['renderCli', './node_modules/aivideoedit-render-cli/package.json'],
  ['transitionCore', './node_modules/aivideoedit-transition-core/package.json'],
]) {
  try {
    accessSync(new URL(path, import.meta.url), constants.R_OK);
    if (key === 'renderCore') renderCore = true;
    if (key === 'renderCli') renderCli = true;
    if (key === 'transitionCore') transitionCore = true;
  } catch {}
}

const result = {
  schema: 'aivideoedit.scene-runtime-doctor.v1',
  node: process.version,
  node_ok: major >= 22,
  ffmpeg_ok: Boolean(ffmpeg),
  ffprobe_ok: Boolean(ffprobe),
  dependencies: {
    render_core: renderCore,
    render_cli: renderCli,
    transition_core: transitionCore,
  },
  ready: major >= 22 && Boolean(ffmpeg) && Boolean(ffprobe) && renderCore && renderCli && transitionCore,
};
console.log(JSON.stringify(result, null, 2));
process.exit(result.ready ? 0 : 2);
