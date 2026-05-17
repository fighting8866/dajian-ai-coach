# 昇腾开发板部署清单 · 第一阶段（仅视觉上板）

**策略**：前端与主后端留在 PC；开发板只跑 `ascend_service`，承担视觉推理 HTTP 服务；语音保持 `SPEECH_PROVIDER=local`；不搬整套仓库、不接大模型、不改训练主流程。

---

## 一、仓库内检索结果（全局搜索确认）

| 关键词 | 出现位置（摘要） |
|--------|------------------|
| `ascend_service.app:app` | `ascend_service/README.md`、`docs/ascend_deployment_v1.md`；启动命令为板侧 uvicorn 入口。 |
| `ASCEND_BASE_URL` | `backend/config.py`（主配置）、`backend/gateways/ascend_gateway/http_gateway.py`、`backend/factories/provider_factory.py`、`backend/api/system.py`（`provider-status` 探测）。 |
| `VISION_PROVIDER` | `backend/config.py`、`backend/factories/provider_factory.py`。 |
| `SPEECH_PROVIDER` | `backend/config.py`、`backend/factories/provider_factory.py`（可与旧名 `SPEECH_AI_PROVIDER` 兼容）。 |
| `/vision/analyze` | **板侧**：`ascend_service/api/vision.py`（`POST /vision/analyze`）。**主后端对外**：`backend/api/vision.py`（`POST /api/vision/analyze`），经网关转发到 `{ASCEND_BASE_URL}/vision/analyze`。 |
| `/speech/analyze` | **板侧**：`ascend_service/api/speech.py`。第一阶段可不在 PC 侧启用 ascend 语音。 |
| `provider-status` | `backend/api/system.py` → `GET /api/system/provider-status`（含 `ascend_health_check`）。 |
| `health` | **主后端**：`backend/app.py` → `GET /health`。**板侧**：`ascend_service/api/health.py` → `GET /health`。 |
| `uvicorn` | `backend/requirements.txt`、`ascend_service/requirements.txt`；文档中的启动示例。 |

---

## 二、第一阶段：最少需要拷贝到开发板的内容

1. **必选目录（整块拷贝）**  
   - `ascend_service/`  
   内含 `app.py`、`api/`、`services/`、`schemas/`、`requirements.txt` 等；**必须保持「上一级目录能 `import ascend_service`」的目录结构**。

2. **必选文件**  
   - `ascend_service/requirements.txt`

3. **推荐一并带上（免查路径）**  
   - `scripts/board_start_ascend_service.sh`（本仓库提供的启动脚本）  
   - 本文档、`docs/BOARD_SMOKE_TEST.md`

4. **不要**在第一阶段要求拷贝：`backend/`、`frontend/`、训练数据、大模型权重（当前视觉管线以 **MediaPipe + OpenCV** 为主，见下）。

**目录布局示例（开发板上）**：

```text
/opt/dajian-ai-coach/          ← 工作目录（示例）
  ascend_service/              ← Python 包
    app.py
    requirements.txt
    ...
```

启动时 **当前工作目录** 必须是 **`ascend_service` 的父目录**（如上例中的 `/opt/dajian-ai-coach`），否则 `python -m uvicorn ascend_service.app:app` 无法解析包名。

---

## 三、`ascend_service` 启动依赖（requirements）

以仓库内 **`ascend_service/requirements.txt`** 为准，当前包含：

- `fastapi`、`uvicorn`、`pydantic`、`python-multipart`
- **视觉链路**：`mediapipe`、`opencv-python`、`numpy`
- **语音链路（本阶段可不启用，但同文件会装上）**：`faster-whisper`、`pydub`、`librosa`、`soundfile`

板侧安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r ascend_service/requirements.txt
```

> **说明**：ARM/Ascend 上部分包（如 `mediapipe`、`faster-whisper`）可能没有现成 wheel，需按板卡厂商给的 Python/conda 环境与镜像源安装。第一阶段若仅验证视觉，仍以「能装上 `mediapipe` + `opencv-python`」为硬门槛；语音依赖装不上时，只要不调 `POST /speech/analyze`，视觉路径仍可单独验证。

---

## 四、视觉模型与配置文件路径

| 类型 | 说明 |
|------|------|
| **MediaPipe** | `vision_service.py` 使用 `mp.solutions.pose`、`mp.solutions.face_detection`；模型由 **MediaPipe 运行时自动加载/缓存**（常见为用户目录下缓存，依版本与系统而定），**仓库内无单独 `.onnx` 路径**。 |
| **OpenCV Haar** | 使用 `cv2.data.haarcascades + "haarcascade_frontalface_default.xml"`，随 **opencv-python** 安装自带。 |
| **可选环境变量（板侧与主后端同名，便于对齐）** | `VISION_TARGET_ANALYSIS_FPS`（默认 `1.0`）、`VISION_MAX_ANALYSIS_FRAMES`（默认 `240`），在 `ascend_service/services/vision_service.py` 中读取。 |
| **ffprobe** | 非 Python 依赖；部分视频时长修复会尝试调用系统 `ffprobe`（可选）。 |

---

## 五、PC 主后端仅切视觉到 Ascend 时：`.env` 改哪些

在 **`backend/.env`**（或与 `config.py` 同目录、已被 `_load_backend_dotenv()` 加载的文件）中设置：

| 变量 | 建议值 | 说明 |
|------|--------|------|
| `ASCEND_BASE_URL` | `http://<开发板IP>:<端口>` | **无尾斜杠**，与板侧 uvicorn 监听一致，如 `http://192.168.1.10:18081`。 |
| `VISION_PROVIDER` | `ascend` | 视觉走开发板。 |
| `SPEECH_PROVIDER` | `local` | 第一阶段语音仍本机。 |

默认即可（一般不必改）：

- `ASCEND_VISION_ENDPOINT=/vision/analyze`
- `ASCEND_SPEECH_ENDPOINT=/speech/analyze`

改完后 **重启主后端**。

---

## 六、协议与路径对照（联调时防混）

| 角色 | 路径 |
|------|------|
| 浏览器 / 前端 → PC 主后端 | `POST /api/vision/analyze` |
| PC 主后端 → 开发板 `ascend_service` | `POST {ASCEND_BASE_URL}/vision/analyze`（multipart：`video_file`、`request_id`） |
| 存活检查 | 板侧 `GET {ASCEND_BASE_URL}/health`；PC `GET /api/system/provider-status` |

---

## 七、第一轮联调建议看的日志

1. **开发板终端**：uvicorn 标准输出；视觉请求时出现 `[ascend_service.api.vision]`、`[ascend_service.vision]` 等行。  
2. **PC 主后端**：`[ascend.trace] GATEWAY_INIT`、`[ascend.trace] vision SEND`、`[ascend.trace] multipart DONE/FAIL`、`[ascend.trace] vision BEGIN/END`。  
3. **自检接口**：PC 上 `GET /api/system/provider-status` → `ascend_health_check.reachable=true`、`vision_provider=ascend`。

更细步骤见 **`docs/BOARD_SMOKE_TEST.md`**。
