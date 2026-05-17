# API 接口文档

## 会话管理

### POST /api/session/start
**功能**：开始一个新的训练会话

**请求体**：
```json
{
  "user_id": "user123",
  "session_name": "演示训练"
}
```

**响应**：
```json
{
  "session_id": "xxx",
  "start_time": "2026-04-14T12:00:00",
  "message": "训练已开始"
}
```

### POST /api/session/stop
**功能**：停止训练会话并计算评分

**请求体**：
```json
{
  "session_id": "xxx",
  "metrics": {
    "speech_rate": 238,
    "pause_count": 11,
    "avg_pause_sec": 0.9,
    "filler_count": 4,
    "forward_gaze_ratio": 0.63,
    "downward_head_ratio": 0.18,
    "posture_stability": 0.76
  },
  "ppt_match": {
    "page_index": 1,
    "title": "项目简介",
    "match_score": 85,
    "keyword_coverage": 0.8,
    "matched_keywords": ["项目", "简介", "背景"],
    "missing_keywords": ["目标"],
    "comment": "当前页讲解匹配度较高，核心内容覆盖较充分"
  },
  "qa_result": {
    "questions": [
      {
        "question": "请介绍一下你的项目背景",
        "answer": "我的项目是基于深度学习的智能问答系统，旨在解决用户的常见问题",
        "relevance_score": 0.85,
        "is_relevant": true
      }
    ],
    "overall_relevance": 0.85,
    "feedback": "回答整体切题，能够清晰表达项目背景"
  }
}
```

**响应**：
```json
{
  "session_id": "xxx",
  "status": "completed",
  "message": "训练已结束"
}
```

## 结果管理

### GET /api/result/{session_id}
**功能**：获取训练结果

**响应**：
```json
{
  "session_id": "xxx",
  "total_score": 82,
  "language_score": 85,
  "posture_score": 78,
  "metrics": [
    {"name": "语速", "value": 220, "unit": "字/分钟", "description": "演讲平均语速"},
    {"name": "停顿次数", "value": 8, "unit": "次", "description": "演讲中的停顿次数"},
    {"name": "平均停顿时长", "value": 0.8, "unit": "秒", "description": "平均每次停顿时长"},
    {"name": "口头禅次数", "value": 2, "unit": "次", "description": "无意义填充词出现次数"},
    {"name": "正视前方比例", "value": 0.78, "unit": "", "description": "面向听众的时间比例"},
    {"name": "低头率", "value": 0.08, "unit": "", "description": "低头看稿或屏幕的比例"},
    {"name": "姿态稳定度", "value": 0.85, "unit": "", "description": "站姿和身体稳定程度"}
  ],
  "suggestions": [
    {"category": "语速", "content": "语速适中，保持良好的节奏"},
    {"category": "停顿", "content": "停顿自然，节奏良好"},
    {"category": "口头禅", "content": "口头禅使用较少，表现良好"}
  ],
  "summary": {
    "overall_comment": "整体表现优秀，已经具备较好的答辩表达能力",
    "strongest_aspect": "语速控制较好",
    "weakest_aspect": "口头禅需要改进",
    "training_tip": "建议注意减少口头禅的使用"
  },
  "ppt_match": {
    "page_index": 1,
    "title": "项目简介",
    "match_score": 85,
    "keyword_coverage": 0.8,
    "matched_keywords": ["项目", "简介", "背景"],
    "missing_keywords": ["目标"],
    "comment": "当前页讲解匹配度较高，核心内容覆盖较充分"
  },
  "qa_result": {
    "questions": [
      {
        "question": "请介绍一下你的项目背景",
        "answer": "我的项目是基于深度学习的智能问答系统，旨在解决用户的常见问题",
        "relevance_score": 0.85,
        "is_relevant": true
      }
    ],
    "overall_relevance": 0.85,
    "feedback": "回答整体切题，能够清晰表达项目背景"
  }
}
```

### GET /api/history
**功能**：获取训练历史记录

**响应**：
```json
{
  "history": [
    {
      "session_id": "xxx",
      "session_name": "训练_123456",
      "timestamp": "2026-04-14T12:00:00",
      "total_score": 82,
      "language_score": 85,
      "posture_score": 78,
      "start_time": "2026-04-14T12:00:00",
      "end_time": "2026-04-14T12:05:00",
      "status": "completed"
    }
  ]
}
```

## PPT 匹配

### POST /api/ppt/upload
**功能**：上传 PPT 文件并解析

**注意**：当前演示版本只支持 .pptx 文件

**请求**：
- 方法：POST
- 路径：/api/ppt/upload
- 内容类型：multipart/form-data
- 字段：file (文件)

