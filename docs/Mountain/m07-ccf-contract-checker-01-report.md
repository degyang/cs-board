# CCF-CONTRACT-CHECKER-01 门禁执行报告

**指令**: §3E — CCF 单一垂直切片：可执行 Contract Checker
**implementation commit**: `44ee044`
**branch**: `feat/mountain-assets-settings-web`
**worktree**: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web`

## §3E.4 门禁执行结果

### Gate 1: `npm run build`

```
✓ built in 892ms
```

退出码: 0

### Gate 2: `npm run test:contract-checker`

```
 Test Files  2 passed (2)
      Tests  44 passed (44)
```

退出码: 0

### Gate 3: `npm test -- --run`

```
 Test Files  12 passed (12)
      Tests  251 passed (251)
```

退出码: 0，0 warning，0 unhandled rejection。

### Gate 4: `node scripts/check-api-contract.mjs`

```
⚠ MOUNTAIN_API_BASE not set — falling back to fixture comparison only
  NOTE: This is fixture mode, NOT real API verification.

All fixture contracts aligned (fixture mode — not real API) ✓
```

退出码: 0。Fixture mode 明确声明不是真实 API。

### Gate 5: `git diff --check`

```
(clean)
```

退出码: 0。

## 专项测试场景

### 成功场景

| 测试名 | 描述 |
|--------|------|
| `checkRealBackend returns zero violations for valid responses` | 完整成功场景，所有 endpoint 返回合法 DTO |

### 失败场景

| 测试名 | 描述 |
|--------|------|
| `sends GET for service detail` | 验证 checker 对 detail 使用 GET |
| `sends GET for service secrets` | 验证 checker 对 secrets 使用 GET |
| `sends POST for service probe` | 验证 checker 对 probe 使用 POST |
| `detects missing required fields in ServiceAvailability` | 缺必填字段检测 |
| `detects unknown fields in ServiceDefinition` | 未知字段拒绝 |
| `passes when optional ApiError fields are missing` | 缺可选字段允许 |
| `detects wrong type in top-level field` | boolean/string 类型错误 |
| `detects wrong type in nested field` | config_status.configured 类型错误 |
| `detects wrong type in array element` | items[0].secret_key 类型错误 |
| `fails when no service ID and list is empty` | 空 Registry 失败 |
| `fails when server is unreachable` | 网络错误失败 |
| `fails when 404 has no JSON body` | 非 JSON 404 失败 |
| `validates error body on 404 without injecting status` | 404 status 作为元数据 |

### 行为测试（直接 import 生产核心）

| 测试名 | 描述 |
|--------|------|
| `extractInterfaceFields` (5 cases) | 字段提取、必填/可选区分 |
| `verifyFieldsBidirectional` (4 cases) | 双向验证 |
| `validateJsonType` (10 cases) | string/number/boolean/null/array/Record/元素类型 |
| `verifyResponse` (8 cases) | 完整响应验证含嵌套和数组 |
| `fixture alignment via checkFixtures` (1 case) | 13 fixture 对齐 |

## git status

```
(clean)
```

## 声明

门禁已执行。最终通过由审核者判定。
