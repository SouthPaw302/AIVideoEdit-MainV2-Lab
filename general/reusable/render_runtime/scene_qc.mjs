#!/usr/bin/env node
/**
 * AIVideoEdit scene QC adapter.
 *
 * Runs the upstream structural/runtime/layout/motion/contrast checks and snapshot
 * capture behind an AIVideoEdit-native command. Existing production guards stay
 * authoritative; this is an additional pre-render quality gate.
 */
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import process from 'node:process';
import { assertRuntimeOptIn } from './runtime_opt_in.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const isWin = process.platform === 'win32';
const bin = resolve(here, 'node_modules', '.bin', isWin ? 'hyperframes.cmd' : 'hyperframes');

function die(msg) {
  console.error(`ERROR: ${msg}`);
  process.exit(2);
}

const argv = process.argv.slice(2);
if (!argv.length) die('usage: node scene_qc.mjs <composition-project-dir> [--no-snapshots] [--json]');
const project = resolve(argv[0]);
const snapshots = !argv.includes('--no-snapshots');
const json = argv.includes('--json');
if (!existsSync(project)) die(`project does not exist: ${project}`);

let projectRoot;
try {
  projectRoot = assertRuntimeOptIn(project);
} catch (err) {
  die(err.message);
}

if (!existsSync(bin)) die(`runtime dependencies are not installed. Run npm install in ${here}`);

const args = ['check', project];
if (snapshots) args.push('--snapshots');
const started = Date.now();
const run = spawnSync(bin, args, {
  cwd: project,
  encoding: 'utf8',
  env: { ...process.env, CI: process.env.CI ?? '1' },
});
const summary = {
  schema: 'aivideoedit.scene-qc-result.v1',
  project_root: projectRoot,
  project,
  passed: run.status === 0,
  exit_code: run.status ?? 1,
  snapshots_requested: snapshots,
  elapsed_sec: Math.round((Date.now() - started) / 10) / 100,
  stdout: run.stdout ?? '',
  stderr: run.stderr ?? '',
};
if (json) {
  console.log(JSON.stringify(summary, null, 2));
} else {
  if (summary.stdout) process.stdout.write(summary.stdout);
  if (summary.stderr) process.stderr.write(summary.stderr);
  console.log(`\nAIVideoEdit scene QC: ${summary.passed ? 'PASS' : 'FAIL'}`);
}
process.exit(summary.passed ? 0 : 1);
