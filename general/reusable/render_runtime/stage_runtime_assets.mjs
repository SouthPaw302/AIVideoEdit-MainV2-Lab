#!/usr/bin/env node
import { copyFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import process from 'node:process';
import { assertRuntimeOptIn } from './runtime_opt_in.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const target = resolve(process.argv[2] ?? '.');

let projectRoot;
try {
  projectRoot = assertRuntimeOptIn(target);
} catch (err) {
  console.error(`ERROR: ${err.message}`);
  process.exit(2);
}

const vendor = resolve(target, 'vendor');
mkdirSync(vendor, { recursive: true });

const assets = [
  {
    src: resolve(here, 'node_modules', 'gsap', 'dist', 'gsap.min.js'),
    dst: resolve(vendor, 'aivideoedit-gsap.min.js'),
  },
  {
    src: resolve(here, 'node_modules', 'aivideoedit-transition-core', 'dist', 'index.global.js'),
    dst: resolve(vendor, 'aivideoedit-transition-core.js'),
  },
  {
    src: resolve(here, 'transition_bridge.js'),
    dst: resolve(vendor, 'aivideoedit-transitions.js'),
  },
  {
    src: resolve(here, 'audio_mix_bridge.js'),
    dst: resolve(vendor, 'aivideoedit-audio-mix.js'),
  },
];

for (const item of assets) {
  if (!existsSync(item.src)) {
    console.error(`Missing runtime dependency: ${item.src}`);
    console.error(`Run npm install in ${here} before staging browser assets.`);
    process.exit(2);
  }
  copyFileSync(item.src, item.dst);
}

console.log(JSON.stringify({
  schema: 'aivideoedit.runtime-assets.v1',
  project_root: projectRoot,
  target: vendor,
  files: assets.map((x) => x.dst),
}, null, 2));
