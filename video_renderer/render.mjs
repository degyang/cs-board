import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import {resolveBrowserExecutable} from './browser-resolver.mjs';

const [propsPath, outputPath, publicDir] = process.argv.slice(2);
if (!propsPath || !outputPath || !publicDir) {
  throw new Error('用法：node render.mjs <props.json> <output.mp4> <job-public-dir>');
}

const rendererRoot = path.dirname(new URL(import.meta.url).pathname.replace(/^\/(.:)/, '$1'));
const inputProps = JSON.parse(fs.readFileSync(propsPath, 'utf8'));
const browserExecutable = resolveBrowserExecutable();

const serveUrl = await bundle({
  entryPoint: path.join(rendererRoot, 'src', 'index.tsx'),
  rootDir: rendererRoot,
  publicDir: path.resolve(publicDir),
  webpackOverride: (configuration) => configuration,
});
const rendererOptions = browserExecutable ? {browserExecutable} : {};
const composition = await selectComposition({
  serveUrl,
  id: 'DynamicInfographic',
  inputProps,
  logLevel: 'warn',
  timeoutInMilliseconds: 120000,
  ...rendererOptions,
});
await renderMedia({
  serveUrl,
  composition,
  inputProps,
  codec: 'h264',
  outputLocation: path.resolve(outputPath),
  muted: true,
  crf: 19,
  pixelFormat: 'yuv420p',
  x264Preset: 'medium',
  concurrency: '50%',
  overwrite: true,
  logLevel: 'warn',
  timeoutInMilliseconds: 120000,
  ...rendererOptions,
});
