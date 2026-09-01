# CCF-CREATE-TASK-13 (§3Q): Core Task Input Persistence Report

**Instruction**: CCF-CREATE-TASK-13 — "CCF 新建任务核心输入真实保存"  
**Branch**: `feat/mountain-assets-settings-web`  
**Implementation commit**: `7510dd9` — `feat(mountain-web): persist core task inputs`  
**Report commit**: `docs(mountain): report core task input persistence`  
**File**: `web-v2/src/pages/CreateTaskPage.tsx`

---

## 1 Two-Step Request Sequence

The CreateTaskPage implements a real two-step save via the Mountain API client:

### Step 1: Create Task

```
POST /api/v1/tasks
Content-Type: application/json

{
  "title": "用户输入的标题",
  "engine": "whiteboard",
  "pipeline_id": "mountain-av-v1"
}
```

- `createTask(req)` calls `post('/tasks', req)` → `request()` sets `Content-Type: application/json`, body = JSON string.
- On `!res.ok`: parses `body.detail` as `ApiError`, throws `MountainApiError(status, apiError, apiError?.message ?? 'API error: ${status}')`.
- On success: receives `{ task_id, run_id }` — stored in `createdTask` state.

### Step 2: Upload Inputs (multipart)

```
POST /api/v1/tasks/{task_id}/inputs
(no manual Content-Type — browser sets multipart/form-data boundary)

FormData:
  script                    — full script text
  reference                 — File object (optional)
  style                     — "极简粗线简笔白板风" (fixed)
  pen_text                  — "" (fixed)
  stroke_detail             — "detailed" (fixed)
  include_subtitles         — "true" (stringified boolean)
  target_chars              — "80" (default)
  min_chars                 — "35" (default)
  max_chars                 — "140" (default)
  visual_anchor_enabled     — "true" (stringified boolean)
```

- `uploadInputs(taskId, form)` calls `postForm('/tasks/${encodeURIComponent(taskId)}/inputs', form)` → fetch `{ method: 'POST', body: form }`, no `Content-Type` header (browser sets multipart boundary automatically).
- On success: navigates to `/tasks/${encodeURIComponent(task_id)}`.
- On failure: sets `uploadErr` with safe error text (see §6).

### Request Evidence

Test: "saves title+script+whiteboard config then navigates" — `fetchMock.mock.calls` verified:
- Call 0: URL endsWith `/tasks`, `opts.headers['Content-Type'] === 'application/json'`, `JSON.parse(opts.body)` matches `{ title, engine: 'whiteboard', pipeline_id: 'mountain-av-v1' }`.
- Call 1: URL endsWith `/tasks/${encodeURIComponent(taskId)}/inputs`, `opts.body instanceof FormData`, `opts.headers` is undefined (no manual Content-Type). `FormData.get(...)` assertions verified for all 10 fields.

---

## 2 FormData Field Mapping

| FormData field | Source | Value | Backend type |
|---|---|---|---|
| `script` | textarea (trimmed) | user input | `Form(...)` min 10 chars |
| `reference` | file input (`accept="audio/*,.wav,.mp3,.m4a,.ogg,.flac"`) | `File` object or null | `File(...)` optional |
| `style` | constant | `"极简粗线简笔白板风"` | `Form("极简粗线简笔白板风")` |
| `pen_text` | constant | `""` | `Form("")` trunc 12 |
| `stroke_detail` | constant | `"detailed"` | `Form("detailed")` ∈ {light,standard,detailed,full} |
| `include_subtitles` | checkbox (default true) | `"true"` / `"false"` | `Form(True)` |
| `target_chars` | number input (default "80") | `"80"` (stringified) | `Form(80)` |
| `min_chars` | number input (default "35") | `"35"` (stringified) | `Form(35)` |
| `max_chars` | number input (default "140") | `"140"` (stringified) | `Form(140)` |
| `visual_anchor_enabled` | checkbox (default true) | `"true"` / `"false"` | `Form(True)` |

Boolean and integer fields are converted to strings via `String(value)` before `form.set()`.

---

## 3 Validation Matrix

