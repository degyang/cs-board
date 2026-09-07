import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const isExecutableFile = (candidate) => {
  if (!candidate) return false;
  try {
    fs.accessSync(candidate, fs.constants.R_OK | fs.constants.X_OK);
    return fs.statSync(candidate).isFile();
  } catch {
    return false;
  }
};

const versionedCandidates = (directory, suffix) => {
  try {
    return fs.readdirSync(directory, {withFileTypes: true})
      .filter((entry) => entry.isDirectory())
      .map((entry) => path.join(directory, entry.name, ...suffix))
      .sort((left, right) => right.localeCompare(left, undefined, {numeric: true}));
  } catch {
    return [];
  }
};

/** Resolve an already-installed Chromium without triggering a network download. */
export const resolveBrowserExecutable = ({
  environment = process.env,
  homeDirectory = os.homedir(),
  platform = process.platform,
} = {}) => {
  const configured = [
    environment.REMOTION_BROWSER_EXECUTABLE,
    environment.PUPPETEER_EXECUTABLE_PATH,
    environment.CHROME_PATH,
  ];

  const platformCandidates = platform === 'win32' ? [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  ] : [
    '/usr/bin/google-chrome-stable',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ];

  const cachedCandidates = platform === 'linux' ? [
    ...versionedCandidates(path.join(homeDirectory, '.cache/puppeteer/chrome-headless-shell'), ['chrome-headless-shell-linux64', 'chrome-headless-shell']),
    ...versionedCandidates(path.join(homeDirectory, '.cache/puppeteer/chrome'), ['chrome-linux64', 'chrome']),
    ...versionedCandidates(path.join(homeDirectory, '.cache/ms-playwright'), ['chrome-headless-shell-linux64', 'chrome-headless-shell']),
    ...versionedCandidates(path.join(homeDirectory, '.cache/ms-playwright'), ['chrome-linux64', 'chrome']),
  ] : [];

  return [...configured, ...platformCandidates, ...cachedCandidates].find(isExecutableFile) ?? null;
};
