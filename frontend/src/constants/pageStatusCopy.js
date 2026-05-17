/**
 * 全站页面级加载/状态文案（仅展示层，不参与业务判断）
 * 用于 Home / Training / Result / History / Report 等同构体验
 */

/** 主列表区 / 全屏骨架：标题行 + 辅助句 */
export const PAGE_LOADING = {
  result: {
    label: '正在获取本轮结果…',
    hint: '请稍候，系统正在拉取分数与说明。',
  },
  history: {
    label: '正在加载历史记录…',
    hint: '请稍候，正在拉取记录与总览。',
  },
  report: {
    label: '正在获取报告内容…',
    hint: '请稍候，稍后可审阅、打印或另存为 PDF。',
  },
  homeOverview: {
    label: '正在加载训练概况…',
    hint: '请稍候，将展示目标、节奏与周报摘要。',
  },
  /** 首页演示区主 CTA 等待 */
  homeDemoPrimary: '正在加载训练概况，稍候即可选择演示起点…',
  /** 系统状态小区域 */
  systemStatus: '正在获取系统状态…',
  /** 训练页准备检查 */
  trainingPreflight: '正在检查环境、服务与设备权限…',
}

/** 报错区 el-alert 标题（与业务错误详情区分：标题统一、正文仍用接口/脱敏信息） */
export const PAGE_ERROR_ALERT_TITLE = {
  result: '无法加载本轮结果',
  history: '无法加载历史记录',
  report: '无法加载报告',
  homeOverview: '无法加载训练概况',
  /** 首页「系统状态」区块 */
  systemStatus: '暂时无法获取系统状态',
  /** 训练页全局操作错误条 */
  training: '暂时无法完成该操作',
}

/** 空状态/弱提示常用短句（可按页再包一层） */
export const PAGE_SOFT = {
  /** 统计口径：未纳入本轮可汇总数据 */
  trainingNotInStatsShort: '未纳入统计',
  trainingNotInStatsBody:
    '分数与说明仍可供你对照；再完成一轮完整训练后，更容易被趋势与总览引用。',
}
