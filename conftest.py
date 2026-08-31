"""Root conftest — 设置测试环境变量。"""

import os

# 测试环境允许明文 secret（cryptography 可能未安装）
os.environ.setdefault("CSBOARD_ALLOW_PLAINTEXT_SECRETS", "1")
