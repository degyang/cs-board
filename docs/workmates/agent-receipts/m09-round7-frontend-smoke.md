# m09-round7: Frontend API/UI Smoke — infographic-remotion Engine

## 1. API Verification: `create_options()` in `csboard/application/commands.py:230-277`

**Verdict: PASS — infographic-remotion is correctly registered.**

The `create_options()` method always includes an `infographic-remotion` engine entry in its response. The logic:

1. **When `service_resolver` is available** (lines 238-256): It instantiates a `CapabilityService`, calls `snapshot()`, and looks for the item where `engine == "infographic-remotion"` and `visual_source == "preset"`. If found, it appends:
   ```python
   {
       "id": "infographic-remotion",
       "label": "动态信息图",
       "available": infographic_item["supported"],  # bool
       "reason": infographic_item.get("reason_code") or "能力未就绪",
   }
   ```

2. **When `service_resolver` is None** (lines 257-263): It appends a fallback entry with `available: False` and `reason: "CAPABILITY_NOT_AVAILABLE"`.

**Fields returned**: `id`, `label`, `available`, `reason` — all four required fields are present in both code paths.

### CapabilityService (`csboard/application/capabilities.py:92-159`)

The `snapshot()` method determines `infographic-remotion` availability by:
- Checking service requirements against `INFOGRAPHIC_STAGE_REQUIREMENTS` (same as whiteboard)
- Running `_detect_remotion_readiness()` which checks for: `node` binary, `video_renderer/render.mjs` script, and a headless browser (Chromium/Chrome/Edge)
- `supported = not infographic_missing and remotion_ready`
- Reason codes: `REMOTION_NOT_INSTALLED`, `NODE_NOT_FOUND`, `BROWSER_NOT_FOUND`, `RENDER_SCRIPT_MISSING`, `EXTERNAL_STAGE_GATE_REQUIRED`, or `CAPABILITY_NOT_AVAILABLE`

---

## 2. Frontend Verification: `web-v2/src/pages/CreateTaskPage.tsx`

**Verdict: PASS — UI correctly handles unavailable engines.**

### 2a. Engine Display (line 115)

The `engineDisplayOptions` array (line 88) merges static `PRODUCT_ENGINES` (which includes `{id: 'infographic-remotion', label: '动态信息图'}`) with the server response. When the server hasn't returned data yet, each product engine defaults to `{available: false, reason: '...'}` with contextual fallback reasons.

Each engine card (line 115):
- Gets the `unsupported` CSS class when `!item.available`
- Is disabled via `disabled={!item.available || submitting}`
- Shows a `<span className="status-pill limited">暂未开放</span>` badge
- Shows `<span className="option-reason">服务端：{item.reason || '能力未就绪'}</span>` — displays the API's `reason` field

### 2b. Preview Button for Unavailable Engines (line 115)

For `infographic-remotion` specifically, when unavailable, a "预览成片设置" button is rendered that navigates to the final tab in read-only preview mode. The final tab (line 129) shows a notice: "只读预览：动态信息图未被当前服务端开放，本页不会把它写入任务。"

### 2c. Submit Guard (line 89, `validate()` function)

The `validate()` function performs these checks:
- `if (!engine || !engine.available) errors.engine = engine?.reason || '该输出引擎当前不可用'` — blocks submission if selected engine is unavailable
- `if (!visual || !visual.available) errors.visualSource = visual?.reason || '该视觉来源当前不可用'` — blocks submission if selected visual source is unavailable
- The submit button (line 142) is also disabled when `!options.data` hasn't loaded

### 2d. Combination Availability (line 88, 122)

`combinationAvailable` is computed as `Boolean(selectedEngineOption?.available && selectedVisualOption?.available)`. When false, a warning notice on the visual tab shows the reason why the combination cannot be submitted.

---

## 3. Type Definitions (`web-v2/src/lib/api/types.ts:82-87`)

```typescript
export interface CreateOption {
  id: string
  label: string
  available: boolean
  reason?: string | null
}
```

The `reason` field is optional/nullable, matching the backend's behavior (only present when unavailable).

---

## Issues Found

**None.** The API correctly registers `infographic-remotion` with all required fields (`id`, `label`, `available`, `reason`), and the frontend correctly:
- Renders the engine card with disabled state and reason text when unavailable
- Blocks submission via `validate()` guard when an unavailable engine is selected
- Provides a read-only preview mode for the unavailable engine's settings
