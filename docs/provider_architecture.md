# 后端能力 Provider 架构（第一版）

## 1. 为什么要做接口封装

- 业务代码（FastAPI 路由、会话落库）应与「模型在哪跑」解耦：本地 CPU、昇腾开发板或 HTTP 远程服务应可切换。
- 统一入口后，新增环境变量即可切换实现，**无需改 URL、不改前端**。
- 现有 `*_service.py` 保留为可复用的领域逻辑；Provider 负责「选哪一种实现 + 调用 service」。

## 2. local provider 如何工作

| Provider | 本地实现类 | 内部复用 |
|----------|------------|----------|
| Speech | `LocalWhisperSpeechProvider` | `transcribe` 为 Whisper；`analyze_audio` 委托 `AudioService`（归一化、静音门控、指标） |
| Vision | `LocalVisionAIProvider` | `VisionService.analyze_video`（当前为占位返回） |
| PPT | `LocalPPTProvider` | `PPTService` + `PPTMatchService` |
| QA | `LocalRuleQAProvider` | 内嵌 `RuleBasedAnalysisProvider`（规则问答） |

工厂：`factories/provider_factory.py`，按环境变量选择实现（进程内 `@lru_cache` 单例）。

## 3. 后续如何接入开发板（Ascend）Provider

1. 在 `providers/<domain>_provider/` 下新增 `ascend_*_provider.py`，实现对应抽象基类方法。
2. 在 `provider_factory.py` 的 `get_*_provider()` 中，当 `*_PROVIDER=ascend` 时返回新类（当前对 `ascend` 抛出 `NotImplementedError` 作为占位）。
3. 开发板侧若走 HTTP，可在 Ascend Provider 内用 `httpx` 调用板端服务，**路由与数据库仍不变**。

兼容旧变量（仍支持）：`SPEECH_AI_PROVIDER=local_whisper`、`ANALYSIS_AI_PROVIDER=rule_based`。

## 4. 已完成 local provider 化的能力

- **语音**：`SpeechAIProvider` — `transcribe`、`analyze_audio`；HTTP：`POST /api/audio/analyze`。
- **视觉**：`VisionAIProvider` — `analyze_video`；HTTP：`POST /api/vision/analyze`（本版为占位）。
- **PPT**：`PPTProvider` — `parse_ppt`、`extract_text_by_slide`、`match_page_content`、`match_transcript_with_ppt`；HTTP：`/api/ppt/parse|upload|match|match_v1`。
- **问答**：`QAProvider` — `generate_question`、`evaluate_answer`；HTTP：`POST /api/qa/generate`、`POST /api/qa/evaluate`。

**未**改为 Provider 的模块（按需求刻意保留）：`session` / `result` / `report` / `score_service` 等业务编排与持久化。

## 5. 哪些能力更适合未来迁到开发板

- **语音 ASR**：算力敏感，适合昇腾 NPU 或独立推理服务。
- **视觉**：视频/关键点推理适合板端或 GPU；当前本地仅为占位。
- **PPT**：解析可在本地；若板端统一做「文档理解」，可只把 **重匹配/大模型** 迁走。
- **问答**：规则版可留本地；若升级为 LLM，适合远端或板载大模型 Provider。

## 6. 配置切换（当前）

在运行前设置环境变量，例如：

```bash
set SPEECH_PROVIDER=local
set VISION_PROVIDER=local
set PPT_PROVIDER=local
set QA_PROVIDER=local
```

将来：

```bash
set SPEECH_PROVIDER=ascend
set VISION_PROVIDER=ascend
```

（需在工厂中实现对应 Ascend Provider 类。）

配置文件：`backend/config.py`（默认值）；工厂内会合并 `SPEECH_PROVIDER` 与旧变量 `SPEECH_AI_PROVIDER` 等。
