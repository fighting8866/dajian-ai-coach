# 文档理解增强 V1

## 本步目标

在**不改变训练主流程、语音/视觉协议、评分权重**的前提下，增加**统一文档理解服务**与**调试接口**，提升 PPT / PDF（及后续图片）的文本与结构化输出质量，为内容评分、问答生成、追问等能力打基础。

## 统一输出结构（`document`）

解析结果为一个 JSON 对象，核心字段如下：

```json
{
  "doc_type": "pptx|pdf|image",
  "pages": [
    {
      "page_no": 1,
      "title": "...",
      "plain_text": "...",
      "markdown_text": "...",
      "keywords": ["...", "..."],
      "blocks": [{ "type": "...", "text": "..." }]
    }
  ],
  "full_text": "...",
  "outline": [{ "page_no": 1, "title": "..." }],
  "metadata": { "parser": "...", "document_parser_provider": "basic|markitdown|docling", "...": "..." }
}
```

- **PPT（pptx）**：`python-pptx` 抽文本；**每页 `blocks`** 按幻灯片内形状顺序输出 `text` / `table` 块（与 `PPTService` 内 `_iter_shape_text_chunks` 一致）；另含 `title`（首行/启发式）、`keywords`（规则）、简易 `markdown_text`。全页 `plain_text` 仍与历史「去重拼接」逻辑一致。
- **PDF**：见下文「解析策略」。
- **图片**：V1 **仅占位**，`pages` 为空，`metadata.status = not_implemented`。

## 配置

环境变量（或 `config.settings` 默认值）：

| 变量 | 含义 | 默认 |
|------|------|------|
| `DOCUMENT_PARSER_PROVIDER` | `basic`：pypdf 文本层；`markitdown`：PDF 优先 MarkItDown；`docling`：预留，当前仍回退文本层 | `basic` |

实现位置：`backend/config.py`、`backend/factories/provider_factory.py`（`get_document_parser_provider_kind`、`get_document_understanding_service`）。

## 开源增强路线（当前接入深度）

### 1. MarkItDown（多格式 → Markdown）

- **定位**：微软开源，适合将 Office/PDF 等转为 Markdown，便于后续 LLM 与结构化流水线。
- **V1 接入**：当 `DOCUMENT_PARSER_PROVIDER=markitdown` 时，对 **PDF** 优先调用 `markitdown.MarkItDown().convert(path)`；若未安装或转换失败，**自动回退**到 `pypdf` 文本层，并在 `metadata.notes` 中说明。转换成功后按 **换页符 `\f`** 或 **Markdown 标题** 做轻量分页，生成多页 `pages`（否则整篇一页）。
- **安装**（可选）：`pip install 'markitdown[pdf]'`

### 2. Docling（更强结构化文档理解）

- **定位**：IBM 等推动的文档解析，表格/版式理解更强。
- **V1 接入**：**预留**。`DOCUMENT_PARSER_PROVIDER=docling` 时，PDF 仍使用 **pypdf 文本层**，`metadata` 标明 `docling_reserved` / 说明文字，避免静默假接入。

### 3. PaddleOCR（扫描件 / 图片）

- **定位**：版式与中文 OCR 常见选型。
- **V1 接入**：**仅占位**。`/api/document/parse` 对图片扩展名返回统一壳结构，`metadata.paddleocr: reserved`，不执行真实识别。对 **PDF 文本层过弱**（basic 模式超半数页为空、或 MarkItDown 输出极短）时，`metadata` 会标记 `weak_text_layer` 并同样保留 `paddleocr: reserved`，提示后续可接 OCR。

## 调试接口

- **POST** `/api/document/parse`  
  - multipart 上传单文件。  
  - 支持：`pptx`、`pdf`；图片后缀返回占位结构。  
  - 响应：`document_parser_provider`、`document`（统一结构）、`saved_path`（调试用落盘路径）。

## 与现有 PPT 主流程的关系

- **POST** `/api/ppt/parse`：路径与原有返回字段 **不变**（`full_text`、`slides`）；`slides` 中每项可含 **`blocks`**（新字段，旧客户端可忽略）。  
- 解析成功时**额外**附加 `document` 字段。  
- **POST** `/api/ppt/upload`：原有 `ppt_id` / `pages` 不变；在成功解析时同样**尝试**附加 `document`（失败不影响上传）。

## 依赖

- **必选（V1 PDF basic）**：`pypdf`（已写入 `requirements.txt`）。  
- **可选**：`markitdown[pdf]`（见上文）。

## 验证建议

1. 启动 API 后，对 `.pptx` 调用 `POST /api/document/parse`，检查 `document.pages[].title/plain_text/keywords`。  
2. 对文本型 `.pdf` 在 `DOCUMENT_PARSER_PROVIDER=basic` 下调用同一接口，确认按页 `plain_text`。  
3. 安装 MarkItDown 后设 `DOCUMENT_PARSER_PROVIDER=markitdown`，对同一 PDF 对比 `metadata.parser` 是否为 `markitdown`。  
4. 调用 `POST /api/ppt/parse`，确认响应中除 `slides` 外含 `document`。  
5. 上传 `.png` 等，确认占位 `metadata.status` 与说明文案。  
6. `GET /health` 或 `GET /api/system/provider-status` 中 `providers.document_parser_provider` 与当前环境变量一致。
