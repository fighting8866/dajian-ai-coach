# 开发板视觉链路部署与比赛演示 · V1

**范围**：仅 **视觉上板**（`VISION_PROVIDER=ascend`），**语音仍在 PC**（`SPEECH_PROVIDER=local`）。前端与主后端在 PC；开发板只跑 `ascend_service`。不修改训练主流程、不重构项目。

**交叉引用**：

- 最小验收清单：`docs/BOARD_VISION_SMOKE_TEST.md`
- PC 环境变量示例：`backend/.env.board.vision.example`
- 板侧启动脚本：`scripts/board_start_vision_service.sh`

---

## 仓库内关键事实（便于核对）

| 项 | 位置 |
|----|------|
| 板侧进程入口 | `python -m uvicorn ascend_service.app:app`（包名 `ascend_service`，工作目录须为 **含 `ascend_service/` 子目录的父目录**） |
| 板侧健康检查 | `GET /health` → `ascend_service/api/health.py` |
| 板侧视觉分析 | `POST /vision/analyze`（multipart：`video_file`、`request_id`）→ `ascend_service/api/vision.py` |
| PC 主后端配置 | `backend/config.py`（`ASCEND_BASE_URL`、`VISION_PROVIDER`、`SPEECH_PROVIDER`、超时与端点） |
| PC 探测板子 | `GET /api/system/provider-status` → `backend/api/system.py`（会请求 `{ASCEND_BASE_URL}/health`） |
| PC 视觉转发 | `VISION_PROVIDER=ascend` 时 `AscendVisionAIProvider` + `AscendHttpGateway` → 板侧 `/vision/analyze` |

**第一轮不做**：`SPEECH_PROVIDER=ascend`（语音不上板）。

---

## 网络拓扑（比赛演示）

```text
浏览器 (PC) → Vite :5173 → 代理 /api → 主后端 :8000
主后端 (PC) ──HTTP──→ 开发板 :18081 (ascend_service)
```

- 将下文 **`BOARD_IP`** 换成开发板在局域网中的 IP（如 `192.168.1.100`）。
- **PC 必须能访问** `http://BOARD_IP:18081/health`。

---

## 可执行顺序（与 `BOARD_VISION_SMOKE_TEST.md` 一致）

### 1. 开发板环境检查（在开发板执行）

```bash
uname -a
python3 --version
python3 -c "import sys; print(sys.executable)"
command -v curl || true
command -v ffprobe || echo "ffprobe 未安装（部分视频时长探测可能降级，可先忽略）"
```

**成功判定**：`python3` 可用（建议 3.10+）；能 `curl` 更佳。

---

### 2. 代码上传与依赖安装（在开发板执行）

将仓库中 **`dajian-ai-coach` 整包**或至少以下目录拷到板子，例如：

```text
/opt/dajian-ai-coach/
  ascend_service/
    app.py
    api/
    services/
    schemas/
    requirements.txt
  scripts/
```

**必须**：`ascend_service` 的 **父目录**为工作目录根（与 `import ascend_service` 一致）。

```bash
export ASCEND_SERVICE_ROOT=/opt/dajian-ai-coach
cd "$ASCEND_SERVICE_ROOT"
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r ascend_service/requirements.txt
```

**成功判定**：`pip install` 无致命错误；可执行：

```bash
python3 -c "import fastapi, cv2, numpy; print('core ok')"
python3 -c "import mediapipe; print('mediapipe ok')"
```

> **注意**：ARM/昇腾上 `mediapipe` / `opencv-python` 可能没有官方 wheel，需按板卡厂商镜像或预编译包处理；装不上则视觉链路无法在本仓库代码路径上跑通（见文末「最小缺口」）。

---

### 3. 开发板启动 ascend_service（在开发板执行）

```bash
cd /opt/dajian-ai-coach   # 与 ASCEND_SERVICE_ROOT 一致
chmod +x scripts/board_start_vision_service.sh
export ASCEND_SERVICE_ROOT=/opt/dajian-ai-coach
export ASCEND_HOST=0.0.0.0
export ASCEND_PORT=18081
./scripts/board_start_vision_service.sh
```

