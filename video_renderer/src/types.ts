export type LayoutType =
  | 'overview'
  | 'question'
  | 'principle'
  | 'evidence'
  | 'case'
  | 'path'
  | 'flow'
  | 'comparison'
  | 'layers'
  | 'cause'
  | 'cycle'
  | 'timeline'
  | 'focus'
  | 'summary';

export type CompositionType =
  | 'split-right'
  | 'split-left'
  | 'center-stage'
  | 'top-bottom'
  | 'full-width';

export type TimedCue = {
  id: string;
  anchorText: string;
  startFrame: number;
  endFrame: number;
  spokenStartMs: number;
  spokenEndMs: number;
  enterIds: string[];
  focusId: string;
  alignmentCoverage: number;
  alignmentConfidence: number;
};

export type InfographicPage = {
  id: string;
  image: string;
  startFrame: number;
  endFrame: number;
  seriesTitle: string;
  chapterTitle: string;
  pageTitle: string;
  layoutType: LayoutType;
  composition: CompositionType;
  slideRole: 'overview' | 'detail' | 'transition' | 'summary';
  relationshipType: 'none' | 'sequence' | 'cause' | 'comparison' | 'hierarchy';
  coreIdea: string;
  visualStrategy: string;
  narrativeLink: string;
  nodes: string[];
  conclusion: string;
  cues: TimedCue[];
  seriesPersistent: boolean;
  chapterPersistent: boolean;
};

/**
 * P1 portable renderer input. All artifact references are run-relative POSIX
 * paths (never absolute paths, URLs with credentials, or provider data).
 * Frame spans are zero-based, start-inclusive and end-exclusive; total frame
 * count is ceil(totalDurationMs * fps / 1000).
 */
export type DynamicInfographicPropsV1 = {
  schemaVersion: 1;
  fps: number;
  width: number;
  height: number;
  totalDurationMs: number;
  totalDurationFrames: number;
  style: string;
  subtitlesEnabled?: boolean;
  /** Run-relative public asset paths only. */
  audioPaths?: string[];
  pages: InfographicPage[];
};

/**
 * Existing composition input retains an optional version only for the checked-in
 * local default props. New adapters and task packages must emit the strict V1
 * type above; P1 does not change the renderer implementation.
 */
export type InfographicVideoProps = Omit<DynamicInfographicPropsV1, 'schemaVersion'> & {
  schemaVersion?: 1;
};

/** P1 task-package render-manifest contract; never contains an absolute path. */
export type RenderManifestV1 = {
  schema_version: 1;
  engine: 'infographic-remotion';
  output_relative_path: string;
  output_sha256: string;
  size_bytes: number;
  duration_ms: number;
  frames: number;
  probe_sha256: string;
};

/** Hash-only, UTC evidence consumed by post-smoke activation. */
export type RemotionEvidenceV1 = {
  schema_version: 1;
  verified_at: string;
  renderer_sha256: string;
  lockfile_sha256: string;
  props_sha256: string;
  tool_versions: Record<string, string>;
  service_probe_sha256: string;
  artifact_index_sha256: string;
  render_manifest_sha256: string;
  mp4_sha256: string;
};
