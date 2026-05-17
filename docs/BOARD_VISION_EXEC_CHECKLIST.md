# 开发板视觉链路 · 最小执行清单

**固定策略**：`VISION_PROVIDER=ascend`，`SPEECH_PROVIDER=local`。  
**占位符**：将 `BOARD_IP` 换成开发板局域网 IP（例：`192.168.1.100`）。  
**目录**：`ASCEND_SERVICE_ROOT` = 含 `ascend_service/` 的父目录（例：`/opt/dajian-ai-coach` 或本机仓库 `dajian-ai-coach`）。

---

## A. 开发板执行

### A1. 环境可跑 Python

```bash
python3 --version
cd "$ASCEND_SERVICE_ROOT" && test -f ascend_service/app.py && echo ok
```

| 预期 | 失败先查 |
|------|----------|
| Python 3 有版本输出；最后一行 `ok` | 路径是否含 `ascend_service/app.py`；是否拷全仓库父目录 |

---

### A2. 虚拟环境与依赖（仅首次或变更后）

```bash
cd "$ASCEND_SERVICE_ROOT"
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r ascend_service/requirements.txt
python3 -c "import mediapipe, cv2; print('deps_ok')"
```

| 预期日志 | 失败先查 |
|----------|----------|
| `deps_ok` | `pip` 报错；ARM 无 wheel → 换厂商源/预编译包；缺系统库按报错补 |

---

### A3. 启动 ascend_service

```bash
cd "$ASCEND_SERVICE_ROOT"
export ASCEND_SERVICE_ROOT="$PWD"
export ASCEND_HOST=0.0.0.0
export ASCEND_PORT=18081
chmod +x scripts/board_start_vision_service.sh
./scripts/board_start_vision_service.sh
```

| 预期日志 | 失败先查 |
|----------|----------|
| `[board_start_vision_service] listening http://0.0.0.0:18081`；随后 uvicorn `Application startup complete` | 端口占用：`ss -tlnp \| grep 18081`；路径错误见 A1 |

**另开终端**（仍在开发板）：

```bash
curl -sS http://127.0.0.1:18081/health
```

| 预期 | 失败先查 |
|------|----------|
| JSON 含 `"status":"ok"`、`"vision_analyze":"/vision/analyze"` | A3 是否真在跑；防火墙 |

---

## B. PC 后端执行

### B1. 配置环境变量并启动

```bash
# 在 PC，进入仓库 backend 目录前设置（Linux/macOS 示例）
export ASCEND_BASE_URL=http://BOARD_IP:18081
export VISION_PROVIDER=ascend
export SPEECH_PROVIDER=local
cd /path/to/dajian-ai-coach/backend
uvicorn app:app --host 0.0.0.0 --port 8000
```

*或*：将 `backend/.env.board.vision.example` 复制为 `backend/.env`，改 `ASCEND_BASE_URL` 后同上启动（`config.py` 会读 `.env`）。

| 预期日志 | 失败先查 |
|----------|----------|
| 启动无 Import 错；可选看到 `[provider.factory] VISION_PROVIDER resolved: kind='ascend'`（首次走视觉时） | `.env` 是否在 `backend/`；变量是否被 shell 覆盖 |

---

### B2. 探测板子与配置

```bash
curl -sS http://127.0.0.1:8000/api/system/provider-status
```

| 预期（JSON） | 失败先查 |
|--------------|----------|
| `vision_provider`=`ascend`，`speech_provider`=`local`，`ascend_health_check.reachable`=`true`，`system_health_hint`=`ok` | PC 能否 `curl http://BOARD_IP:18081/health`；`ASCEND_BASE_URL` 是否无尾斜杠、IP 是否正确 |

---

## C. PC 前端执行

### C1. 启动

```bash
cd /path/to/dajian-ai-coach/frontend
npm install
npm run dev
```

| 预期日志 | 失败先查 |
|----------|----------|
| `Local: http://localhost:5173/` | Node/npm；端口占用 |

---

### C2. 训练页自检（浏览器）

打开 `http://localhost:5173` → 登录 → **训练** → 看「训练前准备检查」。

| 预期 | 失败先查 |
|------|----------|
| 「画面分析」**通过**；文案含开发板仪态/画面分析 | 浏览器 F12 → Network：`/api/system/provider-status` 是否 200；再看 B2 |

---

### C3. 端到端（短视频）

完成一次短录像并结束训练 → 打开**结果页**。

| 预期 | 失败先查 |
|------|----------|
| PC 后端终端：`[ascend.trace] vision BEGIN` … `success=true`（或明确超时/错误） | `ASCEND_VISION_TIMEOUT_SECONDS`；板子负载 |
| 开发板终端：`[ascend_service.api.vision]`、`SUMMARY` | A3 是否掉线；B1 URL 是否指错板 |

---

## 比赛前 5 分钟自检清单

按顺序打勾；任一项失败先修再演示。

1. **[开发板]** `curl -sS http://127.0.0.1:18081/health | head -c 200` → 含 `"status":"ok"`。
2. **[PC]** `curl -sS http://BOARD_IP:18081/health | head -c 200` → 同上（证明 PC 到板网络通）。
3. **[PC 后端已起]** `curl -sS http://127.0.0.1:8000/api/system/provider-status` → `reachable:true`，`system_health_hint:ok`，`vision_provider:ascend`，`speech_provider:local`。
4. **[PC 前端已起]** 浏览器能打开训练页；「画面分析」为通过。
5. **[可选 30s]** 录 10～15 秒结束训练，结果页能打开；板子日志出现一行 `[ascend_service.api.vision]`。

**备用**：PC 后端日志搜 `[ascend.trace]`；板子日志搜 `ascend_service.api.vision`。