**响应**：
```json
{
  "ppt_id": "xxx",
  "source_ext": ".pptx",  // 原始文件扩展名
  "parsed_file_ext": ".pptx",  // 实际解析的文件扩展名
  "pages": [
    {
      "page_index": 1,
      "title": "项目简介",
      "keywords": ["项目", "背景", "目标", "意义"]
    }
  ]
}
```

### POST /api/ppt/match
**功能**：匹配 PPT 页面与讲解内容

**请求体**：
```json
{
  "ppt_id": "xxx",
  "page_index": 1,
  "spoken_text": "这是我的项目简介，主要介绍项目背景和目标"
}
```

**响应**：
```json
{
  "page_index": 1,
  "title": "项目简介",
  "match_score": 80,
  "keyword_coverage": 0.8,
  "matched_keywords": ["项目", "背景", "目标"],
  "missing_keywords": ["意义"],
  "comment": "当前页讲解匹配度较高，核心内容覆盖较充分"
}
```

## 问答模拟

### POST /api/qa/generate
**功能**：基于 PPT 页面生成答辩问题

**请求体**：
```json
{
  "ppt_id": "xxx",
  "page_index": 1,
  "num_questions": 3
}
```

**响应**：
```json
{
  "page_index": 1,
  "title": "项目简介",
  "questions": [
    "请介绍一下你的项目背景",
    "你的项目目标是什么",
    "项目的创新点在哪里"
  ]
}
```

### POST /api/qa/evaluate
**功能**：评估答辩回答的相关性

**请求体**：
```json
{
  "ppt_id": "xxx",
  "page_index": 1,
  "answers": [
    {
      "question": "请介绍一下你的项目背景",
      "answer": "我的项目是基于深度学习的智能问答系统，旨在解决用户的常见问题"
    }
  ]
}
```

**响应**：
```json
{
  "page_index": 1,
  "title": "项目简介",
  "questions": [
    {
      "question": "请介绍一下你的项目背景",
      "answer": "我的项目是基于深度学习的智能问答系统，旨在解决用户的常见问题",
      "relevance_score": 0.85,
      "is_relevant": true
    }
  ],
  "overall_relevance": 0.85,
  "feedback": "回答整体切题，能够清晰表达项目背景"
}
```

## 训练报告

### GET /api/report/{session_id}
**功能**：获取训练报告

**请求路径**：`/api/report/{session_id}`

**路径参数**：
- `session_id`：会话 ID（必填）

**响应**：
```json
{
  "session_id": "xxx",
  "session_name": "演示训练",
  "start_time": "2026-04-14T12:00:00",
  "end_time": "2026-04-14T12:05:00",
  "total_score": 82,
  "language_score": 85,
  "posture_score": 78,
  "summary": {
    "overall_comment": "整体表现优秀，已经具备较好的答辩表达能力",
    "strongest_aspect": "语速控制较好",
    "weakest_aspect": "口头禅需要改进",
    "training_tip": "建议注意减少口头禅的使用"
  },
  "key_metrics": [
    {
      "category": "语言表达",
      "metrics": [
        {"name": "语速", "value": 220, "unit": "字/分钟", "score": 85},
        {"name": "停顿次数", "value": 8, "unit": "次", "score": 90},
        {"name": "口头禅次数", "value": 2, "unit": "次", "score": 95}
      ]
    },
    {
      "category": "视觉表现",
      "metrics": [
        {"name": "正视前方比例", "value": 0.78, "unit": "", "score": 75},
        {"name": "低头率", "value": 0.08, "unit": "", "score": 90},
        {"name": "姿态稳定度", "value": 0.85, "unit": "", "score": 85}
      ]
    }
  ],
  "ppt_match": {
    "page_index": 1,
    "title": "项目简介",
    "match_score": 85,
    "keyword_coverage": 0.8,
    "comment": "当前页讲解匹配度较高，核心内容覆盖较充分"
  },
  "qa_result": {
    "overall_relevance": 0.85,
    "feedback": "回答整体切题，能够清晰表达项目背景"
  },
  "suggestions": [
    {
      "category": "语言表达",
      "items": [
        "语速适中，保持良好的节奏",
        "口头禅使用较少，表现良好"
      ]
    },
    {
      "category": "视觉表现",
      "items": [
        "保持良好的站姿，避免不必要的移动",
        "适当增加与听众的眼神交流"
      ]
    }
  ],
  "conclusion": "通过本次训练，你在语言表达方面表现优秀，视觉表现也达到了良好水平。建议继续加强眼神交流和站姿稳定性，进一步提升整体答辩效果。"
}
```