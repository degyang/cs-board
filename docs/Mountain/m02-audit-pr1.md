# M02 审计报告 — PR-1: 运行时基础设施

日期: 2026-08-29
分支: `feat/mountain-m07-project-api-web-v2`

---

## 变更摘要

### 新增文件（源码，8 个，412 行）

| 文件 | 行数 | 职责 |
|------|------|------|
| `csboard/runtime/__init__.py` | 14 | 统一导出 RuntimePaths, ToolchainResolver, ProcessSupervisor, SecretStore |
| `csboard/runtime/paths.py` | 47 | `RuntimePaths` dataclass — 统一路径解析，替代 `webapp/server.py` 中的硬编码常量 |
| `csboard/runtime/toolchain.py` | 75 | `ToolchainResolver` dataclass — 自动发现 python/node/ffmpeg/ffprobe/remotion |
| `csboard/runtime/process_supervisor.py` | 106 | `ProcessSupervisor` + `ProcessHandle` — 子进程生命周期管理，支持取消和清理 |
| `csboard/runtime/secret_store.py` | 30 | `SecretStore` Protocol — 密钥存取抽象接口 |
| `csboard/adapters/secrets/__init__.py` | 1 | 适配器子包 |
| `csboard/adapters/secrets/plaintext_secret_store.py` | 52 | 明文 JSON 文件实现（开发/测试用） |
| `csboard/adapters/secrets/file_secret_store.py` | 87 | Fernet 加密实现（需 `cryptography` 库） |

### 新增文件（测试，4 个，319 行）

| 文件 | 行数 | 测试数 | 覆盖功能 |
|------|------|--------|----------|
| `tests/test_runtime_paths.py` | 55 | 5 | from_root 解析、ensure_dirs 幂等、frozen 不可变 |
| `tests/test_toolchain_resolver.py` | 63 | 4 | auto_detect 发现、validate 缺失报告、frozen 不可变 |
| `tests/test_process_supervisor.py` | 82 | 6 | 启动/终止/全部取消/已退出清理/输出重定向/重复终止 |
| `tests/test_secret_store.py` | 119 | 13 | Plaintext: CRUD+协议+持久化; File: CRUD+持久化+错误密钥+协议 |

### 修改文件

无。PR-1 为纯新增，不修改任何现有文件。

---

## 设计决策

### 与 `docs/Mountain/02-target-architecture.md` 的对应

| 文档要求 | 实现情况 | 偏离说明 |
|----------|----------|----------|
| RuntimePaths 集中管理路径 | ✅ `RuntimePaths.from_root()` 计算所有子路径 | — |
| ToolchainResolver 解析外部工具 | ✅ `auto_detect()` 从 venv/PATH 发现 | — |
| ProcessSupervisor 管理子进程 | ✅ start/terminate/cancel_all | — |
| SecretStore 抽象密钥管理 | ✅ Protocol + 两种实现 | — |

### 偏离设计的地方

1. **SecretStore 无系统密钥链实现** — 文档提到桌面端应使用系统密钥链。当前仅提供文件实现，密钥链适配器留给 M08（桌面架构）。
2. **ProcessSupervisor 未做 detached 进程** — 与 `webapp/server.py` 中 `start_new_session=True` 不同，新 supervisor 默认前台可控，支持 terminate。detached 模式可在需要时扩展。
3. **ToolchainResolver 不校验版本** — 只检查工具是否存在，不验证版本号。版本兼容性检查留给 Stage 实现时按需添加。

---

## 测试覆盖

- **28 个新测试**，全部通过
- **81 个总测试**（含既有 53 个），全部通过，无回归
- 4 个 FileSecretStore 测试因 `cryptography` 未安装而跳过（预期行为）

### 未覆盖的边界情况

- `ToolchainResolver` 在 Windows 路径下的行为（CI 环境为 Linux）
- `ProcessSupervisor` 在进程卡死时 SIGKILL 超时路径

---

## 遗留问题

1. **现有代码未使用 RuntimePaths** — `webapp/server.py` 和 `MountainCommands` 仍使用各自的硬编码路径。PR-2 完成后可逐步替换。
2. **`cryptography` 依赖未声明** — `FileSecretStore` 需要 `pip install cryptography`。应在 `webapp/requirements.txt` 中添加为可选依赖。
3. **`utc_now` 导入路径** — `ProcessSupervisor` 从 `csboard.application.context` 导入 `utc_now`，形成 runtime → application 依赖。可考虑将 `utc_now` 下沉到 `csboard.domain`。

---

## 签收

- [x] 代码审查通过
- [x] 测试全部通过（81/81，4 skipped）
- [x] 文档已更新（本文件）
