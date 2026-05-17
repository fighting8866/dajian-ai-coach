# 答见 - AI辅助答辩/演讲训练助手

## 项目简介

一个基于AI技术的答辩/演讲训练助手，帮助学生和职场人士提升演讲表达能力。

## 核心功能

- **音频分析**：语速、停顿、口头禅等语音指标分析
- **视觉分析**：眼神交流，姿态稳定性等视觉分析
- **评分系统**：综合评分和针对性建议
- **历史记录**：训练历史和进步趋势分析
- **PPT匹配**：与演示文稿内容的匹配度分析
- **问答模拟**：基于PPT页面生成答辩问题并评估回答
- **训练报告**：自动生成结构化训练评估报告

## 技术栈

- **前端**：Vue3 + Vite + Element Plus
- **后端**：Python + FastAPI
- **数据库**：SQLite
- **音频处理**：faster-whisper, librosa, pydub
- **视觉处理**：OpenCV, MediaPipe
- **PPT处理**：python-pptx

## 快速开始

### 安装依赖

**后端**：
```bash
cd backend
pip install -r requirements.txt
```

**前端**：
```bash
cd frontend
npm install
```

### 启动服务

**后端**：
```bash
cd backend
python app.py
```

**前端**：
```bash
cd frontend
npm run dev
```

## 项目结构

- `backend/`：后端代码
  - `api/`：API接口
  - `services/`：核心服务
  - `models/`：数据模型
  - `database/`：数据库配置
- `frontend/`：前端代码
  - `src/`：源代码
    - `pages/`：页面组件
    - `api/`：API调用
    - `router/`：路由配置
- `docs/`：文档

## 注意事项

- 当前版本支持基于 PPT 页面进行答辩问题生成与规则评估
- 当前版本支持训练结果自动整理为结构化报告页面
- 训练报告页依赖后端 GET /api/report/{session_id} 接口
- 音频和视频分析功能需要浏览器权限
- PPT 解析仅支持 .pptx 格式

## 开发指南

- 后端API文档：http://localhost:8000/docs
- 前端开发服务器：http://localhost:5173