**成功判定**（另开 SSH 终端，仍在开发板）：

```bash
curl -sS http://127.0.0.1:18081/health
```

响应 JSON 中含 `"status":"ok"`、`"service":"ascend-service"`，且 `endpoints` 含 `vision_analyze`。

---

### 4. PC 主后端配置（在 PC 执行）

1. 复制示例为 `backend/.env`（或与现有合并）：

   ```bash
   # 在 PC，仓库根 dajian-ai-coach 下
   cp backend/.env.board.vision.example backend/.env
   ```

2. 编辑 `backend/.env`：把 `ASCEND_BASE_URL` 改为 **`http://BOARD_IP:18081`**（无尾斜杠）。

3. 启动主后端（示例）：

   ```bash
   cd backend
   # Windows PowerShell 可先设环境变量再启动；或依赖 config.py 自动读 .env
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

**成功判定**（在 PC）：

```bash
curl -sS http://127.0.0.1:8000/api/system/provider-status
```

- `vision_provider` 为 `ascend`
- `speech_provider` 为 `local`
- `ascend_base_url` 为配置的板址
- `ascend_health_check.reachable` 为 **true**
- `system_health_hint` 为 **ok**

若 `reachable` 为 false：检查防火墙、IP、端口、板子服务是否监听 `0.0.0.0:18081`。

---

### 5. 前端联调（在 PC 执行）

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://127.0.0.1:5173`（或你的 PC 局域网 IP + 5173）。

**成功判定**：能登录；训练页「训练前准备检查」中 **「画面分析」为通过**（`VISION_PROVIDER=ascend` 且板子可达时）。

> 若前端不在 `localhost:5173`，需保证主后端 CORS 允许该来源（默认见 `backend/app.py`）；否则改为在允许的 origin 下访问或临时调整 CORS（属部署问题，非视觉链路独有）。

---

### 6. 验证 provider-status（在 PC 执行）

```bash
curl -sS http://127.0.0.1:8000/api/system/provider-status | python -m json.tool
```

**成功判定**：同第 4 步；首页若拉取系统状态，应能看到板侧可达（见 `Home.vue` 中 `loadSystemStatus` 调用 `/system/provider-status`）。

---

### 7. 短视频训练 + 视觉结果（浏览器 + PC）

1. 进入 **训练**，完成一次 **较短** 录像（建议 10–30 秒，便于联调）。
2. 结束训练进入 **结果页**。

**成功判定**：

- PC 主后端日志出现 `[ascend.trace] vision BEGIN` / `vision END`…（经网关转发至板子）。
- 开发板终端出现 `[ascend_service.api.vision]` 日志。
- 结果页仪态/视觉相关指标有输出（`vision_valid` 为 false 时也可能为降级说明，但应证明请求已打到板侧）。

---

### 8. 结果页 / 报告页验收（浏览器）

- **结果页**：对应会话详情加载正常，视觉维度与文案合理。
- **报告页**：同一 `session_id` 打开报告，数据与结果一致。

**成功判定**：无 404/无权；视觉相关字段与本轮训练一致。

---

## 板侧视觉链路必要文件（当前仓库已具备）

以下均在仓库内，**无需另补路径**即可组成视觉 HTTP 服务：

- `ascend_service/app.py`
- `ascend_service/api/health.py`
- `ascend_service/api/vision.py`
- `ascend_service/services/vision_service.py`
- `ascend_service/schemas/protocol.py`
- `ascend_service/requirements.txt`

**缺什么会跑不通**（环境而非缺文件）：板侧成功安装 `mediapipe`、`opencv-python`、`numpy` 等；PC 到板子网络通。

---

## 常见问题

| 现象 | 处理 |
|------|------|
| `provider-status` 中 `reachable: false` | 板子防火墙、`ASCEND_BASE_URL` 错误、服务未监听 `0.0.0.0` |
| 视觉超时 | 调大 `ASCEND_VISION_TIMEOUT_SECONDS`（`backend/config.py` / `.env`） |
| 训练页「画面分析」block | 同上 + 确认 `VISION_PROVIDER=ascend` 与 `.env` 已被后端加载 |
