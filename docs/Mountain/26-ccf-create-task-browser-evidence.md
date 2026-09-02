# CCF 新建任务浏览器证据最终指令

指令：`CCF-CREATE-TASK-EVIDENCE-FINAL`  
状态：仅补证据，不修改产品功能  
工作树：`/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-webui-surface-parity`  
分支：`feat/mountain-webui-surface-parity`  
已验收实现：`387013d`  
已验收报告：`e6f7f27`

## 1. 当前结论

代码纠偏、338个前端测试和真实contract checker已经报告通过；唯一未关闭门禁是六张新建任务截图及其真实浏览器零错误证据。

环境中已有可用Chromium，不需要下载：

```text
/home/ubuntu/.cache/ms-playwright/chromium-1187/chrome-linux/chrome
```

该文件已验证可执行，版本为Chromium 140，动态库无`not found`。

## 2. 唯一工作范围

- 不修改`CreateTaskPage.tsx`、CSS、API client或测试；
- 不创建Task，不填写用户真实文案，不上传音频；
- 只启动隔离后端和5175前端，运行现有截图脚本；
- 生成六张`create-*.png`，更新evidence README和纠偏报告；
- 如脚本断言失败，只允许修复截图脚本中与真实DOM/等待条件直接相关的问题，不得放宽或删除断言。

## 3. 精确执行步骤

在CCF工作树执行：

```bash
set -euo pipefail
CCF_EVIDENCE_DATA="$(mktemp -d)"
CCF_BACKEND_LOG="$(mktemp)"
CCF_WEB_LOG="$(mktemp)"

/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/run_mountain_backend.py \
  --host 127.0.0.1 --port 8000 --data-dir "$CCF_EVIDENCE_DATA" \
  >"$CCF_BACKEND_LOG" 2>&1 &
CCF_BACKEND_PID=$!

npm --prefix web-v2 run dev -- --host 127.0.0.1 --port 5175 --strictPort \
  >"$CCF_WEB_LOG" 2>&1 &
CCF_WEB_PID=$!

for attempt in $(seq 1 60); do
  curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null \
    && curl -fsS http://127.0.0.1:5175/ >/dev/null \
    && break
  if ! kill -0 "$CCF_BACKEND_PID" 2>/dev/null; then
    sed -n '1,160p' "$CCF_BACKEND_LOG"
    exit 1
  fi
  if ! kill -0 "$CCF_WEB_PID" 2>/dev/null; then
    sed -n '1,160p' "$CCF_WEB_LOG"
    exit 1
  fi
  sleep 0.5
done

curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null
curl -fsS http://127.0.0.1:5175/ >/dev/null

MOUNTAIN_API_BASE=http://127.0.0.1:8000 \
  node web-v2/scripts/check-api-contract.mjs

PLAYWRIGHT_CHROMIUM_EXECUTABLE=/home/ubuntu/.cache/ms-playwright/chromium-1187/chrome-linux/chrome \
WEBUI_BASE=http://127.0.0.1:5175 \
MOUNTAIN_API_BASE=http://127.0.0.1:8000 \
  node web-v2/scripts/capture-parity-evidence.mjs

kill "$CCF_WEB_PID" "$CCF_BACKEND_PID"
wait "$CCF_WEB_PID" 2>/dev/null || true
wait "$CCF_BACKEND_PID" 2>/dev/null || true
rm -rf -- "$CCF_EVIDENCE_DATA"
rm -f -- "$CCF_BACKEND_LOG" "$CCF_WEB_LOG"
```

如果中途失败，仍只终止以上两个精确PID并删除以上三个精确临时路径；禁止`pkill`或终止其他会话服务。

## 4. 证据检查

必须存在且非零：

```text
docs/Mountain/webui-parity-evidence/tasks/create-intro.png
docs/Mountain/webui-parity-evidence/tasks/create-script.png
docs/Mountain/webui-parity-evidence/tasks/create-voice.png
docs/Mountain/webui-parity-evidence/tasks/create-visual.png
docs/Mountain/webui-parity-evidence/tasks/create-final.png
docs/Mountain/webui-parity-evidence/tasks/create-validation.png
```

人工检查：六图均为1440×900且不是404/loading/error/空白；分别显示任务介绍、文案与三字数规则、reference与真实音色状态、真实风格状态、成片设置、字段错误与正确Tab。页面不得出现真实Secret、用户文案或音频内容。

```bash
sha256sum docs/Mountain/webui-parity-evidence/tasks/create-*.png
```

更新`docs/Mountain/webui-parity-evidence/README.md`：真实时间、前后端commit、21张截图、console error/warning=0、failed API=0，以及六张hash。

## 5. 最终门禁

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 test -- --run
test "$(find docs/Mountain/webui-parity-evidence/tasks -maxdepth 1 -name 'create-*.png' -type f -size +0c | wc -l)" -eq 6
git diff --check origin/integration/mountain-v2...HEAD
! rg -n 'Project|project_id|/projects' web-v2/src
git status --short
```

## 6. 提交与报告

证据和报告提交：

```text
docs(mountain): close create task browser evidence
```

在`docs/Mountain/21-create-task-surface-parity-execution.md`末尾追加最终证据报告，记录真实截图命令、21张结果、六张hash、零错误、进程/临时目录清理和clean status。推送当前分支后申请PM复审，不自行宣布通过。
