#!/usr/bin/env node
import { existsSync, readFileSync, statSync } from 'node:fs';
import { dirname, parse, resolve } from 'node:path';

export const RUNTIME_ID = 'browser_scene_runtime';

function startingDirectory(subjectPath) {
  const resolved = resolve(subjectPath);
  if (!existsSync(resolved)) return resolved;
  try {
    return statSync(resolved).isDirectory() ? resolved : dirname(resolved);
  } catch {
    return dirname(resolved);
  }
}

export function findProjectRoot(subjectPath) {
  let current = startingDirectory(subjectPath);
  const root = parse(current).root;
  while (true) {
    if (existsSync(resolve(current, 'OPERATING_ORDER.json'))) return current;
    if (current === root) return null;
    const parent = dirname(current);
    if (parent === current) return null;
    current = parent;
  }
}

export function readRuntimeOptIns(projectRoot) {
  const orderPath = resolve(projectRoot, 'OPERATING_ORDER.json');
  let order;
  try {
    order = JSON.parse(readFileSync(orderPath, 'utf8'));
  } catch (err) {
    throw new Error(`cannot read valid OPERATING_ORDER.json at ${orderPath}: ${err.message}`);
  }
  const runtimes = order.optional_runtimes ?? [];
  if (!Array.isArray(runtimes) || runtimes.some((x) => typeof x !== 'string' || !x.trim())) {
    throw new Error('OPERATING_ORDER.optional_runtimes must be an array of non-empty runtime ids');
  }
  return runtimes;
}

export function assertRuntimeOptIn(subjectPath, runtimeId = RUNTIME_ID) {
  const projectRoot = findProjectRoot(subjectPath);
  if (!projectRoot) {
    throw new Error(
      `browser scene runtime refused: no OPERATING_ORDER.json found above ${resolve(subjectPath)}; ` +
      `boot the production from current main and use the normal AIVideoEdit workflow`
    );
  }
  const runtimes = readRuntimeOptIns(projectRoot);
  if (!runtimes.includes(runtimeId)) {
    throw new Error(
      `browser scene runtime refused: ${runtimeId} is not explicitly enabled in ` +
      `${resolve(projectRoot, 'OPERATING_ORDER.json')}. Add ` +
      `"optional_runtimes": ["${runtimeId}"] only when the resolved project workflow intentionally needs it.`
    );
  }
  return projectRoot;
}
