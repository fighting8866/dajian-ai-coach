# 开发板 × PC 主后端 · 最小联调检查清单（V1）

**范围**：第一阶段只验证 **视觉** 走开发板；`SPEECH_PROVIDER=local`；前端与主后端在 PC。

---

## 0. 前置

- [ ] 开发板与 PC **网络互通**（互 ping / 同网段或路由可达）。
- [ ] 开发板已部署 `ascend_service` 目录 + `requirements.txt`，且 **工作目录为 `ascend_service` 的父目录** 启动 uvicorn。
- [ ] PC `backend/.env` 已设置 `ASCEND_BASE_URL`、`VISION_PROVIDER=ascend`、`SPEECH_PROVIDER=local`，并已 **重启主后端**。

---

## 1. 开发板本机（无 PC）

在开发板上：

```bash
curl -sS "http://127.0.0.1:18081/health" | head
```

期望：HTTP 200，JSON 中含端点说明（含 `vision_analyze` 等）。

可选（需准备小视频文件）：

```bash
curl -sS -X POST "http://127.0.0.1:18081/vision/analyze" \
  -F "request_id=smoke-local" \
  -F "video_file=@/path/to/test.webm"
```

期望：HTTP 200，`success` 为真或业务错误信息可读；终端出现 `[ascend_service.api.vision]` / `[ascend_service.vision]` 日志。

---

## 2. PC → 开发板（网络与防火墙）

将 `<BOARD_IP>` 换成实际 IP：

```bash
curl -sS "http://<BOARD_IP>:18081/health" | head
```

期望：与步骤 1 类似。若失败：查开发板防火墙、端口是否监听 `0.0.0.0`、IP 是否错误。

---

## 3. PC 主后端自检接口

```bash
curl -sS "http://127.0.0.1:8000/api/system/provider-status"
```

（若主后端端口不同，改 URL。）

重点看 JSON：

- [ ] `vision_provider` 为 **`ascend`**
- [ ] `speech_provider` 为 **`local`**
- [ ] `ascend_health_check.reachable` 为 **`true`**
- [ ] `ascend_health_check.checked_url` 为 **`{ASCEND_BASE_URL}/health`**
- [ ] `system_health_hint` 为 **`ok`**（若板址未配为 `board_url_missing`，不可达为 `board_unreachable`）

可选：

```bash
curl -sS "http://127.0.0.1:8000/health"
```

顶层或 `providers` 中应能反映 `vision_provider`、`ascend_base_url` 等（与 `backend/app.py` 当前实现一致即可）。

---

## 4. 端到端（前端或 API）

- [ ] 在训练流程中触发 **上传录像并由后端调用视觉分析**（前端走 `POST /api/vision/analyze`）。
- [ ] PC 主后端日志出现：`[ascend.trace] vision SEND` → `multipart DONE`（失败则看 `multipart FAIL` 与错误码）。
- [ ] 开发板终端出现：`[ascend_service.api.vision]` 及 `SUMMARY` / `FINAL` 行。

---

## 5. 失败时优先看哪里

| 现象 | 先看 |
|------|------|
| `provider-status` 中 `reachable=false` | PC 能否访问 `<ASCEND_BASE_URL>/health`；板子 uvicorn 是否启动；IP/端口；防火墙。 |
| `multipart FAIL` / 超时 | PC 日志中的 URL 与超时 `ASCEND_VISION_TIMEOUT_SECONDS`；板侧是否卡死；视频过大。 |
| 板侧 import 错误 | 板子 venv 是否执行 `pip install -r ascend_service/requirements.txt`。 |
| 视觉结果异常但通迅正常 | 板侧 `[ascend_service.vision]` 日志；`VISION_TARGET_ANALYSIS_FPS` / `VISION_MAX_ANALYSIS_FRAMES`。 |

---

## 6. 本阶段不要求

- [ ] 不验证 `POST /speech/analyze`（语音仍 local）。
- [ ] 不要求训练/评分/大模型相关接口在板上运行。