| Rule | Condition | Error message |
|---|---|---|
| Title required | `title.trim() === ''` | "请输入任务名称" |
| Script required | `script.trim() === ''` | "请输入文案" |
| Chars: integer | `parseIntField` returns null (non-finite, non-integer) | "字数必须为整数" |
| Chars: bounds | any value < 1 or > 500 | "字数范围超出合理界限" |
| Chars: ordering | not (1 ≤ min ≤ target ≤ max ≤ 500) | "需满足 1 ≤ 最小 ≤ 目标 ≤ 最大 ≤ 500" |

`parseIntField(t)` returns `null` on empty string, `NaN`, `Infinity`, or non-integer — fields default to empty string, so empty = skipped from ordering check (treated as "unset").

---

## 4 Partial-Failure State Machine

```
[idle] --submit--> [creating]
  | on create success: createdTask = { task_id, run_id }
  | on create fail: set createErr, reset submitting → [idle]
  v
[uploading] --upload--> [done] (navigate to workbench)
  | on upload fail: set uploadErr, keep createdTask → [partial-fail]
  v
[partial-fail]
  | "重试保存输入" → handleRetryUpload() → runUpload(createdTask.task_id)
  |   (NO re-create, only uploadInputs called)
  | "进入任务工作台" → enterWorkbench() → navigate /tasks/{task_id}
  | title field DISABLED (prevent re-create by design)
```

Key guarantees:
- `createdTask` state preserved on upload failure — `task_id`/`run_id` never lost.
- `handleSubmit`: `if (createdTask) return runUpload(createdTask.task_id)` — safety net prevents duplicate Task creation.
- `handleRetryUpload`: validates, then calls `runUpload(createdTask.task_id)` — only `uploadInputs`, never `createTask`.
- `submittingRef` dedup guard prevents concurrent submissions.
- `mountedRef` (set false in cleanup effect) prevents state updates after unmount.

### Partial-Failure Evidence

Test: "keeps task_id on upload failure then retries only upload" — after upload 400:
- "任务已创建、输入保存失败" + "代码：UPLOAD_FAILED" present.
- `createCalls === 1`, `uploadCalls === 1`.
- No navigation, title disabled, "创建任务" gone, "重试保存输入" + "进入任务工作台" present.
- Retry: click "重试保存输入", mock upload → 200, `createCalls` stays 1, `uploadCalls` = 2, navigation occurs.

---

## 5 Reference Audio Security Boundary

The browser must never read, print, cache, or base64-encode the reference audio file content.

- File input: `accept="audio/*,.wav,.mp3,.m4a,.ogg,.flac"`.
- `form.set('reference', file)` — the raw `File` object is passed directly to `FormData`. No `FileReader`, no `readAsDataURL`, no `readAsArrayBuffer`, no `URL.createObjectURL`.
- UI hint: "浏览器不会读取、打印、缓存或 base64 化音频内容".
- Gate scan: `FileReader|readAsDataURL` = 0 matches on `CreateTaskPage.tsx` + `create-task.test.tsx`.

---

## 6 Error Security

`safeErrorText(err)` duck-types on `'apiError' in err`:

```typescript
function safeErrorText(err: unknown): { message: string; code?: string } {
  const isApi = err !== null && typeof err === 'object' && 'apiError' in err;
  if (isApi) {
    const e = err as { apiError?: { code?: string; message?: string } };
    return { message: e.apiError?.message ?? '上传失败', code: e.apiError?.code };
  }
  return { message: '网络错误，请稍后重试' };
}
```

Only `message` and `code` from `MountainApiError.apiError` are rendered. The error response's `details` object (which may contain `path`, `command`, `token`, `secret`, `traceback`, `reference`) is never rendered.

Test evidence: upload 400 with `{detail: {code:'SENSITIVE', message:'安全错误信息', details: {path:'/etc/secret/key', command:'rm -rf /', token:'sk-live-secret-token', secret:'topsecret-value', traceback:'Traceback...', reference:'audio-bytes'}}}` — "安全错误信息" + "代码：SENSITIVE" present; all 6 sensitive strings (`path`, `command`, `token`, `secret`, `traceback`, `reference`) are `queryByText(null)`.

---

## 7 Execution Strategy Scope

Per §3Q.2, the following are explicitly NOT implemented:

| Item | Status | Rationale |
|---|---|---|
| 动态信息图 (infographic-remotion) | Not implemented | Out of scope — `queryByText(/动态信息图/)` returns null in tests |
| 资产选择 (asset selection) | Not implemented | Out of scope |
| Manual/gated execution strategy | Not implemented | Out of scope — `queryByText(/manual\|gated/i)` returns null in tests |
| Auto-start Run | Not implemented | Out of scope — create+upload only, no Run trigger |
| Browser-local authority splitting | Not implemented | Out of scope |

The UI shows fixed hints: "引擎：白板动画（固定）" and "标准白板配置：style=极简粗线简笔白板风 / stroke_detail=detailed".

---

## 8 Backend First-Save-Requires-Reference Constraint

The backend (`POST /tasks/{task_id}/inputs`) enforces: if no `reference` file is provided AND no prior reference exists for the task, returns HTTP 400 "首次保存必须提供参考音频".

This is a real backend constraint, not a frontend gap. The partial-failure state machine handles it gracefully: create succeeds → upload 400 → "任务已创建、输入保存失败" + error message → user adds reference file → "重试保存输入" re-calls only `uploadInputs`.

---

## 9 Pipeline ID Justification

`pipeline_id: 'mountain-av-v1'` is passed to `createTask()` because the backend validates:
- Rejects `pipeline_id` not matching the expected value (400).
- The pipeline defines which processing stages run on the task.

The value is a fixed constant in `CreateTaskPage.tsx`, not user-editable.

---

## 10 Gate Evidence

### Build

```
$ npm run build (tsc --noEmit + vite build)
✓ 68 modules transformed.
✓ built in 932ms
```

Clean, zero errors.

### Tests (create-task.test.tsx in isolation)

```
$ npx vitest run tests/create-task.test.tsx
✓ tests/create-task.test.tsx (17 tests) 273ms
Test Files  1 passed (1)
     Tests  17 passed (17)
```

17/17 pass, 0 warnings.

### Warning Scan

```
OK: 0 warnings in create-task log
```

Scanned for: `not wrapped in act`, `console.error`, `react state update on an unmounted`, `warning:`, `⚠`, `deprecat`.

### Forbidden-Pattern Scan

```
OK: 0 forbidden-pattern matches
```

Scanned `CreateTaskPage.tsx` + `create-task.test.tsx` for: `localStorage|sessionStorage|FileReader|readAsDataURL|infographic-remotion|execution_strategy.*manual|policy.*gated`.

### Contract Checker

```
$ npm run test:contract-checker
✓ tests/checker-behavior.test.ts (33 tests) 47ms
✓ tests/contract-checker-exec.test.ts (15 tests) 285ms
Test Files  2 passed (2)
     Tests  48 passed (48)
```

48/48 pass.

### git diff --name-only 0638567..HEAD

```
web-v2/src/pages/CreateTaskPage.tsx
web-v2/src/styles/app.css
web-v2/tests/create-task.test.tsx
```

Both required files present: `CreateTaskPage.tsx` + `create-task.test.tsx`.

### git status

```
(empty — all changes committed)
```

### Pre-Existing Test Suite Failures (not caused by this change)

The full `npx vitest run` shows 10 test files failing (assets-contract.test.tsx, contract.test.tsx, and others). These failures are **pre-existing**: reverting the 3 changed files to the pre-commit state (0638567) and re-running the full suite produces the same 10 failing test files with the same failure pattern. The failing test files do not import `CreateTaskPage.tsx` or `app.css`; the failure mode is global-test-pollution (test isolation issue where `assets-contract.test.tsx` and `contract.test.tsx` fail in full-suite but pass individually). This change does not introduce or modify any of these failures.

---

## 11 Test Coverage Summary

| Describe block | Tests | What's verified |
|---|---|---|
| Form rendering | 2 | All fields present; engine hint; cancel link; no forbidden patterns in UI |
| Validation | 5 | Empty title; empty script; non-integer chars; bounds; ordering |
| Two-step save | 3 | With reference → 2 calls + navigate; without reference → form.get('reference') null; create failure → error + no upload |
| Partial failure & retry | 3 | Upload fail → error + buttons; retry → only upload; enter workbench → navigate |
| Concurrency & unmount | 3 | Loading state + disabled; double-submit → 1 call; unmount → no console errors |
| Error security | 1 | Sensitive fields (path/command/token/secret/traceback/reference) never rendered |
