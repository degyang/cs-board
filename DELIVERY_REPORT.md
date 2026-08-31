# Mountain WebUI Assets & Settings Foundation — Delivery Report

## 1. Files Created/Modified

### New Files Created:
- `src/lib/api/http.ts` — Base HTTP client with error handling
- `src/lib/api/assets.ts` — Asset management API (preset styles, custom styles, voice library)
- `src/lib/api/services.ts` — Dynamic service management API
- `src/lib/api/settings.ts` — Settings API (runtime, voice alignment, toolchain, storage, diagnostics)
- `src/lib/api/tasks.ts` — Task lifecycle API (refactored from client.ts)
- `src/pages/AssetManagementPage.tsx` — Asset management with 3 tabs
- `src/pages/SettingsPage.tsx` — Settings with 5 tabs (models, voice-alignment, toolchain, storage, diagnostics)
- `src/pages/ServiceDetailPage.tsx` — Service detail view with config editing and secret management
- `src/__tests__/assets-settings.test.ts` — 43 tests covering all 16 requirements

### Modified Files:
- `src/app/router.tsx` — Added routes for `/assets`, `/settings`, `/settings/models/:serviceId`
- `src/components/layout/Sidebar.tsx` — Added "素材管理" navigation item, updated imports
- `src/lib/api/types.ts` — Added new types for assets, services, settings; updated STAGE_NAMES
- `tests/contract.test.tsx` — Updated stage name from "生成画面锚定重点" to "文案整理与画面锚定重点"

## 2. API Module Structure

The API client has been split into modular files:

```
src/lib/api/
├── http.ts          — Base HTTP utilities (MountainApiError, request, get, post, patch, put, del, postForm)
├── types.ts         — All TypeScript DTOs (original + new)
├── tasks.ts         — Task lifecycle endpoints
├── assets.ts        — Asset management endpoints
├── services.ts      — Dynamic service management endpoints
└── settings.ts      — Settings endpoints
```

## 3. New Pages Created

### AssetManagementPage (`/assets`)
- Three tabs: 预设风格 (read-only), 自定义风格 (CRUD), 声音库 (CRUD)
- Search and filter for preset styles
- Create/delete forms for custom styles and voice assets
- File upload support (FormData)

### SettingsPage (`/settings`)
- Five tabs: 模型服务, 声音对齐, 工具链, 存储, 诊断
- Dynamic service list grouped by capability
- Service toggle and set-default functionality
- Links to service detail pages

### ServiceDetailPage (`/settings/models/:serviceId`)
- Service status display (config_status, availability, secret_status)
- JSON config editor with save functionality
- Secret management (add/delete with password inputs)
- Back navigation to settings page

## 4. Router Updates

Added routes:
- `/assets` → AssetManagementPage
- `/settings` → SettingsPage
- `/settings/models/:serviceId` → ServiceDetailPage

Preserved existing routes:
- `/` → TasksPage
- `/tasks/new` → CreateTaskPage
- `/tasks/:taskId` → TaskWorkbenchPage
- `/tasks/:taskId/runs/:runId/diagnostics` → RunDiagnosticsPage
- `/help` → HelpPage

## 5. Sidebar Updates

Added "素材管理" navigation group with:
- 素材管理 (AssetManagementPage) — with image icon

Updated imports to use new API modules.

## 6. Test Coverage

43 tests covering all 16 requirements:

1. **Task routes not falling back to Project** — 3 tests
2. **Stage keys not regressing** — 3 tests (including first stage "文案整理与画面锚定重点")
3. **Asset tabs display** — 1 test
4. **CRUD contracts** — 4 tests (assets, services, settings, tasks APIs)
5. **FormData upload** — 2 tests
6. **Secret security** — 3 tests
7. **Error states** — 3 tests
8. **No localStorage** — 2 tests
9. **Route switching isolation** — 5 tests
10. **Dynamic service concept** — 3 tests
11. **Type definitions** — 4 tests
12. **CSS naming namespaces** — 4 tests
13. **No emoji icons** — 1 test
14. **No window.alert** — 1 test
15. **No inferring provider availability** — 2 tests
16. **No fixed provider lists** — 2 tests

## 7. Build/Test Results

### npm ci
✅ Successful (29 packages installed)

### npm run build
✅ Successful
- TypeScript compilation: ✓
- Vite build: ✓
- Output: 270.51 kB (83.36 kB gzipped)

### npm test
✅ All 163 tests passed (7 test files)
- tests/http-contract.test.ts: 33 tests ✓
- tests/api-client.test.ts: 7 tests ✓
- src/__tests__/assets-settings.test.ts: 43 tests ✓
- tests/providers-page.test.tsx: 16 tests ✓
- tests/create-task.test.tsx: 6 tests ✓
- tests/contract.test.tsx: 50 tests ✓
- tests/provider-detail.test.tsx: 8 tests ✓

## 8. Static Analysis Results

### git diff --check
✅ No whitespace errors

### Forbidden Pattern Checks
✅ No localStorage for business data (only UI state in AppShell)
✅ No window.alert (only in test assertions)
✅ No emoji icons (only in test assertions)
✅ No mock/fixture data
✅ No project.save, project.run.start, /create, /projects, CreateProjectPage, ProjectsPage, ProjectWorkbenchPage, project_id (only in test assertions)
✅ No split, 文案分割 (only in test assertions)

## 9. Commit Message

```
feat(mountain-web): implement assets and settings foundation
```

## 10. Summary

This PR implements the foundation for asset management and settings pages in the Mountain WebUI:

- **Asset Management**: Three-tab interface for preset styles (read-only), custom styles (CRUD), and voice library (CRUD) with file upload support
- **Settings**: Five-tab interface for dynamic service management, voice alignment status, toolchain status, storage status, and diagnostics
- **Dynamic Services**: Replaced fixed provider concept with dynamic service list grouped by capability
- **API Modularization**: Split monolithic client.ts into modular files (http, tasks, assets, services, settings)
- **Type Safety**: Added comprehensive TypeScript types for all new features while preserving backward compatibility
- **Test Coverage**: 43 new tests covering all 16 specified requirements
- **Stage Names**: Updated first stage to "文案整理与画面锚定重点" as required

All delivery gates passed:
- ✅ npm ci
- ✅ npm run build
- ✅ npm test (163 tests passed)
- ✅ git diff --check
- ✅ Static analysis (no forbidden patterns)

The implementation follows all specified requirements:
- Uses Task terminology (not Project)
- Uses correct stage names
- No localStorage for business data
- No emoji icons
- No window.alert
- No fixed provider lists
- Proper error handling
- CSS naming namespaces (am-*, set-*, va-*, mp-*)
