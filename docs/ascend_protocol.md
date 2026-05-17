# 开发板接入预留协议与通信层（第一版）

## 为什么要增加通信层

当前后端已经具备本地 `provider` 能力（speech/vision/ppt/qa），并且现有 API 路径与前端流程已稳定。  
为了后续接入昇腾开发板，先增加一层**可替换通信结构**：

- `provider` 负责业务能力选择（local / ascend）
- `gateway` 负责和未来开发板服务通信（当前为 HTTP 占位）
- `adapter` 负责内部结构与板端协议结构转换

这样可以在不改现有 API 路径的前提下，先把接入边界清晰化。

## 预留请求协议（Speech / Vision）

Speech 请求（当前已升级为文件上传）：

`POST /speech/analyze` 使用 `multipart/form-data`，关键字段：

- `request_id`: 字符串，请求追踪 ID
- `audio_file`: 音频二进制文件

说明：主后端会先接收前端上传音频并保存到本地，再把文件内容上传给 `ascend_service`。  
这避免了远端服务直接读取主后端本地路径（`audio_path`）的问题，更适合后续 PC -> 开发板部署。

Vision 请求（当前已升级为文件上传）：

`POST /vision/analyze` 使用 `multipart/form-data`，关键字段：

- `request_id`: 字符串，请求追踪 ID
- `video_file`: 视频二进制文件

说明：主后端会先接收前端上传视频并保存到本地，再把文件内容上传给 `ascend_service`。  
这避免了远端服务直接读取主后端本地路径（`video_path`）的问题，更适合后续 PC -> 开发板部署。

统一响应结构（示例）：

```json
{
  "success": true,
  "provider": "ascend",
  "request_id": "9adf...e3",
  "result": {
    "transcript": "...",
    "speech_rate": 165.2
  },
  "error": null
}
```

对应代码中的协议模型位于 `backend/gateways/ascend_gateway/base.py`。

## local provider 与 ascend provider 的区别

- `local provider`：直接调用本地实现（当前默认，不依赖开发板服务）
- `ascend provider`：将请求转换为统一协议，通过 `AscendHttpGateway` 调用远程服务，再把响应适配回内部结果

当前协议状态：

- `speech`：已升级为文件上传协议（`multipart/form-data` + `audio_file`），并在 `ascend_service` 内执行真实音频分析
- `vision`：已升级为文件上传协议（`multipart/form-data` + `video_file`），并在 `ascend_service` 内执行真实视觉分析

默认 endpoint（主后端 -> ascend_service）：

- `ASCEND_SPEECH_ENDPOINT=/speech/analyze`（不再默认走 `/mock/speech/analyze`）
- `ASCEND_VISION_ENDPOINT=/vision/analyze`

本次仅完成结构预留，未强制接通真实开发板服务。

## 真正接开发板时需要实现哪些层

后续只需要完善以下层即可，不需要改前端 API 主流程：

1. `gateways/ascend_gateway/http_gateway.py`：对接真实网关地址与鉴权、重试策略等
2. `adapters/ascend_request_adapter.py`：补齐板端需要的请求字段
3. `adapters/ascend_response_adapter.py`：将板端真实响应映射为内部结构
4. `providers/*/ascend_*_provider.py`：根据实际能力增加参数/错误处理

## fallback 机制

第一版 fallback 规则：

- 默认 `SPEECH_PROVIDER=local`、`VISION_PROVIDER=local`，即默认走本地能力
- 仅当显式配置为 `ascend` 时，才走网关调用链路
- 若配置为 `ascend` 但未设置 `ASCEND_BASE_URL`，会抛出明确错误：`当前未配置开发板服务地址`

该机制保证默认现有流程不受影响，并允许按配置逐步切换到开发板。

补充说明：当前视觉分析第一版基于 MediaPipe Solutions API，后端环境暂时固定 `mediapipe==0.10.21` 以保持兼容。

## 如何验证 speech 新协议已生效

建议按下面顺序验证：

1. 主后端配置 `SPEECH_PROVIDER=ascend`，并确保 `ASCEND_SPEECH_ENDPOINT=/speech/analyze`。
2. 正常走前端既有流程调用 `POST /api/audio/analyze`（前端流程与 API 路径无需变更）。
3. 主后端日志应出现：
   - `send_speech ... transport=multipart/form-data`
   - `POST multipart ... file_name=... request_id=...`
4. `ascend_service` 日志应出现：
   - `uploaded file saved ... bytes=...`
   - `speech.normalize / speech.validity / speech.transcribe / speech.metrics`
   - `final audio_valid=... audio_message=...`
5. 返回结果中的 `transcript` 应来自真实 ASR，不再是固定占位文本。
