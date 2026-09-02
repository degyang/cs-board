# CCF 浏览器证据端口恢复指令

状态：`CORRECTION REQUIRED`  
拒绝报告：`0224bb3`  
前置实现：`387013d`  
本轮仅恢复证据运行，不修改产品代码。

## 1. PM核查事实

- 六张`create-*.png`仍为0，PNG总数仍为15；
- 当前复查时5175、5180、8000均无监听进程，`ss/lsof/pgrep`无占用者；
- 因此不再要求使用5175，直接使用新的严格端口5275；
- Vite代理配置固定指向后端8000，前端监听端口改变不影响`/api`代理；
- 可用Chromium仍为`/home/ubuntu/.cache/ms-playwright/chromium-1187/chrome-linux/chrome`。

## 2. 唯一执行步骤

在当前CCF工作树新开终端执行。必须使用`trap`保证失败也清理本轮精确进程和临时目录：

```bash
set -euo pipefail
CCF_DATA="$(mktemp -d)"
CCF_BACK_LOG="$(mktemp)"
CCF_WEB_LOG="$(mktemp)"
CCF_BACK_PID=""
CCF_WEB_PID=""

cleanup() {
  if [ -n "$CCF_WEB_PID" ] && kill -0 "$CCF_WEB_PID" 2>/dev/null; then kill "$CCF_WEB_PID"; fi
  if [ -n "$CCF_BACK_PID" ] && kill -0 "$CCF_BACK_PID" 2>/dev/null; then kill "$CCF_BACK_PID"; fi
  if [ -n "$CCF_WEB_PID" ]; then wait "$CCF_WEB_PID" 2>/dev/null || true; fi
  if [ -n "$CCF_BACK_PID" ]; then wait "$CCF_BACK_PID" 2>/dev/null || true; fi
  rm -rf -- "$CCF_DATA"
  rm -f -- "$CCF_BACK_LOG" "$CCF_WEB_LOG"
}
trap cleanup EXIT

/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/run_mountain_backend.py \
  --host 127.0.0.1 --port 8000 --data-dir "$CCF_DATA" \
  >"$CCF_BACK_LOG" 2>&1 &
CCF_BACK_PID=$!

npm --prefix web-v2 run dev -- --host 127.0.0.1 --port 5275 --strictPort \
  >"$CCF_WEB_LOG" 2>&1 &
CCF_WEB_PID=$!

ready=0
for attempt in $(seq 1 80); do
  if curl --noproxy '*' -fsS http://127.0.0.1:8000/api/v1/health >/dev/null \
    && curl --noproxy '*' -fsS http://127.0.0.1:5275/ >/dev/null; then
    ready=1
    break
  fi
  if ! kill -0 "$CCF_BACK_PID" 2>/dev/null || ! kill -0 "$CCF_WEB_PID" 2>/dev/null; then break; fi
  sleep 0.5
done

if [ "$ready" -ne 1 ]; then
  echo '=== backend log ==='
  sed -n '1,200p' "$CCF_BACK_LOG"
  echo '=== web log ==='
  sed -n '1,200p' "$CCF_WEB_LOG"
  echo '=== listeners ==='
  ss -ltnp | rg ':(8000|5275)\b' || true
  exit 1
fi

MOUNTAIN_API_BASE=http://127.0.0.1:8000 node web-v2/scripts/check-api-contract.mjs

PLAYWRIGHT_CHROMIUM_EXECUTABLE=/home/ubuntu/.cache/ms-playwright/chromium-1187/chrome-linux/chrome \
WEBUI_BASE=http://127.0.0.1:5275 \
MOUNTAIN_API_BASE=http://127.0.0.1:8000 \
  node web-v2/scripts/capture-parity-evidence.mjs

test "$(find docs/Mountain/webui-parity-evidence/tasks -maxdepth 1 -name 'create-*.png' -type f -size +0c | wc -l)" -eq 6
sha256sum docs/Mountain/webui-parity-evidence/tasks/create-*.png
```

不得回退到5180，不得写第三份失败报告后停止。若5275启动失败，必须在回报中附上以上自动打印的完整backend/web日志和listener证据；没有日志的“端口占用”不成立。

## 3. 完成条件

- 脚本报告21张截图；
- console error/warning=0，failed API=0；
- 六张create图存在且人工检查有效；
- README记录5275仅为证据监听端口，不改变产品默认端口；
- `npm --prefix web-v2 run build`通过；
- `npm --prefix web-v2 test -- --run`保持338 passed；
- cleanup trap后8000/5275无本轮进程；
- 临时目录和日志已删除；
- 工作树clean。

提交：

```text
docs(mountain): complete create task browser evidence
```

更新21号执行文档最终报告和evidence README，推送分支后申请复审，不自行宣布通过。
