import type {DynamicInfographicPropsV1} from '../types';

// TypeScript's JSON module inference deliberately widens literal strings and
// numbers, so this checked companion is the typed representation of the JSON
// golden fixture at tests/fixtures/infographic/dynamic-infographic-props-v1.json.
// This is an assignment (not a cast): `npm run build` rejects contract drift.
export const dynamicInfographicPropsV1Fixture: DynamicInfographicPropsV1 = {
  schemaVersion: 1,
  fps: 30,
  width: 1920,
  height: 1080,
  totalDurationMs: 1050,
  totalDurationFrames: 32,
  style: 'fixture',
  subtitlesEnabled: false,
  audioPaths: ['artifacts/audio/narration.wav'],
  pages: [{
    id: 'page-unit-001', image: 'artifacts/planning/illustrations/visual-001.png',
    startFrame: 0, endFrame: 32, seriesTitle: 'Fixture', chapterTitle: 'P1',
    pageTitle: 'Frame conversion', layoutType: 'focus', composition: 'split-right',
    slideRole: 'detail', relationshipType: 'none', coreIdea: 'ceil duration frame conversion',
    visualStrategy: 'one page per Voice Unit', narrativeLink: 'fixture', nodes: ['visual-001'],
    conclusion: 'done', seriesPersistent: false, chapterPersistent: false,
    cues: [{
      id: 'cue-visual-001', anchorText: 'fixture', startFrame: 0, endFrame: 30,
      spokenStartMs: 0, spokenEndMs: 1000, enterIds: ['visual-001'], focusId: 'visual-001',
      alignmentCoverage: 1, alignmentConfidence: 1,
    }],
  }],
};
