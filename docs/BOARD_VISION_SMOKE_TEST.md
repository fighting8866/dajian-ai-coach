# 开发板视觉链路 · 最小 Smoke Test 清单

**前提**：`VISION_PROVIDER=ascend`，`SPEECH_PROVIDER=local`，PC 可访问开发板 `ASCEND_BASE_URL`。

**执行环境标注**：`[BOARD]` 开发板 · `[PC]` 本机/PC

---

## Step A — 板侧服务存活 `[BOARD]`

```bash
curl -sS http://127.0.0.1:18081/health
```

**成功判定**：

- HTTP 200
- JSON：`status` 为 `ok`，`service` 为 `ascend-service`
- `endpoints.vision_analyze` 为 `/vision/analyze`

---

## Step B — 板侧视觉接口（multipart）`[BOARD]`

准备一段短视频 `test.webm`（或 mp4，依板侧解码能力），在开发板执行：

```bash
curl -sS -X POST "http://127.0.0.1:18081/vision/analyze" \
  -F "request_id=smoke-vision-1" \
  -F "video_file=@/path/to/test.webm"
```

**成功判定**：

- HTTP 200
- JSON 顶层：`success` 为 `true`，`provider` 含 `ascend`，`result` 为对象
- `result` 中含 `forward_gaze_ratio`、`downward_head_ratio`、`posture_stability`、`vision_valid` 等字段

（`vision_valid` 为 `false` 时若因视频太短/无有效帧，仍算「接口通」，但需换更正常片段再验一次指标合理性。）

---

## Step C — PC 探测板子 `[PC]`

（主后端已用 `.env` 配置 `ASCEND_BASE_URL` 并启动。）

```bash
curl -sS http://127.0.0.1:8000/api/system/provider-status
```

**成功判定**：

- `vision_provider` === `"ascend"`
- `speech_provider` === `"local"`
- `ascend_base_url_configured` === `true`
- `ascend_health_check.reachable` === `true`
- `system_health_hint` === `"ok"`

---

## Step D — PC 主后端直连视觉（可选，验证网关前路径）`[PC]`

主后端会先落盘再调 provider；最快是走训练流程。若需单独测 PC 的 `/api/vision/analyze`，可对 **PC** 上传短视频（与日常训练相同方式），并观察后端日志是否出现 `[ascend.trace] vision SEND` 指向 `ASCEND_BASE_URL`。

**成功判定**：日志中板址与 `POST .../vision/analyze` 一致，且返回非 5xx。

---

## Step E — 前端 Training preflight `[PC]` 浏览器

1. 打开训练页，展开「训练前准备检查」，点击重新检查（若有）。
2. 观察「画面分析」行。

**成功判定**：状态为 **通过**；文案含「开发板进行画面与仪态分析」类描述（`vision_provider=ascend` 且板子可达时）。

---

## Step F — 首页系统状态（可选）`[PC]` 浏览器

打开首页，若展示 provider / 板侧状态（代码中 `loadSystemStatus` 拉 `/system/provider-status`）。

**成功判定**：无加载错误；控制台或 UI 体现 `ascend_reachable: true`（与 Step C 一致）。

---

## Step G — 端到端短视频训练 `[PC]` 浏览器

完成一轮训练（含短视频），进入结果页。

**成功判定**：

- `[PC]` 后端日志：`[ascend.trace] vision BEGIN` … `success=true`（或明确降级原因）
- `[BOARD]` 终端：`[ascend_service.api.vision]` 日志出现且 `request_id` 可对应
- 结果页加载成功，视觉相关模块有数据或合规降级说明

---

## Step H — 报告页 `[PC]` 浏览器

从结果页或历史进入同一 session 的报告。

**成功判定**：报告打开无 404/无权；视觉维度与结果页一致。

---

## 失败时优先检查

1. `ASCEND_BASE_URL` 是否无尾斜杠、IP/端口是否正确  
2. 开发板防火墙与监听地址是否为 `0.0.0.0:18081`  
3. 板侧 `mediapipe` / `opencv` 是否安装成功（Step B 在板本机失败则 PC 必失败）
