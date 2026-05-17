# Ascend Mock 联调说明（第一版）

本文用于验证 `SPEECH_PROVIDER=ascend` / `VISION_PROVIDER=ascend` 时，
后端已真正走通：

- ascend provider
- request/response adapter
- HTTP gateway
- mock ascend service

## 1. 启动 mock ascend service

在项目根目录执行：

```bash
cd backend
uvicorn mock_services.ascend_mock_service:app --host 127.0.0.1 --port 18080
```

健康检查：

```bash
curl http://127.0.0.1:18080/health
```

## 2. 切换到 ascend provider

在启动主后端前设置环境变量：

```bash
ASCEND_BASE_URL=http://127.0.0.1:18080
ASCEND_TIMEOUT_SECONDS=20
ASCEND_SPEECH_ENDPOINT=/mock/speech/analyze
ASCEND_VISION_ENDPOINT=/vision/analyze
SPEECH_PROVIDER=ascend
VISION_PROVIDER=ascend
```

再启动主后端服务（原有方式不变）。

## 3. 验证 speech / vision 端点分流

当前默认策略：

- speech 默认走 mock：`/mock/speech/analyze`
- vision 默认走真实端点：`/vision/analyze`

可通过环境变量覆盖：

- `ASCEND_SPEECH_ENDPOINT`
- `ASCEND_VISION_ENDPOINT`

### Speech

调用原路径 `POST /api/audio/analyze`（前端流程不用改）。

你应看到主后端日志包含：

- `[ascend.provider.speech] provider=ascend ...`
- `[ascend.adapter.request] speech request_id=...`
- `[ascend.gateway] POST url=http://127.0.0.1:18080/mock/speech/analyze ...`
- `[ascend.adapter.response] speech ... provider=ascend-mock`

mock 服务日志会打印：

- `[ascend-mock] speech request_id=...`

### Vision

调用原路径 `POST /api/vision/analyze`（前端流程不用改）。

你应看到主后端日志包含：

- `[ascend.provider.vision] provider=ascend ...`
- `[ascend.adapter.request] vision request_id=...`
- `[ascend.gateway] POST url=http://127.0.0.1:18080/vision/analyze ...`
- `[ascend.adapter.response] vision ... provider=ascend-service`（或真实开发板 provider）

若你仍希望 vision 走 mock，可显式设置：

```bash
ASCEND_VISION_ENDPOINT=/mock/vision/analyze
```

## 4. 后续替换为真实开发板 URL

当板端服务可用后，仅需把：

- `ASCEND_BASE_URL=http://127.0.0.1:18080`

替换为真实开发板网关地址（例如 `http://board-gateway:xxxx`）。

若真实板端协议字段有差异，只需改：

- `backend/adapters/ascend_request_adapter.py`
- `backend/adapters/ascend_response_adapter.py`

前端 API 路径与主流程无需变更。
