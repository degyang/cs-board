import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {resolveBrowserExecutable} from './browser-resolver.mjs';

const executable = (target) => {
  fs.mkdirSync(path.dirname(target), {recursive: true});
  fs.writeFileSync(target, 'fixture');
  fs.chmodSync(target, 0o700);
};

test('configured Remotion browser wins', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'remotion-browser-'));
  const configured = path.join(root, 'configured-browser');
  executable(configured);
  assert.equal(resolveBrowserExecutable({environment: {REMOTION_BROWSER_EXECUTABLE: configured}, homeDirectory: root, platform: 'linux'}), configured);
});

test('latest Puppeteer headless shell is reused without configuration', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'remotion-browser-'));
  const older = path.join(root, '.cache/puppeteer/chrome-headless-shell/linux-120/chrome-headless-shell-linux64/chrome-headless-shell');
  const newer = path.join(root, '.cache/puppeteer/chrome-headless-shell/linux-152/chrome-headless-shell-linux64/chrome-headless-shell');
  executable(older);
  executable(newer);
  assert.equal(resolveBrowserExecutable({environment: {}, homeDirectory: root, platform: 'linux'}), newer);
});

test('missing configured and cached browsers return null', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'remotion-browser-'));
  assert.equal(resolveBrowserExecutable({environment: {}, homeDirectory: root, platform: 'test'}), null);
});
