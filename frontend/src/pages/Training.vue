<template>
  <div
    class="training-page training-workbench ui-page-frame ui-page-shell-inset"
    :class="{
      'training-page--defense-main': sessionId && !trainingFlowDebugMode,
      'training-page--demo-mode': demoModeUi.active,
      'training-page--prep-layout': !sessionId,
    }"
  >
    <header class="training-page-head ui-page-header">
      <p class="ui-page-header__eyebrow training-page-head__eyebrow">训练工作台</p>
      <h1 class="training-page-title ui-page-title">{{ pageHeroTitle }}</h1>
      <p class="ui-page-sub training-page-head__sub">
        上方为当前阶段摘要；下方主区完成模式、课件与自检后即可开始训练。
      </p>
    </header>

    <div
      class="training-prep-connector"
      :class="{ 'training-prep-connector--prep': !sessionId }"
    >
    <section
      class="training-primary-status-card training-main-mission ui-surface"
      :class="[
        'training-primary-status-card--' + uiSessionState,
        { 'training-primary-status-card--demo': demoModeUi.active },
      ]"
      role="region"
      aria-label="当前状态与下一步"
    >
      <div class="tps-head">
        <h2 class="tps-title">{{ trainingStateTitle }}</h2>
        <p
          v-if="defenseFlowRibbonVisible"
          class="tps-eyebrow muted"
        >
          {{ defenseFlowRibbonEyebrow }}
        </p>
      </div>
      <p class="tps-line">
        <span class="tps-k">当前环节</span>{{ trainingStatePhaseLine }}
      </p>
      <p v-if="primaryStatusNowLine" class="tps-line tps-now">
        <span class="tps-k">现在</span>{{ primaryStatusNowLine }}
      </p>
      <p v-if="primaryStatusAfterLine" class="tps-line tps-next">
        <span class="tps-k">接下来</span>{{ primaryStatusAfterLine }}
      </p>

      <p
        v-if="missionPrimaryActionHint"
        class="tps-mission-cta"
      >
        {{ missionPrimaryActionHint }}
      </p>

      <details
        v-if="trainingStateSidLine || trainingConfigSummaryLine"
        class="tps-mission-extras"
      >
        <summary>本次会话与本轮配置</summary>
        <p
          v-if="trainingStateSidLine"
          class="tps-line tps-sid-line tps-mission-extras__line"
          :class="{ 'tps-sid-line--quiet': !trainingFlowDebugMode }"
        >
          <span class="tps-k">{{ trainingFlowDebugMode ? '会话' : '编号' }}</span>
          <code v-if="trainingFlowDebugMode" class="tps-sid">{{ trainingStateSidLine }}</code>
          <span v-else class="tps-sid tps-sid--plain" :title="String(sessionId || '')">{{
            trainingStateSidLine
          }}</span>
        </p>
        <p
          v-if="trainingConfigSummaryLine"
          class="tps-line tps-config tps-mission-extras__line tps-mission-extras__config"
        >
          <span class="tps-k">本轮配置</span>{{ trainingConfigSummaryLine }}
        </p>
      </details>

      <div
        v-if="unfinishedResumePrompt && !sessionId"
        class="tps-mission-resume-cta"
      >
        <p class="tps-mission-resume-lead muted">
          检测到未结束的上次练习。你可继续上次的阶段与设置，或放弃后重新开一轮。
        </p>
        <div class="unfinished-session-resume__actions tps-resume-actions">
          <el-button
            type="primary"
            size="default"
            native-type="button"
            :aria-label="continueResumeButtonLabel"
            :disabled="!trainingAllowedActions.continueResume"
            @click="continueUnfinishedTraining"
          >
            {{ continueResumeButtonLabel }}
          </el-button>
          <el-button
            size="default"
            native-type="button"
            aria-label="放弃未完成的训练并重新开始"
            :disabled="!trainingAllowedActions.abandonResume"
            @click="abandonUnfinishedTraining"
          >
            放弃并重新开始
          </el-button>
        </div>
        <details class="tps-mission-extras tps-mission-extras--resume">
          <summary>查看上次练习详情</summary>
          <ul class="unfinished-session-resume__list">
            <li>
              <span class="usr-k">当前阶段：</span>{{ unfinishedResumePhaseDisplay }}
            </li>
            <li>
              <span class="usr-k">会话编号：</span
              ><code class="usr-sid">{{
                trainingSessionShortId(unfinishedResumePrompt.sessionId)
              }}</code>
            </li>
            <li>
              <span class="usr-k">评分模式：</span>{{ unfinishedResumeServerProfileLabel }}
            </li>
            <li>
              <span class="usr-k">课件模式：</span>{{ unfinishedResumeServerDmLabel }}
            </li>
            <li>
              <span class="usr-k">训练重点：</span>{{ unfinishedResumeServerFocusLabel }}
            </li>
            <li v-if="unfinishedResumePrompt && !unfinishedResumePrompt.hasSnapshot" class="muted usr-note">
              本机无完整页面缓存时，会尽量恢复以上设置；若曾进入问答，可能需重新选题或生成问题。
            </li>
          </ul>
          <p class="unfinished-session-resume__media-hint muted">
            继续后不会自动打开麦克风与摄像头，需要时请在系统或浏览器中重新授权。
          </p>
        </details>
      </div>
    </section>

    <div v-if="!sessionId" class="ui-l-desk-2 ui-l-desk-2--prep-cols training-workbench-desk training-workbench-desk--prep">
      <div class="training-desk__left training-desk__config">
    <div class="training-config-panel" aria-label="模式与课件配置">
    <div class="training-flow-shell">
    <section class="training-mode-panel training-mode-panel--nested">
      <h2 class="mode-section-title">训练模式</h2>
      <p class="mode-hint">开始训练前请选择本轮评分权重方案；开始后将锁定至本轮结束。</p>
      <p v-if="!sessionId" class="mode-draft-hint muted">
        <el-button link type="primary" size="small" @click="confirmResetTrainingPageToDefaults">
          清除预填并恢复默认
        </el-button>
        <span class="mode-draft-hint__sub">未开始训练时的模式与专项会记住；刷新或重新打开页面可自动恢复。</span>
      </p>
      <el-radio-group
        v-model="trainingScoringProfile"
        :disabled="!!sessionId"
        class="mode-radios"
        size="default"
      >
        <el-radio-button value="defense">答辩模式</el-radio-button>
        <el-radio-button value="interview">面试模式</el-radio-button>
      </el-radio-group>
      <p class="mode-selected">当前已选择：<strong>{{ trainingModeLabel }}</strong></p>
      <p class="mode-hint mode-hint--spaced">课件答辩方式（开始训练后锁定）</p>
      <p class="mode-deck-explainer">
        默认推荐<strong>有课件答辩</strong>，可使用<strong>内容匹配</strong>、<strong>猜页</strong>与<strong>基于课件的提问增强</strong>。
        若本轮侧重表达与仪态、不需要课件，请切换为<strong>无课件答辩</strong>（主界面将不展示课件上传区）。
      </p>
      <el-radio-group
        v-model="trainingDeckMode"
        :disabled="!!sessionId"
        class="mode-radios mode-radios--deck"
        size="default"
      >
        <el-radio-button value="with_deck">有课件答辩</el-radio-button>
        <el-radio-button value="none">无课件答辩</el-radio-button>
      </el-radio-group>
      <p class="mode-selected mode-selected--subtle">
        当前选择：<strong>{{ trainingDeckModeLabel }}</strong>
      </p>
    </section>
    <!-- 课件上传 + 调试匹配区（仅「有课件答辩」主路径展示） -->
    <div v-if="trainingDeckMode === 'with_deck'" class="ppt-match-section">
      <h3>{{ trainingFlowDebugMode ? '课件与匹配（调试）' : '课件' }}</h3>
      
      <!-- 上传 PPT -->
      <div class="ppt-upload" role="group" aria-label="选择课件并上传解析">
        <el-upload
          class="upload-demo"
          action="#"
          :auto-upload="false"
          :on-change="handleFileChange"
          accept=".pptx"
          :limit="1"
        >
          <el-button type="primary" native-type="button" aria-label="选择 .pptx 课件文件"
            >选择 PPT 文件</el-button>
          <template #tip>
            <div class="el-upload__tip">
              当前版本仅支持 .pptx 文件
            </div>
          </template>
        </el-upload>
        <el-button
          class="ppt-upload__submit"
          type="success"
          native-type="button"
          @click="uploadPPT"
          :disabled="!selectedFile || isUploadingPpt"
          :loading="isUploadingPpt"
          loading-text="上传中…"
        >
          上传 PPT
        </el-button>
      </div>

      <!-- PPT 解析状态（与「仅选文件 / 已上传」严格区分） -->
      <div class="ppt-info">
        <p class="ppt-status-line" :class="'ppt-status--' + pptUxStatus">{{ pptStatusUserMessage }}</p>
        <p v-if="trainingFlowDebugMode && displayPptId" class="ppt-debug-id">PPT ID：{{ displayPptId }}</p>
        <template v-if="pptPagesForUi.length && trainingFlowDebugMode">
          <h4>页面列表</h4>
          <el-select v-model="selectedPageIndex" placeholder="选择页面">
            <el-option
              v-for="page in pptPagesForUi"
              :key="page.page_index"
              :label="`${page.page_index} - ${page.title}`"
              :value="page.page_index"
            />
          </el-select>
        </template>
        <p
          v-if="trainingFlowDebugMode && displayPptId && !hasUploadedPptReady"
          class="ppt-id-only-hint"
        >
          当前仅有课件编号、未验证到本地解析结构；请重新上传 PPT，或确认服务端仍保留该课件。
        </p>
      </div>
      
      <!-- 匹配测试：手动选页 / 自动猜页（调试） -->
      <div v-if="hasPptContext && trainingFlowDebugMode" class="match-test">
        <h4>匹配模式</h4>
        <el-radio-group v-model="pptMatchMode" class="ppt-match-mode">
          <el-radio-button value="manual">手动匹配</el-radio-button>
          <el-radio-button value="auto">自动猜页</el-radio-button>
        </el-radio-group>

        <template v-if="pptMatchMode === 'manual'">
          <h4 class="match-subtitle">讲解文本（对所选页）</h4>
          <el-input
            type="textarea"
            v-model="spokenText"
            :rows="4"
            placeholder="请输入本次讲解的文本"
          />
          <el-button type="primary" @click="testMatch" :disabled="!selectedPageIndex || !spokenText">
            测试匹配度
          </el-button>
        </template>

        <template v-else>
          <p class="auto-guess-hint">仅根据口述文本猜测最可能页码（规则：标题 / 关键词 / 大纲命中），不依赖视觉翻页。</p>
          <h4 class="match-subtitle">口述 / 讲解文本</h4>
          <el-input
            type="textarea"
            v-model="spokenText"
            :rows="4"
            placeholder="粘贴或输入当前讲解内容，用于猜页"
          />
          <el-button type="primary" @click="guessCurrentPage" :disabled="!String(spokenText || '').trim()">
            猜当前页
          </el-button>
        </template>
      </div>

      <!-- 自动猜页结果（调试） -->
      <div
        v-if="trainingFlowDebugMode && pptMatchMode === 'auto' && autoGuessResult"
        class="match-result auto-guess-result"
      >
        <h4>猜页结果</h4>
        <div v-if="autoGuessShowLowMatchTip" class="auto-guess-low-match">
          未找到明显匹配页，请补充更具体的讲解文本
        </div>
        <div class="result-item">
          <strong>最佳页码：</strong>{{ autoGuessBestPageDisplay }}
        </div>
        <div class="result-item">
          <strong>标题：</strong>{{ autoGuessBestTitleDisplay }}
        </div>
        <div class="result-item">
          <strong>匹配分：</strong>{{ autoGuessResult.best_match_score }}
        </div>
        <div class="result-item">
          <strong>置信度：</strong>{{ autoGuessResult.confidence }}
        </div>
        <div v-if="autoGuessTopCandidates.length" class="result-item top-candidates">
          <strong>候选页（Top）：</strong>
          <ul>
            <li v-for="(c, i) in autoGuessTopCandidates" :key="i">
              第 {{ c.page_index }} 页「{{ c.title }}」— 分 {{ c.match_score }}
              <span v-if="c.title_hit" class="tag-hit">标题</span>
              <span v-if="c.outline_hit" class="tag-hit">大纲</span>
              <span v-if="c.keyword_coverage > 0" class="tag-hit">关键词覆盖 {{ c.keyword_coverage }}</span>
            </li>
          </ul>
        </div>
      </div>
      
      <!-- 匹配结果（手动模式，调试） -->
      <div v-if="trainingFlowDebugMode && pptMatchMode === 'manual' && matchResult" class="match-result">
        <h4>匹配结果</h4>
        <div class="result-item">
          <strong>匹配分数：</strong>{{ matchResult.match_score }}
        </div>
        <div class="result-item">
          <strong>关键词覆盖率：</strong>{{ matchResult.keyword_coverage }}
        </div>
        <div class="result-item">
          <strong>匹配的关键词：</strong>{{ matchResult.matched_keywords.join(', ') }}
        </div>
        <div class="result-item">
          <strong>未匹配的关键词：</strong>{{ matchResult.missing_keywords.join(', ') }}
        </div>
        <div class="result-item">
          <strong>评价：</strong>{{ matchResult.comment }}
        </div>
        <!-- PPT 匹配成功提示 -->
        <div v-if="lastPptMatchResult" class="match-success">
          当前已保存本次 PPT 匹配结果
        </div>
      </div>
      
      <!-- 调试信息 -->
      <div v-if="trainingFlowDebugMode && lastPptMatchResult" class="debug-info">
        <h4>调试信息</h4>
        <div class="debug-item">
          <strong>是否存在 lastPptMatchResult：</strong>{{ lastPptMatchResult ? '是' : '否' }}
        </div>
        <div class="debug-item" v-if="lastPptMatchResult">
          <strong>page_index：</strong>{{ lastPptMatchResult.page_index }}
        </div>
        <div class="debug-item" v-if="lastPptMatchResult">
          <strong>match_score：</strong>{{ lastPptMatchResult.match_score }}
        </div>
        <div class="debug-item" v-if="lastPptMatchResult">
          <strong>title：</strong>{{ lastPptMatchResult.title }}
        </div>
      </div>
    </div>

    <div v-else class="ppt-match-section ppt-match-section--without-deck">
      <h3>课件</h3>
      <p class="without-deck-lead">
        当前为<strong>无课件答辩</strong>训练：本轮<strong>不启用</strong>内容匹配、自动猜页和基于课件的提问增强。
      </p>
      <p class="without-deck-sub">
        需要上述能力时，请在上方切换为「有课件答辩」，随后在课件区上传并解析课件。
      </p>
    </div>

    <!-- 备用题库 / 批量出题：仅训练前或调试模式 -->
    <div
      v-if="trainingDeckMode === 'with_deck' && hasPptContext && showMockGenerateSection"
      class="mock-qa-generate-section"
    >
      <h3>{{ sessionId ? '备用题库（调试）' : '模拟答辩问题生成' }}</h3>
      <p class="mock-qa-tip">基于当前已上传 PPT 的标题、大纲、关键词与正文摘要自动生成若干评审式问题（规则版）。</p>
      <el-button
        type="primary"
        @click="generateMockQuestionsBatch()"
        :disabled="!hasPptContext || isGeneratingMockBatch"
        :loading="isGeneratingMockBatch"
        loading-text="生成中…"
      >
        重新生成问题列表
      </el-button>
      <p v-if="mockQuestionsList.length && !trainingFlowDebugMode" class="mock-bank-toggle-line">
        <el-button
          v-if="!mockQuestionBankExpanded"
          link
          type="primary"
          @click="mockQuestionBankExpanded = true"
        >
          展开备用题库 / 换一题
        </el-button>
        <el-button
          v-else
          link
          type="primary"
          @click="mockQuestionBankExpanded = false"
        >
          收起备用题库
        </el-button>
        <span class="mock-bank-toggle-hint">（开启「调试流程」时列表默认展开）</span>
      </p>
      <div
        v-if="mockQuestionsList.length && (trainingFlowDebugMode || mockQuestionBankExpanded)"
        class="mock-qa-list"
      >
        <h4>备用题库（调试 / 换题）</h4>
        <p class="mock-select-hint">
          正式流程已由系统选定首题作为老师当前问题；此处可改选其他题目或用于排障。
        </p>
        <div
          v-if="selectedMockQuestionIndex >= 0 && qaRoundSource === 'auto_generated'"
          class="mock-q-picked-banner"
          role="status"
        >
          当前使用第 {{ selectedMockQuestionIndex + 1 }} 题作为老师当前问题。
        </div>
        <ol>
          <li
            v-for="(item, idx) in mockQuestionsList"
            :key="idx"
            :class="['mock-qa-row', { 'mock-qa-row--selected': selectedMockQuestionIndex === idx }]"
          >
            <span class="mq-source">[{{ item.source }}]</span>
            <span v-if="item.provider_label" class="mq-source mq-provider">{{ item.provider_label }}</span>
            {{ displayMockQuestionText(item) }}
            <el-button
              size="small"
              type="primary"
              link
              class="mock-pick-btn"
              :disabled="!displayMockQuestionText(item)"
              @click.stop="selectMockQuestionForQa(idx)"
            >
              {{ selectedMockQuestionIndex === idx ? '当前题' : '选为当前题' }}
            </el-button>
          </li>
        </ol>
      </div>
    </div>

    </div>
    </div>
      </div>
      <div class="training-desk__right training-desk__ops">
    <aside class="training-ops-panel" aria-label="训练前检查与控制">
    <div class="training-ops-stack">
    <!-- 错误提示（与结果/历史/报告页告警风格一致） -->
    <el-alert
      v-if="errorMessage"
      class="training-page-error"
      type="error"
      :closable="false"
      show-icon
      :title="PAGE_ERROR_ALERT_TITLE.training"
      role="alert"
    >
      <p class="training-page-error__body">{{ errorMessage }}</p>
      <div class="training-page-error__actions">
        <el-button type="primary" size="small" @click="clearTrainingPageError">我知道了</el-button>
        <el-button size="small" @click="goHomeFromTrainingPage">返回首页</el-button>
      </div>
    </el-alert>
    
    <!-- 停止训练过程状态提示 -->
    <div v-if="isAnalyzingVision" class="status-message info">
      录像已结束，正在分析视频…
    </div>
    <div v-else-if="isSubmittingSession" class="status-message info">
      正在提交训练结果…
    </div>

    <!-- 开始训练按钮不可点时的原因 -->
    <div v-if="startButtonDisabled && startDisabledReason" class="status-message info">
      {{ startDisabledReason }}
    </div>
    
    <div v-if="stopSuccess" class="status-message success">
      训练结果提交成功，正在跳转结果页…
    </div>

    <p
      v-if="missionPrimaryActionHint && !unfinishedResumePrompt"
      class="training-ops-next-hint"
      role="status"
    >
      {{ missionPrimaryActionHint }}
    </p>

    <section v-if="!sessionId && !unfinishedResumePrompt" class="preflight-panel">
      <h3 class="preflight-title">训练前准备检查</h3>
      <p v-if="preflightLoading" class="preflight-loading-hint muted" role="status">
        {{ PAGE_LOADING.trainingPreflight }}
      </p>
      <p class="preflight-intro">
        <template v-if="trainingDeckMode === 'with_deck'">
          请授权麦克风与摄像头，并确认左侧课件已上传解析。外接分析环境需网络稳定。
        </template>
        <template v-else>
          请授权麦克风与摄像头。无课件模式下课件项为提示，不阻塞开始。
        </template>
      </p>
      <div v-if="preflightWarningBanner" class="preflight-warn-banner" role="status">
        {{ preflightWarningBanner }}
      </div>
      <ul class="preflight-list" aria-label="准备检查项">
        <li
          v-for="row in preflightRows"
          :key="row.id"
          :class="['preflight-row', 'preflight-row--' + row.status]"
        >
          <span class="preflight-badge">{{ preflightStatusLabel(row.status) }}</span>
          <div class="preflight-row-body">
            <span class="preflight-label">{{ row.label }}</span>
            <span class="preflight-msg">{{ row.message }}</span>
          </div>
        </li>
      </ul>
      <div class="preflight-actions">
        <el-button
          type="primary"
          plain
          :loading="preflightLoading"
          loading-text="检查中…"
          @click="runPreflightChecks({ fromButton: true })"
        >
          重新检查
        </el-button>
      </div>
      <details v-if="trainingFlowDebugMode && preflightDebugText" class="preflight-debug">
        <summary>自检详情（调试）</summary>
        <pre class="preflight-debug-pre">{{ preflightDebugText }}</pre>
      </details>
    </section>

    <section
      v-if="!sessionId"
      id="training-control-dock"
      class="training-controls-dock ui-controls-dock training-controls-dock--emphasis training-controls-dock--prep-nested"
      aria-label="训练控制"
    >
      <h2 class="ui-controls-dock__title">训练控制</h2>
      <p class="ui-controls-dock__hint muted">
        自检通过且课件（若需要）就绪后，点击开始训练；训练中可随时停止并提交结果。
      </p>
      <div class="ui-controls-dock__buttons">
        <el-button
          type="primary"
          size="large"
          native-type="button"
          aria-label="开始训练"
          :disabled="startButtonDisabled"
          :loading="loading"
          loading-text="启动中…"
          class="training-primary-start-btn"
          @click="startTraining"
        >
          开始训练
        </el-button>
        <el-button
          type="danger"
          size="large"
          plain
          native-type="button"
          aria-label="停止训练并提交结果"
          :disabled="!trainingAllowedActions.stop"
          :loading="isStopping"
          loading-text="停止中…"
          @click="stopSession"
        >
          停止训练
        </el-button>
      </div>
    </section>
    </div>
    </aside>
      </div>
    </div>

    <div v-if="!sessionId" class="training-prep-low training-prep-low--sink no-print">
      <p
        v-if="!unfinishedResumePrompt && deckPreflightCapabilityHint"
        class="preflight-capability-hint"
        :class="{ 'training-when-demo-soft': demoModeUi.active }"
        role="note"
      >
        {{ deckPreflightCapabilityHint }}
      </p>
      <details v-if="apiResult && trainingFlowDebugMode" class="training-api-debug">
        <summary>API 响应（调试）</summary>
        <div class="api-result api-result--in-details">
          <pre>{{ apiResult }}</pre>
        </div>
      </details>
    </div>
    </div>

    <div v-if="sessionId" class="training-in-session-outer" :class="'training-in-session--phase-' + String(sessionPhase)">
      <div class="training-in-session__main">
        <div
          class="training-session-hero training-session-hero--v2 ui-surface"
          :class="[
            'training-session-hero--' + String(sessionPhase),
            { 'training-session-hero--demo': trainingFlowDebugMode },
          ]"
          role="region"
          aria-label="本阶段与当前任务"
        >
          <p class="training-session-hero__eyebrow no-print">本阶段</p>
          <h2 v-if="!trainingFlowDebugMode" class="training-session-hero__title">{{ defenseStageHeadline }}</h2>
          <h2 v-else class="training-session-hero__title">当前：{{ sessionPhaseLabel }}</h2>
          <p v-if="!trainingFlowDebugMode" class="training-session-hero__task">{{ trainingStateNextStepLine }}</p>
          <p v-else class="training-session-hero__task muted">已开启调试验证；请按主流程与下方单步区操作。</p>
        </div>

        <div
          class="session-info training-session-brief"
          :class="[{ 'session-info--main': !trainingFlowDebugMode }, 'ui-surface', 'ui-surface--subtle']"
        >
          <p v-if="trainingFlowDebugMode" class="session-brief__line">会话编号：{{ sessionId }}</p>
          <p v-else class="session-brief__line">当前：<strong>{{ defenseFlowRibbonTitle || '会话进行中' }}</strong></p>
          <p v-if="sessionPhase === 'lecture' && isLectureRecordingAudio" class="session-brief__line training-session-brief--rec">
            讲解录音中…
          </p>
          <p v-if="isVideoRecording" class="session-brief__line training-session-brief--rec">答辩录像中…</p>
        </div>

        <div class="video-preview-box training-primary-video training-session-stage-video" :class="{ 'video-preview-box--main': !trainingFlowDebugMode }">
          <h3>{{ trainingFlowDebugMode ? '摄像头预览（调试）' : '主画面：答辩录像' }}</h3>
          <video ref="cameraPreviewRef" class="camera-preview" autoplay muted playsinline></video>
          <p v-if="videoMimeType && trainingFlowDebugMode"><strong>当前视频 MIME：</strong>{{ videoMimeType }}</p>
          <p class="video-tip">{{ trainingFlowDebugMode ? '开始训练后自动开启，结束训练后自动停止并上传分析。' : '用于仪态与表达分析；请保持面部在画面中。' }}</p>
        </div>

        <div
          class="session-phase-banner training-session-mission"
          :class="[{ 'session-phase-banner--main': !trainingFlowDebugMode }]"
          role="region"
          aria-label="阶段内操作与说明"
        >
          <p class="session-mission-eyebrow no-print">阶段内操作</p>
          <div class="session-phase-actions session-mission__actions">
            <el-button
              v-if="sessionPhase === 'lecture' && !trainingFlowDebugMode"
              type="primary"
              size="large"
              native-type="button"
              aria-label="结束讲解阶段并进入答辩问答"
              :disabled="isGeneratingMockBatch"
              :loading="isGeneratingMockBatch"
              loading-text="切换中…"
              @click="finishLectureEnterQa"
            >
              结束讲解，进入答辩问答
            </el-button>
            <el-checkbox
              v-if="!demoModeUi.active"
              v-model="trainingFlowDebugMode"
              size="small"
              class="debug-flow-checkbox"
            >
              需要排查时：显示调试验证与单步项
            </el-checkbox>
          </div>
          <details v-if="!trainingFlowDebugMode" class="training-phase-hint-details no-print">
            <summary>查看本阶段操作说明</summary>
            <p v-if="sessionPhase === 'lecture'" class="phase-hint">开始训练后会自动开始录像与讲解录音。完成本轮陈述后，再点击「结束讲解，进入答辩问答」，与真实答辩中「讲完再答问」的顺序一致。</p>
            <p
              v-else-if="sessionPhase === 'qa' && !isGeneratingFollowup && qaRoundSource === 'followup_generated'"
              class="phase-hint"
            >这是在主问题与评估之后追加的「追问」。请用语音或文本把要点说清，再提交评估，不必刻意抢时长。</p>
            <p
              v-else-if="sessionPhase === 'qa' && !isGeneratingFollowup"
              class="phase-hint"
            >先看清「老师提问」题干，再优先用语音完成作答，随后提交评估；与下方「答辩问答」区配合即可。</p>
            <p v-if="isGeneratingFollowup" class="phase-hint phase-hint--pending">正根据你上一题的表现准备一道追问，请稍候；生成后请像现场答辩一样继续语音或文本作答。</p>
          </details>
        </div>

        <div v-if="visionAnalysis && trainingFlowDebugMode" class="audio-analysis-box training-in-session-aux">
          <h3>视觉分析结果（调试）</h3>
          <p class="video-tip">当前视觉分析为第一版规则法，摄像头高度、光照和眼镜反光会影响结果</p>
          <p v-if="visionAnalysis.vision_valid === false" class="audio-invalid-hint">
            本次视觉分析未成功：{{ visionAnalysis.vision_message || '有效检测帧过少，请调整机位、光照或靠近镜头后重试' }}
          </p>
          <template v-if="visionAnalysis.vision_valid !== false">
            <p><strong>正视前方比例：</strong>{{ visionAnalysis.forward_gaze_ratio ?? '-' }}</p>
            <p><strong>低头率：</strong>{{ visionAnalysis.downward_head_ratio ?? '-' }}</p>
            <p><strong>姿态稳定度：</strong>{{ visionAnalysis.posture_stability ?? '-' }}</p>
          </template>
          <template v-else>
            <p><strong>正视前方比例：</strong>-</p>
            <p><strong>低头率：</strong>-</p>
            <p><strong>姿态稳定度：</strong>-</p>
          </template>
        </div>

        <div v-if="audioAnalysis && trainingFlowDebugMode" class="audio-analysis-box training-in-session-aux">
          <h3>音频分析结果（调试）</h3>
          <p v-if="recordingMimeType"><strong>当前录音 MIME：</strong>{{ recordingMimeType }}</p>
          <p v-if="'audio_valid' in audioAnalysis">
            <strong>当前音频分析是否有效：</strong>{{ audioAnalysis.audio_valid === false ? '否' : '是' }}
          </p>
          <p v-if="audioAnalysis.audio_message"><strong>提示：</strong>{{ audioAnalysis.audio_message }}</p>
          <p v-if="audioAnalysis.audio_valid === false" class="audio-invalid-hint">
            {{ audioAnalysis.audio_message || '未检测到有效语音，请靠近麦克风后重试' }}
          </p>
          <p>
            <strong>转写文本：</strong>
            {{ audioAnalysis.audio_valid === false ? '-' : (audioAnalysis.transcript || '-') }}
          </p>
          <p><strong>语速：</strong>{{ audioAnalysis.speech_rate ?? '-' }}</p>
          <p><strong>停顿次数：</strong>{{ audioAnalysis.pause_count ?? '-' }}</p>
          <p><strong>平均停顿时长：</strong>{{ audioAnalysis.avg_pause_sec ?? '-' }}</p>
          <p><strong>口头禅次数：</strong>{{ audioAnalysis.filler_count ?? '-' }}</p>
        </div>

        <div v-if="trainingFlowDebugMode" class="metrics-form training-in-session-aux">
          <h3>训练指标（调试）</h3>
          <div class="form-row">
            <el-input-number v-model="metrics.speech_rate" label="语速" :min="50" :max="500" :step="1" />
            <el-input-number v-model="metrics.pause_count" label="停顿次数" :min="0" :max="100" :step="1" />
            <el-input-number v-model="metrics.avg_pause_sec" label="平均停顿时长" :min="0" :max="5" :step="0.1" />
          </div>
          <div class="form-row">
            <el-input-number v-model="metrics.filler_count" label="口头禅次数" :min="0" :max="50" :step="1" />
            <el-input-number v-model="metrics.forward_gaze_ratio" label="正视前方比例" :min="0" :max="1" :step="0.01" />
            <el-input-number v-model="metrics.downward_head_ratio" label="低头率" :min="0" :max="1" :step="0.01" />
            <el-input-number v-model="metrics.posture_stability" label="姿态稳定度" :min="0" :max="1" :step="0.01" />
          </div>
        </div>
      </div>

      <aside class="training-in-session__rail" aria-label="训练侧栏与主操作">
        <div class="training-rail-card training-rail-card--head">
          <h3 class="training-rail__title">训练中 · 控制</h3>
          <p class="training-rail__line muted no-print">模式 <strong class="training-rail__strong">{{ trainingModeLabel }}</strong> ·
            {{ trainingDeckModeLabel }}
          </p>
        </div>
        <div v-if="currentQaQuestion" class="training-rail-question ui-surface" role="status">
          <p class="training-rail-question__k">老师当前问</p>
          <p class="training-rail-question__body">{{ currentQaQuestion }}</p>
        </div>
        <section
          class="training-controls-dock training-controls-dock--rail ui-surface ui-controls-dock training-controls-dock--emphasis"
          aria-label="训练控制"
        >
          <h2 class="ui-controls-dock__title">训练控制</h2>
          <p class="ui-controls-dock__hint muted">{{ trainingStateNextStepLine }}</p>
          <div class="ui-controls-dock__buttons">
            <el-button
              type="primary"
              size="large"
              native-type="button"
              aria-label="开始训练"
              :disabled="startButtonDisabled"
              :loading="loading"
              loading-text="启动中…"
              class="training-primary-start-btn"
              @click="startTraining"
            >
              开始训练
            </el-button>
            <el-button
              type="danger"
              size="large"
              plain
              native-type="button"
              aria-label="停止训练并提交结果"
              :disabled="!trainingAllowedActions.stop"
              :loading="isStopping"
              loading-text="停止中…"
              @click="stopSession"
            >
              停止训练
            </el-button>
          </div>
        </section>
        <p class="training-rail-foot muted no-print">侧栏在桌面端会随屏固定；小屏时优先出现便于操作。</p>
      </aside>
    <!-- 答辩问答区：主流程仅展示与作答强相关区块 -->
    <div v-if="showQaSection && sessionId" class="qa-section training-qa--session-run" :class="{ 'qa-section--main': sessionId && !trainingFlowDebugMode }">
      <h3>{{ trainingFlowDebugMode ? '模拟答辩问答（调试）' : '答辩问答' }}</h3>
      <p v-if="qaPhaseAutoQuestionTip" class="qa-phase-auto-tip" role="status">{{ qaPhaseAutoQuestionTip }}</p>
      <p v-if="currentQaQuestion && trainingFlowDebugMode" class="qa-current-source">
        本轮问答通道：<strong>{{ qaChannelLabel }}</strong>
      </p>
      <p v-if="qaAutoFollowupHint" class="qa-auto-followup-banner" role="status">
        {{ qaAutoFollowupHint }}
      </p>
      <p
        v-if="trainingFlowDebugMode && lastQuestionGenerationContext && (qaRoundSource === 'auto_generated' || qaRoundSource === 'manual')"
        class="qa-followup-provider-debug"
      >
        <span class="muted-label">本轮首问来源：</span>{{ questionProviderDebugLine }}
      </p>
      <p
        v-if="trainingFlowDebugMode && lastFollowupGenerationContext && qaRoundSource === 'followup_generated'"
        class="qa-followup-provider-debug"
      >
        <span class="muted-label">本轮追问来源：</span>{{ followupProviderDebugLine }}
      </p>
      <div
        v-if="selectedFollowupIndex >= 0 && qaRoundSource === 'followup_generated'"
        class="fu-picked-banner"
        role="status"
      >
        老师追问已就绪，请使用语音作答，结束后将自动评估。
      </div>
      <p v-if="trainingFlowDebugMode" class="qa-tip">
        答辩默认：<strong>语音作答</strong>（与讲解复用同一套转写链路，不写回讲解主录音分析）。
      </p>
      <div v-if="trainingFlowDebugMode" class="qa-actions">
        <el-button type="primary" @click="generateQaQuestion" :disabled="!pptInfo || !selectedPageIndex">
          生成问题（单页调试）
        </el-button>
      </div>
      <div v-if="currentQaQuestion" class="qa-question">
        <p>
          <strong>{{ teacherQuestionLabel }}：</strong>{{ currentQaQuestion }}
        </p>
        <p v-if="currentQaExpectedKeywords.length">
          <strong>参考关键词：</strong>{{ currentQaExpectedKeywords.join('、') }}
        </p>
      </div>
      <div v-if="currentQaQuestion" class="qa-voice-answer">
        <p class="qa-voice-title">{{ qaVoiceAnswerTitle }}</p>
        <p v-if="isQaAnswerRecording" class="qa-recording-hint">正在录制你的回答…</p>
        <p v-if="isAnalyzingQaAudio && !qaAnswerEvaluatePending" class="qa-recording-hint">
          正在转写你的回答…
        </p>
        <p v-if="qaAnswerEvaluatePending" class="qa-recording-hint">正在评估回答…</p>
        <div class="qa-voice-actions">
          <el-button
            type="primary"
            @click="startQaAnswerRecording"
            :disabled="
              !currentQaQuestion || isQaAnswerRecording || isAnalyzingQaAudio || qaAnswerEvaluatePending
            "
          >
            {{ trainingFlowDebugMode ? '开始语音回答' : '请开始语音回答' }}
          </el-button>
          <el-button
            type="warning"
            @click="stopQaVoiceAnswer"
            :disabled="!isQaAnswerRecording || isAnalyzingQaAudio || qaAnswerEvaluatePending"
          >
            结束语音回答
          </el-button>
        </div>
        <p v-if="qaAnswerTranscript && !isAnalyzingQaAudio" class="qa-transcript-preview">
          <span class="muted-label">转写预览：</span>{{ qaAnswerTranscript }}
        </p>
      </div>
      <div v-if="currentQaQuestion && trainingFlowDebugMode" class="qa-text-fallback">
        <el-button
          link
          type="primary"
          class="qa-text-fallback-toggle"
          @click="qaTextFallbackExpanded = !qaTextFallbackExpanded"
        >
          {{ qaTextFallbackExpanded ? '收起' : '展开' }}文本兜底 / 调试输入
        </el-button>
        <div v-show="qaTextFallbackExpanded" class="qa-text-fallback-body">
          <el-input
            type="textarea"
            v-model="qaAnswerText"
            :rows="4"
            placeholder="手动输入或修改回答后，点击下方评估"
            @focus="onQaTextFallbackFocus"
          />
          <div class="qa-actions">
            <el-button
              type="success"
              @click="evaluateQaAnswer({ inputMode: 'text' })"
              :disabled="
                !currentQaQuestion ||
                !qaAnswerText ||
                isAnalyzingQaAudio ||
                qaAnswerEvaluatePending ||
                isQaAnswerRecording
              "
            >
              评估回答（文本）
            </el-button>
          </div>
        </div>
      </div>
      <div v-if="qaEvaluationResult" class="qa-result">
        <p><strong>是否切题：</strong>{{ qaEvaluationResult.is_relevant ? '是' : '否' }}</p>
        <p><strong>覆盖率：</strong>{{ qaEvaluationResult.coverage_score }}</p>
        <p><strong>命中关键词：</strong>{{ (qaEvaluationResult.hit_keywords || []).join('、') }}</p>
        <p><strong>缺失关键词：</strong>{{ (qaEvaluationResult.missing_keywords || []).join('、') }}</p>
        <p><strong>评价：</strong>{{ qaEvaluationResult.comment }}</p>
        <div v-if="showGenerateFollowupButton" class="qa-followup-actions">
          <el-button
            type="warning"
            :loading="isGeneratingFollowup"
            loading-text="生成中…"
            @click="generateFollowupQuestions"
          >
            生成追问
          </el-button>
          <span class="qa-followup-hint">
            若自动追问不足，可在此手动再生成（最多 3 条；一般无需操作）。首轮后通常已自动生成追问。
          </span>
        </div>
      </div>
      <div
        v-if="followupSectionVisible && (showQaFollowupPickerList || !followupQuestions.length)"
        class="qa-followup-list"
      >
        <p v-if="!followupQuestions.length" class="fu-empty-hint">
          本轮未生成明显追问，可先修改回答后再试。
        </p>
        <template v-else>
        <h4>追问候选（可选一条继续作答）</h4>
        <p v-if="followupTaxonomyLabel" class="fu-session-source muted" role="note">
          追问来源：{{ followupTaxonomyLabel }}
        </p>
        <p
          v-if="selectedFollowupIndex >= 0 && qaRoundSource === 'followup_generated'"
          class="fu-picked-inline"
          role="status"
        >
          已选为当前追问
        </p>
        <ol>
          <li
            v-for="(fu, fidx) in followupQuestions"
            :key="fidx"
            :class="['qa-followup-row', { 'qa-followup-row--picked': selectedFollowupIndex === fidx }]"
          >
            <div class="fu-main-row">
              <span class="fu-q">{{ fu.question }}</span>
              <el-button
                size="small"
                type="primary"
                link
                class="mock-pick-btn"
                @click.stop="selectFollowupQuestion(fidx)"
              >
                {{ selectedFollowupIndex === fidx ? '当前追问' : '选为当前追问' }}
              </el-button>
            </div>
            <div v-if="followupDirectionLabel(fu.source)" class="fu-direction">
              {{ followupDirectionLabel(fu.source) }}
            </div>
            <p v-if="fu.reason" class="fu-reason">{{ fu.reason }}</p>
          </li>
        </ol>
        </template>
      </div>
    </div>
    </div>
    
    <div class="ui-sink training-aux-below no-print">
    <el-collapse
      v-if="supplementalPanelVisible"
      v-model="trainingSupplementalCollapse"
      class="ui-aux-collapse ui-aux-collapse--low training-supplemental-hints no-print"
    >
      <el-collapse-item name="sup" title="补充说明：演示、网络、近期训练与设备提示（可选）">
        <el-alert
          v-if="demoModeUi.active"
          class="training-demo-mode-banner no-print"
          type="success"
          :closable="false"
          show-icon
          title="演示模式"
        >
          <p class="training-demo-mode-banner__body muted">
            本页处于便于讲解的展示状态。与训练主流程无关的细节可按需在此展开后查看。
          </p>
          <div class="training-demo-mode-banner__actions">
            <el-button size="small" type="primary" plain @click="exitTrainingDemoMode">退出演示模式</el-button>
            <el-button size="small" @click="router.push('/home')">返回首页</el-button>
          </div>
        </el-alert>
        <p v-if="demoModeUi.active && demoModeUi.presetActive" class="training-demo-preset-note muted">
          已应用演示用界面预设，不影响训练与评分结果。
        </p>

        <el-alert
          v-if="resumeSessionCheckFailed && !sessionId"
          class="training-resume-fail-alert"
          type="warning"
          :closable="true"
          show-icon
          title="暂时无法同步上次进度"
          @close="resumeSessionCheckFailed = false"
        >
          <p class="training-resume-fail-alert__body">
            当前网络不稳定，系统无法判断是否有未提交的训练。你可按下方引导开始新练习，或稍后再试、刷新本页。
          </p>
        </el-alert>

        <div
          v-if="resumeMediaHintVisible && sessionId"
          class="tps-resume-inline"
          role="status"
        >
          <p class="tps-resume-inline__text">
            已回到本轮练习。若继续用语音，请在浏览器中重新允许麦克风与摄像头。
          </p>
          <el-button link type="primary" size="small" @click="resumeMediaHintVisible = false"
            >知道了</el-button
          >
        </div>

        <div
          v-if="!sessionId && !unfinishedResumePrompt && showRecentValidTrainingReminder"
          class="tps-rvr-in-card tps-rvr--supplemental"
        >
          <h3 class="tps-block-title">近期有效训练</h3>
          <template v-if="validTrainingOverviewReady">
            <p v-if="recentValidReminderExplicitNote" class="tps-rvr-note muted">
              专项由上一轮或历史页带入。以下为近期摘要，供对照，不会自动改你的选择。
            </p>
            <p class="tps-rvr-brief muted">
              最近一次：{{ recentValidLatestTime }} · 建议方向：<strong>{{
                recentValidSuggestLabel
              }}</strong>
            </p>
            <div class="recent-valid-training-reminder__actions rvr-actions-row">
              <el-button type="primary" plain size="small" @click="resumeLastValidTrainingConfig">
                继续上次训练方式
              </el-button>
              <el-button
                v-if="applyRecommendedDirectionVisible"
                type="success"
                plain
                size="small"
                @click="applyRecommendedFocusConfig"
              >
                按建议方向训练
              </el-button>
            </div>
          </template>
          <p v-else class="tps-rvr-brief muted">{{ recentValidReminderEmptyText }}</p>
        </div>
      </el-collapse-item>
    </el-collapse>

    <template v-if="demoModeUi.active">
      <el-collapse
        v-if="trainingRuntimeChainLine || trainingBoardLine || showAscendRuntimeCollapse"
        v-model="trainingDemoRuntimeCollapse"
        class="ui-aux-collapse ui-aux-collapse--low training-demo-runtime-collapse no-print"
      >
        <el-collapse-item
          v-if="trainingRuntimeChainLine || trainingBoardLine"
          title="运行与环境（需了解时展开，可选）"
          name="chain-summary"
        >
          <p v-if="trainingRuntimeChainLine" class="training-runtime-chain muted">
            {{ trainingRuntimeChainLine }}
          </p>
          <p v-if="trainingBoardLine" class="training-board-participation muted">
            {{ trainingBoardLine }}
          </p>
        </el-collapse-item>
        <el-collapse-item
          v-if="showAscendRuntimeCollapse"
          title="边缘分析服务（需联系技术支持或排障时展开）"
          name="board-env"
        >
          <p class="training-ascend-runtime-hint muted">
            以下原始信息供核对连接或环境版本。日常完成训练时不必关注。
            优先展示 <code>ascend_service_runtime</code>；无对应字段时回退为
            <code>ascend_health_check.response</code>。
          </p>
          <pre class="training-ascend-runtime-pre">{{ ascendRuntimeEvidenceText }}</pre>
        </el-collapse-item>
      </el-collapse>
    </template>
    <el-collapse
      v-else-if="trainingRuntimeChainLine"
      v-model="trainingAuxCollapse"
      class="ui-aux-collapse ui-aux-collapse--low training-aux-collapse no-print"
    >
      <el-collapse-item title="运行与环境（需了解时展开，可选）" name="chain">
        <p class="training-runtime-chain muted">{{ trainingRuntimeChainLine }}</p>
        <p v-if="trainingBoardLine" class="training-board-participation muted">{{ trainingBoardLine }}</p>
        <el-collapse
          v-if="showAscendRuntimeCollapse"
          v-model="trainingChainNestedEnvCollapse"
          class="training-chain-nested-board-env"
        >
          <el-collapse-item title="边缘分析服务（需联系技术支持或排障时展开）" name="board-env">
            <p class="training-ascend-runtime-hint muted">
              供核对 <code>temp_dir</code>、<code>platform_system</code> 等。无顶层
              <code>ascend_service_runtime</code> 时，下方为 <code>ascend_health_check.response</code> 回退。
            </p>
            <pre class="training-ascend-runtime-pre">{{ ascendRuntimeEvidenceText }}</pre>
          </el-collapse-item>
        </el-collapse>
      </el-collapse-item>
    </el-collapse>

    <el-collapse
      v-model="trainingTopAuxHintsCollapse"
      class="ui-aux-collapse ui-aux-collapse--low training-aux-hints-collapse no-print"
    >
      <el-collapse-item title="辅助说明与更多详情" name="aux">
        <el-alert
          v-if="firstTimeTrainingHintVisible"
          class="training-first-hint"
          type="info"
          :closable="true"
          show-icon
          title="第一次使用可先看这些"
          @close="dismissFirstTrainingHint"
        >
          <ul class="training-first-hint-list">
            <li>在「训练模式」里选择<strong>有课件答辩</strong>或<strong>无课件答辩</strong>，两种都能完整练一轮。</li>
            <li>自检通过后点「开始训练」；结束一轮后会生成<strong>分数与建议</strong>，首页与历史可继续查看。</li>
          </ul>
          <p class="training-first-hint-foot muted">关闭后不再显示；有过训练记录时默认不弹出。</p>
        </el-alert>
        <p v-if="sessionDiscardedBanner" class="session-discarded-banner" role="status">
          {{ sessionDiscardedBanner }}
        </p>
        <section
          v-if="validTrainingOverviewReady && !sessionId && !unfinishedResumePrompt && showRecentValidTrainingReminder"
          class="recent-valid-training-detail ui-surface ui-surface--subtle"
          :class="{ 'training-when-demo-soft': demoModeUi.active }"
          role="region"
          aria-label="最近有效训练详情"
        >
          <h3 class="tps-aux-h3">近期有效训练明细</h3>
          <p v-if="recentValidReminderExplicitNote" class="recent-valid-training-reminder__note muted">
            当前专项已由上一轮结果或历史页带入；以下为近期有效训练摘要，仅供对照，不会自动替换你的选择。
          </p>
          <ul class="recent-valid-training-reminder__list">
            <li>
              <span class="rvr-k">最近一次有效训练时间：</span>{{ recentValidLatestTime }}
            </li>
            <li>
              <span class="rvr-k">当时训练重点：</span>{{ recentValidLatestFocusLabel }}
            </li>
            <li v-if="recentValidLatestTotal != null">
              <span class="rvr-k">当时总分：</span>{{ recentValidLatestTotal }} 分
            </li>
            <li>
              <span class="rvr-k">近期有效训练：</span>共 {{ recentValidCount }} 次（统计窗口内），平均总分约
              {{ recentValidAvgTotal }} 分
            </li>
            <li>
              <span class="rvr-k">总览建议继续：</span><strong>{{ recentValidSuggestLabel }}</strong>
            </li>
          </ul>
        </section>
        <section
          v-if="trainingStageGuide.visible"
          class="training-stage-guide ui-surface"
          :class="{ 'training-when-demo-soft': demoModeUi.active }"
          role="region"
          aria-label="环节与流程说明"
        >
          <div class="ui-stage-callout">
            <p class="ui-stage-callout__k">本环节你可以</p>
            <p class="ui-stage-callout__action">{{ trainingStageGuide.nextAction }}</p>
            <p class="ui-stage-callout__meta muted">
              {{ trainingStageGuide.stageTitle }} · {{ trainingStageGuide.goal }}
            </p>
          </div>
          <h2 class="tsg-heading">整体流程</h2>
          <p class="tsg-disclaimer muted">
            下表帮你把握从讲解到结果的大致顺序，不必严格限时；以本页主操作区与提示为准。
          </p>
          <ol class="tsg-track" aria-label="训练流程步骤">
            <li
              v-for="s in trainingStageGuide.steps"
              :key="s.key"
              class="tsg-track-item"
              :class="s.statusClass"
            >
              <span class="tsg-track-num">{{ s.index }}</span>
              <span class="tsg-track-label">{{ s.label }}</span>
            </li>
          </ol>
          <p class="tsg-current-name">
            <span class="muted">当前环节：</span><strong>{{ trainingStageGuide.stageTitle }}</strong>
          </p>
          <p class="tsg-goal">
            <span class="muted">当前目标：</span>{{ trainingStageGuide.goal }}
          </p>
          <p v-if="trainingStageGuide.doneSummary" class="tsg-done muted">
            <span class="muted">已完成：</span>{{ trainingStageGuide.doneSummary }}
          </p>
          <p class="tsg-next">
            <span class="muted">建议下一步：</span>{{ trainingStageGuide.nextAction }}
          </p>
        </section>
        <div
          v-if="contentFocusDowngraded && !sessionId"
          class="specialty-downgrade-hint"
          :class="{ 'training-when-demo-soft': demoModeUi.active }"
          role="note"
        >
          <p>
            上一轮建议加强<strong>内容讲解</strong>，当前是<strong>无课件答辩</strong>：与课件强相关的练习更适合在
            <strong>有课件答辩</strong>下进行。可切换模式并上传课件，再练内容；或先选语言、仪态、问答等专项。
          </p>
        </div>
        <div v-if="recommendedTrainingFocus" class="training-focus-banner" role="status">
          <p class="training-focus-line">
            <strong>本轮专项：</strong>{{ trainingFocusBannerLabel }}
            <span class="training-focus-badge">专项训练</span>
            <span v-if="trainingFocusSource === 'result_page'" class="training-focus-source-note"
              >（来自上一轮结果或历史页）</span
            >
            <span v-else-if="trainingFocusSource === 'overview_hint'" class="training-focus-source-note"
              >（来自有效训练总览）</span
            >
            <span v-else-if="trainingFocusSource === 'resume_last_config'" class="training-focus-source-note"
              >（与上次有效训练配置一致）</span
            >
            <span v-else-if="trainingFocusSource === 'apply_recommended_focus'" class="training-focus-source-note"
              >（按总览建议方向）</span
            >
          </p>
          <el-button
            v-if="!sessionId"
            link
            type="primary"
            size="small"
            class="training-focus-clear"
            @click="clearRecommendedTrainingFocus"
          >
            改回常规训练
          </el-button>
        </div>
        <div
          v-if="trainingGoalServeHintLines.length && !sessionId"
          class="training-goal-hint"
          :class="{ 'training-when-demo-soft': demoModeUi.active }"
          role="note"
        >
          <h3 class="tps-aux-h3">训练目标</h3>
          <p
            v-for="(ln, i) in trainingGoalServeHintLines"
            :key="`tgh-${i}`"
            class="training-goal-hint__line"
          >
            {{ ln }}
          </p>
        </div>
        <div
          v-if="trainingGoalSessionStatusHintLines.length && sessionId"
          class="training-goal-hint training-goal-hint--session"
          :class="{ 'training-when-demo-soft': demoModeUi.active }"
          role="status"
        >
          <h3 class="tps-aux-h3">训练目标</h3>
          <p
            v-for="(ln, i) in trainingGoalSessionStatusHintLines"
            :key="`tgs-${i}`"
            class="training-goal-hint__line"
          >
            {{ ln }}
          </p>
        </div>
        <div
          v-if="trainingRhythmHintLinesFull.length"
          class="training-goal-hint training-rhythm-hint"
          :class="{ 'training-when-demo-soft': demoModeUi.active }"
          role="note"
        >
          <h3 class="tps-aux-h3">练习节奏</h3>
          <p
            v-for="(ln, i) in trainingRhythmHintLinesFull"
            :key="`trh-${i}`"
            class="training-goal-hint__line"
          >
            {{ ln }}
          </p>
        </div>
        <div
          v-if="trainingPlanAlignHintLine && !sessionId"
          class="training-goal-hint training-next-plan-align-hint"
          :class="{ 'training-when-demo-soft': demoModeUi.active }"
          role="note"
        >
          <h3 class="tps-aux-h3">练习安排</h3>
          <p class="training-goal-hint__line">{{ trainingPlanAlignHintLine }}</p>
        </div>
        <section
          v-if="specialtyGuidance"
          class="specialty-guidance-panel"
          :class="'specialty-guidance-panel--' + recommendedTrainingFocus"
        >
          <h2 class="specialty-guidance-title">{{ specialtyGuidance.title }}</h2>
          <p class="specialty-guidance-goal">
            <span class="specialty-label">本轮训练目标</span>{{ specialtyGuidance.goal }}
          </p>
          <p class="specialty-label">建议关注点</p>
          <ul class="specialty-guidance-tips">
            <li v-for="(line, idx) in specialtyGuidance.tips" :key="'sg-' + idx">{{ line }}</li>
          </ul>
          <p class="specialty-guidance-start">{{ specialtyGuidance.startTip }}</p>
        </section>
        <p
          v-else-if="!contentFocusDowngraded && !sessionId && !unfinishedResumePrompt"
          class="normal-training-reminder"
        >
          当前为<strong>常规训练</strong>：完成讲解与问答流程即可，系统会从语言、仪态、内容与问答综合给分。
        </p>
        <p class="tps-aux-cta muted">
          与运行与网络环境相关的技术说明，可在此上方展开「运行与环境（需了解时展开，可选）」与「补充说明（演示、网络…）」；与训练主流程无冲突。
        </p>
      </el-collapse-item>
    </el-collapse>
    </div>
    <!-- 答辩问答区：主流程仅展示与作答强相关区块 -->
    <div v-if="showQaSection && !sessionId" class="qa-section training-qa--pre-session" :class="{ 'qa-section--main': sessionId && !trainingFlowDebugMode }">
      <h3>{{ trainingFlowDebugMode ? '模拟答辩问答（调试）' : '答辩问答' }}</h3>
      <p v-if="qaPhaseAutoQuestionTip" class="qa-phase-auto-tip" role="status">{{ qaPhaseAutoQuestionTip }}</p>
      <p v-if="currentQaQuestion && trainingFlowDebugMode" class="qa-current-source">
        本轮问答通道：<strong>{{ qaChannelLabel }}</strong>
      </p>
      <p v-if="qaAutoFollowupHint" class="qa-auto-followup-banner" role="status">
        {{ qaAutoFollowupHint }}
      </p>
      <p
        v-if="trainingFlowDebugMode && lastQuestionGenerationContext && (qaRoundSource === 'auto_generated' || qaRoundSource === 'manual')"
        class="qa-followup-provider-debug"
      >
        <span class="muted-label">本轮首问来源：</span>{{ questionProviderDebugLine }}
      </p>
      <p
        v-if="trainingFlowDebugMode && lastFollowupGenerationContext && qaRoundSource === 'followup_generated'"
        class="qa-followup-provider-debug"
      >
        <span class="muted-label">本轮追问来源：</span>{{ followupProviderDebugLine }}
      </p>
      <div
        v-if="selectedFollowupIndex >= 0 && qaRoundSource === 'followup_generated'"
        class="fu-picked-banner"
        role="status"
      >
        老师追问已就绪，请使用语音作答，结束后将自动评估。
      </div>
      <p v-if="trainingFlowDebugMode" class="qa-tip">
        答辩默认：<strong>语音作答</strong>（与讲解复用同一套转写链路，不写回讲解主录音分析）。
      </p>
      <div v-if="trainingFlowDebugMode" class="qa-actions">
        <el-button type="primary" @click="generateQaQuestion" :disabled="!pptInfo || !selectedPageIndex">
          生成问题（单页调试）
        </el-button>
      </div>
      <div v-if="currentQaQuestion" class="qa-question">
        <p>
          <strong>{{ teacherQuestionLabel }}：</strong>{{ currentQaQuestion }}
        </p>
        <p v-if="currentQaExpectedKeywords.length">
          <strong>参考关键词：</strong>{{ currentQaExpectedKeywords.join('、') }}
        </p>
      </div>
      <div v-if="currentQaQuestion" class="qa-voice-answer">
        <p class="qa-voice-title">{{ qaVoiceAnswerTitle }}</p>
        <p v-if="isQaAnswerRecording" class="qa-recording-hint">正在录制你的回答…</p>
        <p v-if="isAnalyzingQaAudio && !qaAnswerEvaluatePending" class="qa-recording-hint">
          正在转写你的回答…
        </p>
        <p v-if="qaAnswerEvaluatePending" class="qa-recording-hint">正在评估回答…</p>
        <div class="qa-voice-actions">
          <el-button
            type="primary"
            @click="startQaAnswerRecording"
            :disabled="
              !currentQaQuestion || isQaAnswerRecording || isAnalyzingQaAudio || qaAnswerEvaluatePending
            "
          >
            {{ trainingFlowDebugMode ? '开始语音回答' : '请开始语音回答' }}
          </el-button>
          <el-button
            type="warning"
            @click="stopQaVoiceAnswer"
            :disabled="!isQaAnswerRecording || isAnalyzingQaAudio || qaAnswerEvaluatePending"
          >
            结束语音回答
          </el-button>
        </div>
        <p v-if="qaAnswerTranscript && !isAnalyzingQaAudio" class="qa-transcript-preview">
          <span class="muted-label">转写预览：</span>{{ qaAnswerTranscript }}
        </p>
      </div>
      <div v-if="currentQaQuestion && trainingFlowDebugMode" class="qa-text-fallback">
        <el-button
          link
          type="primary"
          class="qa-text-fallback-toggle"
          @click="qaTextFallbackExpanded = !qaTextFallbackExpanded"
        >
          {{ qaTextFallbackExpanded ? '收起' : '展开' }}文本兜底 / 调试输入
        </el-button>
        <div v-show="qaTextFallbackExpanded" class="qa-text-fallback-body">
          <el-input
            type="textarea"
            v-model="qaAnswerText"
            :rows="4"
            placeholder="手动输入或修改回答后，点击下方评估"
            @focus="onQaTextFallbackFocus"
          />
          <div class="qa-actions">
            <el-button
              type="success"
              @click="evaluateQaAnswer({ inputMode: 'text' })"
              :disabled="
                !currentQaQuestion ||
                !qaAnswerText ||
                isAnalyzingQaAudio ||
                qaAnswerEvaluatePending ||
                isQaAnswerRecording
              "
            >
              评估回答（文本）
            </el-button>
          </div>
        </div>
      </div>
      <div v-if="qaEvaluationResult" class="qa-result">
        <p><strong>是否切题：</strong>{{ qaEvaluationResult.is_relevant ? '是' : '否' }}</p>
        <p><strong>覆盖率：</strong>{{ qaEvaluationResult.coverage_score }}</p>
        <p><strong>命中关键词：</strong>{{ (qaEvaluationResult.hit_keywords || []).join('、') }}</p>
        <p><strong>缺失关键词：</strong>{{ (qaEvaluationResult.missing_keywords || []).join('、') }}</p>
        <p><strong>评价：</strong>{{ qaEvaluationResult.comment }}</p>
        <div v-if="showGenerateFollowupButton" class="qa-followup-actions">
          <el-button
            type="warning"
            :loading="isGeneratingFollowup"
            loading-text="生成中…"
            @click="generateFollowupQuestions"
          >
            生成追问
          </el-button>
          <span class="qa-followup-hint">
            若自动追问不足，可在此手动再生成（最多 3 条；一般无需操作）。首轮后通常已自动生成追问。
          </span>
        </div>
      </div>
      <div
        v-if="followupSectionVisible && (showQaFollowupPickerList || !followupQuestions.length)"
        class="qa-followup-list"
      >
        <p v-if="!followupQuestions.length" class="fu-empty-hint">
          本轮未生成明显追问，可先修改回答后再试。
        </p>
        <template v-else>
        <h4>追问候选（可选一条继续作答）</h4>
        <p v-if="followupTaxonomyLabel" class="fu-session-source muted" role="note">
          追问来源：{{ followupTaxonomyLabel }}
        </p>
        <p
          v-if="selectedFollowupIndex >= 0 && qaRoundSource === 'followup_generated'"
          class="fu-picked-inline"
          role="status"
        >
          已选为当前追问
        </p>
        <ol>
          <li
            v-for="(fu, fidx) in followupQuestions"
            :key="fidx"
            :class="['qa-followup-row', { 'qa-followup-row--picked': selectedFollowupIndex === fidx }]"
          >
            <div class="fu-main-row">
              <span class="fu-q">{{ fu.question }}</span>
              <el-button
                size="small"
                type="primary"
                link
                class="mock-pick-btn"
                @click.stop="selectFollowupQuestion(fidx)"
              >
                {{ selectedFollowupIndex === fidx ? '当前追问' : '选为当前追问' }}
              </el-button>
            </div>
            <div v-if="followupDirectionLabel(fu.source)" class="fu-direction">
              {{ followupDirectionLabel(fu.source) }}
            </div>
            <p v-if="fu.reason" class="fu-reason">{{ fu.reason }}</p>
          </li>
        </ol>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { postJson, uploadFile, getJson } from '../api/base'
import { trainingFeedback, trainingConfirmDanger } from '../utils/pageFeedback'
import { runtimeChainSummaryLine, boardParticipationLine } from '../utils/inferenceChainLabels'
import {
  readDemoMode,
  exitDemoMode,
  activateDemoModeFromRouteQuery,
  stripDemoQueryKeys,
} from '../utils/demoMode'
import {
  readAppPreferences,
  APP_PREFERENCES_CHANGED_EVENT,
  preferencesSnapshotForLog,
  TRAINING_DRAFT_KEY,
  TRAINING_RUNTIME_SNAPSHOT_KEY,
  TRAINING_FOCUS_HANDOFF_KEY,
  CURRENT_SESSION_ID_KEY,
  LAST_PPT_ID_STORAGE_KEY,
  persistCurrentSessionId,
} from '../utils/appPreferences'
import {
  readUserScopedItem,
  writeUserScopedItem,
  removeUserScopedItem,
  getActiveUserId,
} from '../utils/userScopedStorage'
import {
  readTrainingGoals,
  hasActiveTrainingGoals,
  TRAINING_GOAL_FOCUS_LABEL,
  TRAINING_GOALS_CHANGED_EVENT,
  computeTrainingGoalProgress,
} from '../utils/trainingGoals'
import { computeGoalStatusPack, GOAL_STATUS } from '../utils/trainingGoalStatus'
import { computeTrainingRhythm, buildTrainingRhythmHintLines } from '../utils/trainingStreaks'
import { computeWeeklyTrainingReview } from '../utils/trainingWeeklyReview'
import { computeNextTrainingPlan, buildTrainingPlanAlignHint } from '../utils/nextTrainingPlan'
import { TRAINING_FOCUS_LABEL, TRAINING_STAGE_TRACK, trainingFocusLabel } from '../constants/productTerms'
import { PAGE_LOADING, PAGE_ERROR_ALERT_TITLE } from '../constants/pageStatusCopy'

const router = useRouter()
const route = useRoute()

function clearTrainingPageError() {
  errorMessage.value = ''
}
function goHomeFromTrainingPage() {
  router.push('/home')
}

const preferencesRevision = ref(0)
function onAppPreferencesExternalChange() {
  preferencesRevision.value++
}

const trainingGoalsRevision = ref(0)
function onTrainingGoalsExternalChange() {
  trainingGoalsRevision.value++
}

const RECOMMENDED_FOCUS_STORAGE_KEY = TRAINING_FOCUS_HANDOFF_KEY
const TRAINING_PAGE_DRAFT_STORAGE_KEY = TRAINING_DRAFT_KEY
const FIRST_TRAINING_HINT_DISMISS_KEY = 'mianshi_training_first_hint_dismissed_v1'

function preflightOkBaseKey(sid) {
  return `mianshi_preflight_ok_${String(sid || '').trim()}`
}
let runtimeSnapshotTimer = null
const unfinishedResumePrompt = ref(null)
const resumeMediaHintVisible = ref(false)
/** resume_status 请求失败且本地仍有 session_id 时提示用户可重新开始 */
const resumeSessionCheckFailed = ref(false)

/** 比赛展示：与自检同源，仅作当前链路说明，不驱动流程 */
const trainingPageProviderStatus = ref(null)
const trainingRuntimeChainLine = computed(() =>
  runtimeChainSummaryLine(trainingPageProviderStatus.value)
)

const demoModeUi = ref(readDemoMode())
/** 非演示模式：折叠运行链路说明，减少首屏噪音 */
const trainingAuxCollapse = ref([])
/** 演示/网络/近期训练等补充说明，首屏不默认展开，避免与主任务区抢视线 */
const trainingSupplementalCollapse = ref([])
/** 顶栏：辅助说明与详情，默认收起 */
const trainingTopAuxHintsCollapse = ref([])
const trainingBoardLine = computed(() => boardParticipationLine(trainingPageProviderStatus.value))

/** 与 provider-status 同源：优先 ascend_service_runtime，否则回退 ascend_health_check.response 全文 */
const trainingDemoRuntimeCollapse = ref([])
const trainingChainNestedEnvCollapse = ref([])
const ascendRuntimeForDisplay = computed(() => {
  const s = trainingPageProviderStatus.value
  if (!s) return null
  const top = s.ascend_service_runtime
  if (top && typeof top === 'object' && Object.keys(top).length) return top
  const r = s.ascend_health_check?.response
  if (!r || typeof r !== 'object') return null
  // 与 system.py 一致：无板址时仅有 note 的占位，不是真实板侧 /health
  if (r.note && !('status' in r) && !('service' in r)) return null
  return r
})
const showAscendRuntimeCollapse = computed(
  () => !!ascendRuntimeForDisplay.value && Object.keys(ascendRuntimeForDisplay.value).length > 0
)
const ascendRuntimeEvidenceText = computed(() => {
  const o = ascendRuntimeForDisplay.value
  if (!o) return ''
  try {
    return JSON.stringify(o, null, 2)
  } catch {
    return String(o)
  }
})

function refreshTrainingDemoMode() {
  demoModeUi.value = readDemoMode()
}

function exitTrainingDemoMode() {
  exitDemoMode()
  refreshTrainingDemoMode()
}

/** 训练页 UI 会话状态收口（展示 / 按钮门控 / 日志） */
const UI_SESSION_STATE = Object.freeze({
  IDLE: 'idle',
  PREFLIGHT_READY: 'preflight_ready',
  SESSION_RUNNING_LECTURE: 'session_running_lecture',
  SESSION_RUNNING_QA: 'session_running_qa',
  SESSION_PAUSED_RECOVERABLE: 'session_paused_recoverable',
  SESSION_COMPLETING: 'session_completing',
  SESSION_COMPLETED: 'session_completed',
  SESSION_DISCARDED: 'session_discarded',
})
/** 放弃未完成会话后的短暂提示（避免与恢复卡片并存） */
const sessionDiscardedBanner = ref('')
const lastLoggedUiStateKey = ref('')

const draftPersistenceReady = ref(false)

function hasExplicitTrainingRouteQuery() {
  const q = route.query
  if (String(q.entry || '').trim().toLowerCase() === 'home') {
    const ha = String(q.home_action || '').trim().toLowerCase()
    if (ha === 'regular') return true
  }
  if (normalizeIncomingFocusKey(q.recommended_focus)) return true
  const sp = String(q.scoring_profile || '').trim().toLowerCase()
  if (sp === 'defense' || sp === 'interview') return true
  const dm = String(q.defense_material_mode || '').trim().toLowerCase()
  if (dm === 'with_ppt' || dm === 'without_ppt') return true
  return false
}

function draftDefenseMaterialFromDeck() {
  return trainingDeckMode.value === 'none' ? 'without_ppt' : 'with_ppt'
}

function saveTrainingPageDraft() {
  if (sessionId.value || !draftPersistenceReady.value) return
  try {
    const lastResumeAction =
      trainingFocusSource.value === 'resume_last_config'
        ? 'resume_last_config'
        : trainingFocusSource.value === 'apply_recommended_focus'
          ? 'apply_recommended_focus'
          : null
    writeUserScopedItem(
      localStorage,
      TRAINING_PAGE_DRAFT_STORAGE_KEY,
      JSON.stringify({
        v: 1,
        scoring_profile: trainingScoringProfile.value,
        defense_material_mode: draftDefenseMaterialFromDeck(),
        recommended_training_focus: recommendedTrainingFocus.value,
        training_focus_source: trainingFocusSource.value,
        last_resume_action: lastResumeAction,
        ts: Date.now(),
      })
    )
  } catch (_) {}
}

function clearTrainingPageDraftStorage() {
  try {
    removeUserScopedItem(localStorage, TRAINING_PAGE_DRAFT_STORAGE_KEY, undefined, true)
    console.log('[Training.restore] cleared_saved_config=', true)
  } catch (_) {
    console.log('[Training.restore] cleared_saved_config=', false)
  }
}

function applyGlobalTrainingDefaultsFromPrefs() {
  const p = readAppPreferences()
  trainingScoringProfile.value = p.scoring_profile === 'interview' ? 'interview' : 'defense'
  if (p.defense_material_mode === 'without_ppt') {
    trainingDeckMode.value = 'none'
  } else {
    trainingDeckMode.value = 'with_deck'
  }
}

function restoreTrainingPageDraftFromLocal() {
  if (sessionId.value) return false
  let found = false
  let parsed = null
  try {
    const raw = readUserScopedItem(localStorage, TRAINING_PAGE_DRAFT_STORAGE_KEY)
    if (raw) {
      parsed = JSON.parse(raw)
      found = !!(parsed && typeof parsed === 'object')
    }
  } catch (_) {
    parsed = null
    found = false
  }
  console.log('[Training.restore] found_saved_config=', found, parsed || null)
  if (!found || !parsed) {
    console.log('[Training.restore] restored_from=', '(none)')
    console.log('[Training.restore] incoming_focus_priority=', incomingFocusPriority.value)
    return false
  }

  const sp = String(parsed.scoring_profile || '').trim().toLowerCase()
  if (sp === 'defense' || sp === 'interview') {
    trainingScoringProfile.value = sp
  }
  const dm = String(parsed.defense_material_mode || '').trim().toLowerCase()
  if (dm === 'without_ppt') {
    trainingDeckMode.value = 'none'
  } else if (dm === 'with_ppt') {
    trainingDeckMode.value = 'with_deck'
  }

  const fk = normalizeIncomingFocusKey(parsed.recommended_training_focus)
  recommendedTrainingFocus.value = fk

  const srcRaw = String(parsed.training_focus_source || 'manual').trim().toLowerCase()
  const allowed = new Set([
    'result_page',
    'overview_hint',
    'resume_last_config',
    'apply_recommended_focus',
    'manual',
    'none',
  ])
  trainingFocusSource.value = allowed.has(srcRaw) ? srcRaw : fk ? 'manual' : 'none'

  contentFocusDowngraded.value = false

  if (recommendedTrainingFocus.value === 'content' && trainingDeckMode.value === 'none') {
    recommendedTrainingFocus.value = null
    trainingFocusSource.value = 'none'
    contentFocusDowngraded.value = true
  }

  try {
    writeUserScopedItem(
      sessionStorage,
      RECOMMENDED_FOCUS_STORAGE_KEY,
      JSON.stringify({
        recommended_focus: recommendedTrainingFocus.value,
        scoring_profile: trainingScoringProfile.value,
        defense_material_mode: draftDefenseMaterialFromDeck(),
        source: trainingFocusSource.value,
        ts: Date.now(),
      })
    )
  } catch (_) {}

  const q = {
    ...route.query,
    scoring_profile: trainingScoringProfile.value,
    defense_material_mode: draftDefenseMaterialFromDeck(),
  }
  if (recommendedTrainingFocus.value) {
    q.recommended_focus = recommendedTrainingFocus.value
  } else {
    delete q.recommended_focus
  }
  router.replace({ path: route.path, query: q })

  console.log('[Training.restore] restored_from=', 'local_storage_draft')
  console.log('[Training.restore] incoming_focus_priority=', incomingFocusPriority.value)
  return true
}

async function resetTrainingPageToDefaults() {
  draftPersistenceReady.value = false
  applyGlobalTrainingDefaultsFromPrefs()
  recommendedTrainingFocus.value = null
  trainingFocusSource.value = 'manual'
  contentFocusDowngraded.value = false
  clearTrainingPageDraftStorage()
  try {
    removeUserScopedItem(sessionStorage, RECOMMENDED_FOCUS_STORAGE_KEY, undefined, true)
  } catch (_) {}
  logTrainingFocus({ guidance_mode: 'normal', downgraded_from_content: false })
  await router.replace({ path: route.path, query: {} })
  await nextTick()
  draftPersistenceReady.value = true
}

async function confirmResetTrainingPageToDefaults() {
  let msg =
    '将按偏好设置恢复默认的评分模式与课件模式，并清除已保存的专项与地址栏预填。不会结束已在进行中的训练。'
  if (unfinishedResumePrompt.value) {
    msg +=
      ' 当前仍有未完成会话提示：请先选择继续或放弃，再清除预填。'
  }
  const ok = await trainingConfirmDanger({
    title: '清除预填并恢复默认？',
    message: msg,
    confirmButtonText: '清除并恢复',
    cancelButtonText: '取消',
  })
  if (!ok) return
  await resetTrainingPageToDefaults()
  trainingFeedback(
    'reset_defaults',
    'success',
    '已恢复默认配置。完成自检后即可点击「开始训练」。'
  )
}

const validTrainingOverviewFromApi = ref(null)
/** 与 /history 同源，用于目标状态判断 */
const trainingHistoryListForGoals = ref([])
const validTrainingOverviewLoadFailed = ref(false)
/** /history 列表条数；0 且未手动关闭提示时展示首次引导 */
const trainingHistoryTotalCount = ref(null)

function readFirstTrainingHintDismissed() {
  try {
    return readUserScopedItem(localStorage, FIRST_TRAINING_HINT_DISMISS_KEY) === '1'
  } catch (_) {
    return false
  }
}

const firstTrainingHintDismissed = ref(readFirstTrainingHintDismissed())

function dismissFirstTrainingHint() {
  firstTrainingHintDismissed.value = true
  try {
    writeUserScopedItem(localStorage, FIRST_TRAINING_HINT_DISMISS_KEY, '1')
  } catch (_) {}
  console.log('[Training.empty] first_time_hint_visible=', false)
}

const recommendedTrainingFocus = ref(null)
const trainingFocusSource = ref('none')
/** 推荐内容为专项但当前无课件模式：已降级并仅展示轻提示 */
const contentFocusDowngraded = ref(false)

const SPECIALTY_GUIDANCE = {
  language: {
    title: '语言专项',
    goal: '让评委听得清楚、节奏舒服，把观点稳稳送到对方耳朵里。',
    tips: [
      '想象对面坐着一位评委：语速略慢、咬字清楚，每句话说完再接下一层意思。',
      '想不起词时宁可停顿一两秒，少用「然后、就是、那个」撑场面。',
      '重要结论前轻轻收一下语速，给对方跟上思路的时间。',
      '补充发挥时宁可短而准，不要越说越快、越绕越远。',
    ],
    startTip: '开始前确认麦克风与环境安静；开始训练后先完整讲一轮，再在回放与评分里对照语言项慢慢抠细节。',
  },
  posture: {
    title: '仪态专项',
    goal: '让身体语言帮你加分：稳重、自然、像在正式场合面对评委。',
    tips: [
      '视线尽量平视为主，偶尔自然扫视即可，少长时间低头看稿或瞟角落。',
      '肩膀放松、站姿稳定，手势为辅，不要来回晃或抱臂显得拘谨。',
      '讲到重点时可以略微前倾一点，显得投入；讲完一个小节再收回重心。',
      '注意光线与机位：面部在画面里清晰，避免顶光或侧脸过大。',
    ],
    startTip: '开始训练后系统会持续采样画面；尽量全程待在镜头舒适区内，像正式答辩那样站定再开口。',
  },
  qa: {
    title: '问答专项',
    goal: '把「听清题、答在点上、说完整」练成习惯，追问来了也不慌。',
    tips: [
      '听完问题心里先默念一遍题眼：问什么就答什么，少绕弯子。',
      '先给一句总观点，再补两三句论据或例子，层次清楚即可。',
      '不会的地方诚实收窄范围，比空泛堆砌更让人放心。',
      '语音作答时句尾收干净，避免说到一半断掉或声音越来越小。',
    ],
    startTip: '进入问答后按提示语音作答；把每一轮都当成正式答辩的一环，答完再停，方便系统完整评估。',
  },
  content: {
    title: '内容专项',
    goal: '让讲解和课件「对得上」：结构清楚、关键词到位，听起来像在讲你自己的研究。',
    tips: [
      '先想清楚本页最想传达的一条主线，再展开细节，避免信息堆成一团。',
      '口述里尽量点到标题或大纲里的关键词，帮助系统对齐当前页。',
      '举例和延伸不要紧贴题外话题，收束时回到本页结论。',
      '若使用猜页或手动选页，讲解时口头线索越清晰，对齐越稳。',
    ],
    startTip: '有课件时请先完成上传与解析；讲解阶段像正式答辩一样过一遍幻灯，再进入老师提问。',
  },
}

function normalizeIncomingFocusKey(k) {
  const x = String(k || '').trim().toLowerCase()
  if (x === 'language' || x === 'posture' || x === 'qa' || x === 'content') return x
  return null
}

const specialtyGuidance = computed(() => {
  const k = recommendedTrainingFocus.value
  if (!k || !SPECIALTY_GUIDANCE[k]) return null
  return SPECIALTY_GUIDANCE[k]
})

const trainingGuidanceMode = computed(() => {
  if (recommendedTrainingFocus.value) return recommendedTrainingFocus.value
  if (contentFocusDowngraded.value) return 'normal_downgraded_content'
  return 'normal'
})

/** 与后端 training_focus 对齐：有专项建议时为四选一，否则为 none（常规训练） */
const finalTrainingFocus = computed(() => {
  const k = recommendedTrainingFocus.value
  if (k === 'language' || k === 'posture' || k === 'qa' || k === 'content') return k
  return 'none'
})

const trainingRhythmStats = computed(() => {
  void trainingGoalsRevision.value
  const g = readTrainingGoals()
  const progress = computeTrainingGoalProgress({
    goals: g,
    historyList: trainingHistoryListForGoals.value,
    overview: validTrainingOverviewFromApi.value,
  })
  const pack = computeGoalStatusPack(progress)
  let countRemaining = null
  if (progress.validCountProgress) {
    const rem = progress.validCountProgress.target - progress.validCountProgress.current
    countRemaining = rem > 0 ? rem : null
  }
  return computeTrainingRhythm(trainingHistoryListForGoals.value, {
    goalStatus: pack.status,
    targetFocus: g.target_focus || null,
    countRemaining,
  })
})

const trainingRhythmHintLinesFull = computed(() => buildTrainingRhythmHintLines(trainingRhythmStats.value))

const trainingWeeklyForPlan = computed(() => {
  void trainingGoalsRevision.value
  return computeWeeklyTrainingReview(trainingHistoryListForGoals.value, {
    overview: validTrainingOverviewFromApi.value,
    goals: readTrainingGoals(),
  })
})

const trainingGoalProgressForPlan = computed(() => {
  void trainingGoalsRevision.value
  return computeTrainingGoalProgress({
    goals: readTrainingGoals(),
    historyList: trainingHistoryListForGoals.value,
    overview: validTrainingOverviewFromApi.value,
  })
})

const trainingGoalStatusPackForPlan = computed(() => computeGoalStatusPack(trainingGoalProgressForPlan.value))

const trainingNextPlan = computed(() => {
  void trainingGoalsRevision.value
  return computeNextTrainingPlan({
    historyList: trainingHistoryListForGoals.value,
    overview: validTrainingOverviewFromApi.value,
    goals: readTrainingGoals(),
    goalProgress: trainingGoalProgressForPlan.value,
    goalStatusPack: trainingGoalStatusPackForPlan.value,
    rhythmStats: trainingRhythmStats.value,
    weeklyReview: trainingWeeklyForPlan.value,
  })
})

const trainingPlanAlignHintLine = computed(() =>
  buildTrainingPlanAlignHint(trainingNextPlan.value, finalTrainingFocus.value)
)

watch(
  trainingNextPlan,
  (p) => {
    if (!p?.next_plan_action) return
    console.log('[Training.next_plan] action=', p.next_plan_action)
  },
  { flush: 'post' }
)

const trainingGoalServeHintLines = computed(() => {
  void trainingGoalsRevision.value
  const g = readTrainingGoals()
  if (!hasActiveTrainingGoals(g)) return []
  const lines = []
  const progress = computeTrainingGoalProgress({
    goals: g,
    historyList: trainingHistoryListForGoals.value,
    overview: validTrainingOverviewFromApi.value,
  })
  const pack = computeGoalStatusPack(progress)
  if (pack.status === GOAL_STATUS.NEAR_COMPLETE) {
    lines.push('当前阶段目标已接近完成，本轮适合当作冲刺或巩固。')
  } else if (pack.status === GOAL_STATUS.ACHIEVED) {
    lines.push('当前设定目标已达成（规则判断），本轮可用于巩固或尝试更高标准。')
  }
  const bits = []
  if (g.target_total_score != null) {
    bits.push(`目标总分 ${Number(g.target_total_score).toFixed(1)}`)
  }
  if (g.target_focus) {
    bits.push(`目标专项「${TRAINING_GOAL_FOCUS_LABEL[g.target_focus] || g.target_focus}」`)
  }
  if (g.target_valid_session_count != null) {
    bits.push(`目标有效训练 ${g.target_valid_session_count} 次`)
  }
  if (bits.length) {
    lines.push(`你在首页设定的阶段目标：${bits.join('；')}。本轮练习可视为向该目标推进的一步。`)
  }
  const goalFk = g.target_focus
  const fin = finalTrainingFocus.value
  if (goalFk && fin === goalFk) {
    lines.push('当前训练与目标方向一致，适合集中打磨这一项。')
  }
  if (lines.length) {
    console.log('[Training.goal] serve_hint=', lines)
  }
  return lines
})

const trainingGoalSessionStatusHintLines = computed(() => {
  void trainingGoalsRevision.value
  const g = readTrainingGoals()
  if (!hasActiveTrainingGoals(g)) return []
  const progress = computeTrainingGoalProgress({
    goals: g,
    historyList: trainingHistoryListForGoals.value,
    overview: validTrainingOverviewFromApi.value,
  })
  const pack = computeGoalStatusPack(progress)
  const lines = []
  if (pack.status === GOAL_STATUS.NEAR_COMPLETE) {
    lines.push('提示：当前目标已接近完成，本轮结束后可到首页查看是否达标。')
  } else if (pack.status === GOAL_STATUS.ACHIEVED) {
    lines.push('提示：当前目标已达成（规则判断），本轮可作为巩固训练。')
  }
  const goalFk = g.target_focus
  const fin = finalTrainingFocus.value
  if (goalFk && fin === goalFk) {
    lines.push('当前训练与目标专项方向一致。')
  }
  return lines
})

function logTrainingFocus(opts = {}) {
  const guidance =
    opts.guidance_mode !== undefined ? opts.guidance_mode : trainingGuidanceMode.value
  console.log(
    '[Training.focus] recommended_training_focus=',
    recommendedTrainingFocus.value ?? '(none)',
    'source=',
    trainingFocusSource.value
  )
  console.log('[Training.focus] final training_focus=', finalTrainingFocus.value)
  console.log('[Training.focus] guidance_mode=', guidance)
  if (opts.downgraded_from_content === true) {
    console.log('[Training.focus] downgraded_from_content=true')
  } else if (opts.downgraded_from_content === false) {
    console.log('[Training.focus] downgraded_from_content=false')
  }
}

function resolveTrainingEntrySource() {
  const e = String(route.query.entry || '').trim().toLowerCase()
  if (
    e === 'home' ||
    e === 'history' ||
    e === 'result_resume' ||
    e === 'result_recommended' ||
    e === 'report_recommended'
  ) {
    return e
  }
  if (e === 'result') return 'result_recommended'
  return 'direct'
}

function applyIncomingTrainingFocus() {
  const q = route.query
  const entry = String(q.entry || '').trim().toLowerCase()
  const homeAction = String(q.home_action || '').trim().toLowerCase()

  if (entry === 'home' && homeAction === 'regular') {
    try {
      removeUserScopedItem(sessionStorage, RECOMMENDED_FOCUS_STORAGE_KEY, undefined, true)
    } catch (_) {}
    applyGlobalTrainingDefaultsFromPrefs()
    recommendedTrainingFocus.value = null
    trainingFocusSource.value = 'manual'
    contentFocusDowngraded.value = false
    logTrainingFocus({ guidance_mode: 'normal', downgraded_from_content: false })
    const q2 = { ...route.query }
    delete q2.home_action
    router.replace({ path: route.path, query: q2 })
    return { usedSessionStorage: false }
  }

  const explicitNav = hasExplicitTrainingRouteQuery()

  let focus = normalizeIncomingFocusKey(q.recommended_focus)
  let profile = String(q.scoring_profile || '').trim()
  let dm = String(q.defense_material_mode || '').trim().toLowerCase()
  let source = 'none'
  let usedSessionStorage = false

  if (!explicitNav) {
    try {
      const raw = readUserScopedItem(sessionStorage, RECOMMENDED_FOCUS_STORAGE_KEY)
      if (raw) {
        const o = JSON.parse(raw)
        const srcRaw = String(o.source || '').trim().toLowerCase()
        const fk = normalizeIncomingFocusKey(o.recommended_focus)

        if (srcRaw === 'resume_last_config') {
          usedSessionStorage = true
          source = 'resume_last_config'
          if (!profile && o.scoring_profile) profile = String(o.scoring_profile).trim()
          if (!dm && o.defense_material_mode) dm = String(o.defense_material_mode).trim().toLowerCase()
          focus = fk || null
        } else if (srcRaw === 'apply_recommended_focus') {
          usedSessionStorage = true
          source = 'apply_recommended_focus'
          if (!profile && o.scoring_profile) profile = String(o.scoring_profile).trim()
          if (!dm && o.defense_material_mode) dm = String(o.defense_material_mode).trim().toLowerCase()
          focus = fk || null
        } else if (fk) {
          usedSessionStorage = true
          focus = fk
          if (!profile && o.scoring_profile) profile = String(o.scoring_profile).trim()
          if (!dm && o.defense_material_mode) dm = String(o.defense_material_mode).trim().toLowerCase()
          if (srcRaw === 'overview_hint') source = 'overview_hint'
          else source = 'result_page'
        }
      }
    } catch (_) {}
  } else if (focus) {
    source = 'result_page'
  }

  contentFocusDowngraded.value = false

  const pNorm = profile.trim().toLowerCase()
  if (pNorm === 'interview' || pNorm === 'defense') {
    trainingScoringProfile.value = pNorm
  }
  if (dm === 'without_ppt') {
    trainingDeckMode.value = 'none'
  } else if (dm === 'with_ppt') {
    trainingDeckMode.value = 'with_deck'
  }

  if (!focus && source === 'none') {
    recommendedTrainingFocus.value = null
    trainingFocusSource.value = 'none'
    logTrainingFocus({ guidance_mode: 'normal', downgraded_from_content: false })
    return { usedSessionStorage }
  }

  if (!focus) {
    recommendedTrainingFocus.value = null
    trainingFocusSource.value =
      source === 'resume_last_config'
        ? 'resume_last_config'
        : source === 'apply_recommended_focus'
          ? 'apply_recommended_focus'
          : 'none'
    logTrainingFocus({ guidance_mode: 'normal', downgraded_from_content: false })
    return { usedSessionStorage }
  }

  recommendedTrainingFocus.value = focus
  trainingFocusSource.value = source

  if (recommendedTrainingFocus.value === 'content' && trainingDeckMode.value === 'none') {
    recommendedTrainingFocus.value = null
    trainingFocusSource.value = 'none'
    contentFocusDowngraded.value = true
    logTrainingFocus({ guidance_mode: 'normal', downgraded_from_content: true })
    return { usedSessionStorage }
  }

  logTrainingFocus({ downgraded_from_content: false })
  return { usedSessionStorage }
}

async function clearRecommendedTrainingFocus() {
  const ok = await trainingConfirmDanger({
    title: '清除当前专项预填？',
    message:
      '将移除本轮推荐的专项训练方向与相关地址栏参数，不会影响已在进行中的会话。之后可按默认或自选方式开始训练。',
    confirmButtonText: '清除',
    cancelButtonText: '保留',
  })
  if (!ok) return
  recommendedTrainingFocus.value = null
  trainingFocusSource.value = 'manual'
  contentFocusDowngraded.value = false
  try {
    removeUserScopedItem(sessionStorage, RECOMMENDED_FOCUS_STORAGE_KEY, undefined, true)
  } catch (_) {}
  router.replace({ path: route.path, query: {} })
  logTrainingFocus({ guidance_mode: 'normal', downgraded_from_content: false })
  trainingFeedback(
    'clear_prefill',
    'success',
    '已清除专项预填。可按当前模式继续调整，然后点击「开始训练」。'
  )
}

const trainingFocusBannerLabel = computed(() => {
  const k = recommendedTrainingFocus.value
  if (!k) return ''
  return TRAINING_FOCUS_LABEL[k] || k
})

function overviewFocusLabel(k) {
  return trainingFocusLabel(k)
}

function formatValidOverviewTime(ts) {
  if (ts == null || String(ts).trim() === '') return '—'
  try {
    return new Date(ts).toLocaleString()
  } catch (_) {
    return String(ts)
  }
}

async function fetchValidTrainingOverview() {
  validTrainingOverviewLoadFailed.value = false
  try {
    const data = await getJson('/history')
    validTrainingOverviewFromApi.value = data.valid_training_overview ?? null
    trainingHistoryTotalCount.value = Array.isArray(data.history) ? data.history.length : 0
    trainingHistoryListForGoals.value = Array.isArray(data.history) ? data.history : []
  } catch (_) {
    validTrainingOverviewLoadFailed.value = true
    validTrainingOverviewFromApi.value = null
    trainingHistoryTotalCount.value = null
    trainingHistoryListForGoals.value = []
  }
}

const validTrainingOverviewReady = computed(() => {
  const o = validTrainingOverviewFromApi.value
  return !!(o && o.overview_ready && (o.valid_count_recent || 0) > 0)
})

const incomingFocusPriority = computed(() => {
  if (recommendedTrainingFocus.value && trainingFocusSource.value === 'result_page') {
    return 'explicit_incoming'
  }
  if (recommendedTrainingFocus.value && trainingFocusSource.value === 'resume_last_config') {
    return 'resume_last_config'
  }
  if (recommendedTrainingFocus.value && trainingFocusSource.value === 'apply_recommended_focus') {
    return 'apply_recommended_focus'
  }
  if (recommendedTrainingFocus.value && trainingFocusSource.value === 'overview_hint') {
    return 'overview_applied'
  }
  if (!recommendedTrainingFocus.value && trainingFocusSource.value === 'resume_last_config') {
    return 'resume_last_config'
  }
  if (recommendedTrainingFocus.value) return 'other'
  if (validTrainingOverviewReady.value) return 'overview_hint_available'
  if (validTrainingOverviewFromApi.value && validTrainingOverviewFromApi.value.overview_ready === false) {
    return 'no_valid_history'
  }
  return 'none'
})

const recentValidReminderExplicitNote = computed(
  () => incomingFocusPriority.value === 'explicit_incoming'
)

const recentValidLatestTime = computed(() =>
  formatValidOverviewTime(validTrainingOverviewFromApi.value?.latest_valid_created_at)
)

const recentValidLatestFocusLabel = computed(() =>
  overviewFocusLabel(validTrainingOverviewFromApi.value?.latest_valid_training_focus)
)

const recentValidLatestTotal = computed(() => {
  const v = validTrainingOverviewFromApi.value?.latest_valid_total_score
  if (v == null || v === '') return null
  const n = Number(v)
  return Number.isFinite(n) ? n.toFixed(1) : null
})

const recentValidCount = computed(() => validTrainingOverviewFromApi.value?.valid_count_recent ?? 0)

const recentValidAvgTotal = computed(() => {
  const v = validTrainingOverviewFromApi.value?.avg_total_score_recent
  if (v == null) return '—'
  const n = Number(v)
  return Number.isFinite(n) ? n.toFixed(1) : '—'
})

const recentValidSuggestLabel = computed(() =>
  overviewFocusLabel(validTrainingOverviewFromApi.value?.recommended_continue_focus)
)

const recentValidReminderEmptyText = computed(() => {
  if (validTrainingOverviewLoadFailed.value) {
    return '暂时无法加载最近有效训练摘要，你仍可照常开始训练。'
  }
  return '暂无最近有效训练记录，完成几次有效训练后会在这里汇总。'
})

function trainingSessionShortId(sid) {
  const s = String(sid || '')
  if (!s) return '—'
  if (s.length <= 12) return s
  return `${s.slice(0, 6)}…${s.slice(-4)}`
}

const unfinishedResumePhaseDisplay = computed(() => {
  const ctx = unfinishedResumePrompt.value
  if (!ctx) return ''
  const ph = ctx.snapshot?.session_phase
  if (ph === 'qa') return '答辩问答阶段'
  if (ph === 'lecture') return '讲解阶段'
  return '仅恢复模式与专项（本地无完整阶段缓存）'
})

const unfinishedResumeServerProfileLabel = computed(() => {
  const ctx = unfinishedResumePrompt.value
  const sp = String(ctx?.server?.scoring_profile || '').toLowerCase()
  if (sp === 'interview') return '面试模式'
  if (sp === 'defense') return '答辩模式'
  return '—'
})

const unfinishedResumeServerDmLabel = computed(() => {
  const ctx = unfinishedResumePrompt.value
  const dm = String(ctx?.server?.defense_material_mode || '').toLowerCase()
  if (dm === 'without_ppt') return '无课件答辩'
  if (dm === 'with_ppt') return '有课件答辩'
  return '—'
})

const unfinishedResumeServerFocusLabel = computed(() => {
  const ctx = unfinishedResumePrompt.value
  const tf = String(ctx?.server?.training_focus ?? 'none').trim().toLowerCase()
  return trainingFocusLabel(tf)
})

const continueResumeButtonLabel = computed(() => {
  const ctx = unfinishedResumePrompt.value
  if (!ctx?.hasSnapshot || !ctx.snapshot) return '继续本轮训练'
  const ph = ctx.snapshot.session_phase
  if (ph === 'qa') return '继续答辩问答'
  if (ph === 'lecture') return '继续讲解'
  return '继续本轮训练'
})

const applyRecommendedDirectionVisible = computed(() => {
  if (!validTrainingOverviewReady.value) return false
  const rec = validTrainingOverviewFromApi.value?.recommended_continue_focus
  if (rec == null || String(rec).trim() === '') return false
  const raw = String(rec).trim().toLowerCase()
  if (raw === 'none') return true
  return !!normalizeIncomingFocusKey(rec)
})

function defenseMaterialModeFromDeck() {
  return trainingDeckMode.value === 'none' ? 'without_ppt' : 'with_ppt'
}

function persistAndSyncTrainingQuery(sourceTag) {
  const dm = defenseMaterialModeFromDeck()
  try {
    writeUserScopedItem(
      sessionStorage,
      RECOMMENDED_FOCUS_STORAGE_KEY,
      JSON.stringify({
        recommended_focus: recommendedTrainingFocus.value,
        scoring_profile: trainingScoringProfile.value,
        defense_material_mode: dm,
        source: sourceTag,
        ts: Date.now(),
      })
    )
  } catch (_) {}
  const q = { ...route.query, scoring_profile: trainingScoringProfile.value, defense_material_mode: dm }
  if (recommendedTrainingFocus.value) {
    q.recommended_focus = recommendedTrainingFocus.value
  } else {
    delete q.recommended_focus
  }
  router.replace({ path: route.path, query: q })
  saveTrainingPageDraft()
}

function logTrainingResume(action) {
  console.log('[Training.resume] action=', action)
  console.log('[Training.resume] scoring_profile=', trainingScoringProfile.value)
  console.log('[Training.resume] defense_material_mode=', defenseMaterialModeFromDeck())
  console.log('[Training.resume] training_focus=', recommendedTrainingFocus.value ?? 'none')
}

function logTrainingOverviewState() {
  const o = validTrainingOverviewFromApi.value
  console.log(
    '[Training.overview] latest_valid_training_focus=',
    o?.latest_valid_training_focus ?? '(n/a)'
  )
  console.log(
    '[Training.overview] recommended_continue_focus=',
    o?.recommended_continue_focus ?? '(n/a)'
  )
  console.log('[Training.overview] incoming_focus_priority=', incomingFocusPriority.value)
}

function resumeLastValidTrainingConfig() {
  const o = validTrainingOverviewFromApi.value
  if (!o?.overview_ready) {
    trainingFeedback(
      'resume_last_config',
      'warning',
      '暂时没有可复用的有效训练概况，请先完成至少一轮有效训练后再试。'
    )
    return
  }
  contentFocusDowngraded.value = false
  const sp = String(o.latest_valid_scoring_profile || '').trim().toLowerCase()
  if (sp === 'interview' || sp === 'defense') {
    trainingScoringProfile.value = sp
  }
  const dm = String(o.latest_valid_defense_material_mode || '').trim().toLowerCase()
  if (dm === 'without_ppt') {
    trainingDeckMode.value = 'none'
  } else if (dm === 'with_ppt') {
    trainingDeckMode.value = 'with_deck'
  }
  const lf = String(o.latest_valid_training_focus ?? 'none').trim().toLowerCase()
  if (lf === 'none' || lf === '') {
    recommendedTrainingFocus.value = null
  } else {
    const k = normalizeIncomingFocusKey(lf)
    recommendedTrainingFocus.value = k
  }
  trainingFocusSource.value = 'resume_last_config'

  if (recommendedTrainingFocus.value === 'content' && trainingDeckMode.value === 'none') {
    recommendedTrainingFocus.value = null
    trainingFocusSource.value = 'none'
    contentFocusDowngraded.value = true
    persistAndSyncTrainingQuery('resume_last_config')
    logTrainingResume('resume_last_config')
    logTrainingFocus({ guidance_mode: 'normal_downgraded_content', downgraded_from_content: true })
    logTrainingOverviewState()
    trainingFeedback(
      'resume_last_config',
      'warning',
      '无课件模式下不适用「内容讲解」专项，已自动改为综合训练。可直接点击「开始训练」。'
    )
    return
  }

  persistAndSyncTrainingQuery('resume_last_config')
  logTrainingResume('resume_last_config')
  logTrainingFocus({ downgraded_from_content: false })
  logTrainingOverviewState()
  trainingFeedback(
    'resume_last_config',
    'success',
    '已应用最近一次有效训练的模式与专项，可直接点击「开始训练」。'
  )
}

function applyRecommendedFocusConfig() {
  const o = validTrainingOverviewFromApi.value
  if (!o?.overview_ready) {
    trainingFeedback(
      'apply_recommended_focus',
      'warning',
      '暂时没有有效训练概况，无法应用推荐方向。'
    )
    return
  }
  const rec0 = o.recommended_continue_focus
  if (rec0 == null || String(rec0).trim() === '') {
    trainingFeedback('apply_recommended_focus', 'warning', '暂时没有可用的推荐方向，可先选常规训练或完成更多有效训练后再看建议。')
    return
  }
  contentFocusDowngraded.value = false
  trainingFocusSource.value = 'apply_recommended_focus'
  const raw = String(rec0).trim().toLowerCase()
  if (raw === 'none') {
    recommendedTrainingFocus.value = null
    persistAndSyncTrainingQuery('apply_recommended_focus')
    logTrainingResume('apply_recommended_focus')
    logTrainingFocus({ guidance_mode: 'normal', downgraded_from_content: false })
    logTrainingOverviewState()
    trainingFeedback(
      'apply_recommended_focus',
      'success',
      '已按建议设为常规训练，可直接点击「开始训练」。'
    )
    return
  }
  const k = normalizeIncomingFocusKey(rec0)
  if (!k) {
    trainingFeedback(
      'apply_recommended_focus',
      'warning',
      '当前建议方向暂时无法套用，你可先选手动专项或常规训练。'
    )
    return
  }
  recommendedTrainingFocus.value = k
  if (k === 'content' && trainingDeckMode.value === 'none') {
    recommendedTrainingFocus.value = null
    trainingFocusSource.value = 'none'
    contentFocusDowngraded.value = true
    persistAndSyncTrainingQuery('apply_recommended_focus')
    logTrainingResume('apply_recommended_focus')
    logTrainingFocus({ guidance_mode: 'normal_downgraded_content', downgraded_from_content: true })
    logTrainingOverviewState()
    trainingFeedback(
      'apply_recommended_focus',
      'warning',
      '无课件模式下不适用「内容讲解」专项，已改为综合训练。可直接点击「开始训练」。'
    )
    return
  }
  persistAndSyncTrainingQuery('apply_recommended_focus')
  logTrainingResume('apply_recommended_focus')
  logTrainingFocus({ downgraded_from_content: false })
  logTrainingOverviewState()
  trainingFeedback(
    'apply_recommended_focus',
    'success',
    '已切换为推荐训练方向，可按当前提示继续并点击「开始训练」。'
  )
}

watch(
  [validTrainingOverviewFromApi, recommendedTrainingFocus, trainingFocusSource],
  () => {
    logTrainingOverviewState()
  },
  { flush: 'post' }
)

const apiResult = ref('')
const sessionId = ref('')

const firstTimeTrainingHintVisible = computed(() => {
  void preferencesRevision.value
  if (readAppPreferences().show_first_time_hints === false) return false
  if (sessionId.value) return false
  if (unfinishedResumePrompt.value) return false
  if (validTrainingOverviewLoadFailed.value) return false
  if (trainingHistoryTotalCount.value == null) return false
  if (trainingHistoryTotalCount.value > 0) return false
  if (firstTrainingHintDismissed.value) return false
  return true
})

const showRecentValidTrainingReminder = computed(() => {
  void preferencesRevision.value
  return readAppPreferences().show_recent_valid_reminder !== false
})

watch(
  firstTimeTrainingHintVisible,
  (v) => {
    console.log('[Training.empty] first_time_hint_visible=', v)
    if (v) trainingTopAuxHintsCollapse.value = ['aux']
  },
  { flush: 'post' }
)

watch(
  [resumeMediaHintVisible, sessionId],
  () => {
    if (sessionId.value && resumeMediaHintVisible.value) {
      trainingSupplementalCollapse.value = ['sup']
    }
  },
  { flush: 'post' }
)

/**
 * 训练会话内阶段：lecture=讲解演示（默认），qa=答辩问答。
 * 未开始训练（无 sessionId）时门控由 showQaSection 等计算属性处理。
 */
const sessionPhase = ref('lecture')
/** 调试：讲解阶段也可打开批量出题与问答（真实答辩时序的兜底入口） */
const trainingFlowDebugMode = ref(false)
/** 进入 QA 且系统自动选题成功后的提示 */
const qaPhaseAutoQuestionTip = ref('')
/** 首轮评估后自动追问成功时的答辩向提示 */
const qaAutoFollowupHint = ref('')
/** 正式会话下：首轮主问题评估后是否已尝试过自动追问（避免重复请求） */
const autoFollowupFirstRoundAttempted = ref(false)
/** 备用批量题库是否展开（正式答辩默认折叠；调试模式默认展开） */
const mockQuestionBankExpanded = ref(false)

watch(
  () => demoModeUi.value.active,
  (a) => {
    if (a) trainingFlowDebugMode.value = false
  }
)

/**
 * 答辩问答阶段内：是否已完成至少一次「老师主问题」评估（manual / auto_generated）。
 * 用于首轮评估完成前隐藏「生成追问」。
 */
const primaryTeacherQaEvalDone = ref(false)
const isGeneratingMockBatch = ref(false)
const errorMessage = ref('')
/** 停止训练流程进行中（展示「正在提交训练结果」等） */
const isStopping = ref(false)
const isSubmittingSession = ref(false)
const isAnalyzingAudio = ref(false)
const isAnalyzingVision = ref(false)
const loading = ref(false)
const stopSuccess = ref(false)

/** 与后端 configs.scoring_profiles 键一致：defense=答辩，interview=面试 */
const trainingScoringProfile = ref('defense')
const trainingModeLabel = computed(() =>
  trainingScoringProfile.value === 'interview' ? '面试模式' : '答辩模式'
)

/** 有课件答辩（默认）| 无课件答辩：影响自检阻塞项、课件主区展示，并在 stop 时映射为 defense_material_mode */
const trainingDeckMode = ref('with_deck')
const trainingDeckModeLabel = computed(() =>
  trainingDeckMode.value === 'with_deck'
    ? '有课件答辩：上传课件后可做内容对齐与猜页'
    : '无课件答辩：本轮不进行课件匹配'
)

const trainingConfigSummaryLine = computed(() => {
  const focusText = trainingFocusBannerLabel.value || TRAINING_FOCUS_LABEL.none
  return `${trainingModeLabel.value} · ${trainingDeckModeLabel.value} · 专项：${focusText}`
})

/** 与后端结果链一致：with_deck → with_ppt；none → without_ppt */
const defenseMaterialMode = computed(() =>
  trainingDeckMode.value === 'with_deck' ? 'with_ppt' : 'without_ppt'
)
/** 是否展示课件上传/匹配主区块（无课件模式下隐藏，避免误认必须上传） */
const pptPanelVisible = computed(() => trainingDeckMode.value === 'with_deck')

watch(
  pptPanelVisible,
  (v) => {
    console.log('[Training.mode] ppt panel visible=', v)
  },
  { immediate: true }
)

watch(
  [trainingScoringProfile, trainingDeckMode, recommendedTrainingFocus, trainingFocusSource],
  () => {
    if (!sessionId.value) {
      saveTrainingPageDraft()
    }
  },
  { flush: 'post' }
)

// 训练指标
const metrics = ref({
  speech_rate: 238,
  pause_count: 11,
  avg_pause_sec: 0.9,
  filler_count: 4,
  forward_gaze_ratio: 0.63,
  downward_head_ratio: 0.18,
  posture_stability: 0.76
})

// PPT 相关
const selectedFile = ref(null)
/** PPT 上传解析进行中（仅前端口径，用于状态条） */
const isUploadingPpt = ref(false)
/** 最近一次点击「上传 PPT」是否以失败结束（新选择文件或再次上传时清零） */
const pptUploadFailed = ref(false)
const pptInfo = ref(null)
const pptTextData = ref(null)
const selectedPageIndex = ref(null)
const spokenText = ref('')
const matchResult = ref(null)
const lastPptMatchResult = ref(null)
/** 自动猜页完整结果（仅当猜页成功且达到阈值时可在 stop 时降级为 ppt_match） */
const lastAutoPptMatchResult = ref(null)
/** 问答本轮来源：manual | auto_generated | followup_generated */
const qaRoundSource = ref('manual')
/** 批量列表中选中的题目下标，-1 表示未选 */
const selectedMockQuestionIndex = ref(-1)
/** 当前选中的批量题条目（用于展示与排障） */
const selectedMockQuestion = ref(null)
/** 手动单题评估结果（stop 时优先于自动） */
const lastManualQaResult = ref(null)
/** 批量选题评估结果 */
const lastAutoQaResult = ref(null)
/** 弱点驱动追问评估结果（stop 时优先于批量自动题、次于手动） */
const lastFollowupQaResult = ref(null)
/** 规则追问列表（与接口 followup_questions 对齐） */
const followupQuestions = ref([])
const followupSectionVisible = ref(false)
const selectedFollowupIndex = ref(-1)
/** 当前选中的追问条目快照（与列表项字段对齐，便于展示与排障） */
const selectedFollowupQuestion = ref(null)
const lastFollowupQuestionsSnapshot = ref(null)
/** 最近一次 /qa/followup 返回的 provider 元数据，写入追问轮 qa_result 供 Result/Report 展示 */
const lastFollowupGenerationContext = ref(null)
/** 最近一次首问 /qa/generate 的 provider 元数据，写入首轮 qa_result 供 Result/Report 展示 */
const lastQuestionGenerationContext = ref(null)
const selectedFollowupMeta = ref(null)
const isGeneratingFollowup = ref(false)
const currentQaSource = computed(() => qaRoundSource.value)
const qaChannelLabel = computed(() => {
  const s = qaRoundSource.value
  if (s === 'auto_generated') {
    const ctx = lastQuestionGenerationContext.value
    const kind = String(ctx?.question_provider_kind || 'rule').toLowerCase()
    const fb = ctx?.question_fallback_to_rule === true
    if (kind === 'hybrid' && fb) return '老师提问（混合首问·已回退规则）'
    if (kind === 'hybrid') return '老师提问（混合首问）'
    if (kind === 'model') return '老师提问（模型首问）'
    return '老师提问（规则首问）'
  }
  if (s === 'followup_generated') {
    const ctx = lastFollowupGenerationContext.value
    const kind = String(ctx?.followup_provider_kind || 'rule').toLowerCase()
    const fb = ctx?.followup_fallback_to_rule === true
    const be = String(ctx?.followup_generation_meta?.followup_model_backend || '').toLowerCase()
    if (kind === 'hybrid' && fb) return '老师追问 · 混合追问（已回退规则）'
    if (kind === 'hybrid') return '老师追问（混合追问）'
    if (kind === 'model') {
      if (be === 'mock') return '老师追问（模型追问·mock）'
      if (be) return `老师追问（模型追问·${be}）`
      return '老师追问（模型追问）'
    }
    return '老师追问（规则追问）'
  }
  return '单页生成问题（手动）'
})

/** 与 Result/Report 的 resolveFollowupTaxonomyShortLabel 同口径 */
function resolveFollowupTaxonomyShortLabel(ctx) {
  if (!ctx || typeof ctx !== 'object') return '规则追问'
  const kind = String(ctx.followup_provider_kind || 'rule').toLowerCase()
  const fb = ctx.followup_fallback_to_rule === true
  if (kind === 'hybrid' && fb) return '混合追问（已回退规则）'
  if (kind === 'hybrid') return '混合追问'
  if (kind === 'model') return '模型追问'
  return '规则追问'
}

/** 与 Result/Report 一致：规则 / 模型 / 混合 / 混合（已回退规则） */
const followupTaxonomyLabel = computed(() => {
  const ctx = lastFollowupGenerationContext.value
  if (!ctx) return ''
  return resolveFollowupTaxonomyShortLabel(ctx)
})

const followupProviderDebugLine = computed(() => {
  const ctx = lastFollowupGenerationContext.value
  if (!ctx) return ''
  const meta = ctx.followup_generation_meta || {}
  let t = followupTaxonomyLabel.value || meta.provider_label || '—'
  if (meta.generation_mode) t += ` · ${meta.generation_mode}`
  if (meta.followup_model_backend != null && String(meta.followup_model_backend).trim() !== '')
    t += ` · backend=${meta.followup_model_backend}`
  return t
})

const questionProviderDebugLine = computed(() => {
  const ctx = lastQuestionGenerationContext.value
  if (!ctx) return ''
  const meta = ctx.question_generation_meta || {}
  let t = meta.provider_label || '—'
  if (ctx.question_fallback_to_rule) t += '（已回退规则）'
  if (meta.generation_mode) t += ` · ${meta.generation_mode}`
  return t
})
/** 展示区：首轮为主问题，追问轮为老师追问 */
const teacherQuestionLabel = computed(() =>
  qaRoundSource.value === 'followup_generated' ? '老师追问' : '老师提问'
)
const qaVoiceAnswerTitle = computed(() => {
  if (qaRoundSource.value === 'followup_generated') return '请继续语音回答'
  if (trainingFlowDebugMode.value) return '学生回答（默认语音）'
  return '请开始语音回答'
})
/** 自动猜页纳入训练闭环：置信度或规则分门槛 */
const AUTO_GUESS_MIN_CONFIDENCE = 0.5
const AUTO_GUESS_MIN_MATCH_SCORE = 20
/**
 * 讲解阶段自动猜页持久化（进入答辩问答阶段不清空）：
 * *Raw = API 原始；*Plain = 已转换为与 /session/stop、评分一致的正式 ppt_match。
 */
const lectureLatestAutoGuessRaw = ref(null)
const bestLectureAutoGuessRaw = ref(null)
const lectureLatestAutoPptMatchPlain = ref(null)
const bestLectureAutoPptMatchPlain = ref(null)
/** 进入答辩阶段时自动猜页得到的正式 ppt_match（优先于历史 best/latest 链用于 stop） */
const lectureAutoGuessFinalMatch = ref(null)

const clearLectureAutoGuessPersistence = () => {
  lectureLatestAutoGuessRaw.value = null
  bestLectureAutoGuessRaw.value = null
  lectureLatestAutoPptMatchPlain.value = null
  bestLectureAutoPptMatchPlain.value = null
  lectureAutoGuessFinalMatch.value = null
  lastAutoPptMatchResult.value = null
  autoGuessResult.value = null
}

const autoGuessApiResponseLooksSuccessful = (response) => {
  if (!response || typeof response !== 'object') return false
  if (response.best_page_index == null || response.best_page_index === '') return false
  if (response.ok === false || response.success === false) return false
  const msg = response.message
  if (typeof msg === 'string' && /失败|错误|fail|error|未找到|不存在|无效/i.test(msg)) return false
  return true
}

/**
 * 将 /ppt/match_v1 自动猜页结果转为正式 ppt_match（与后端 PptMatch / score_session 一致）。
 * 只要后端返回了 best_page_index（非 zero-hit），即生成；不再用语义分/置信度门槛拦截提交。
 */
const convertAutoGuessToPlainPptMatch = (ag, pptPages) => {
  if (!ag || ag.best_page_index == null || ag.best_page_index === '') return null
  const pageIdx = Number(ag.best_page_index)
  if (!Number.isFinite(pageIdx)) return null
  const tops = Array.isArray(ag.top_candidates) ? ag.top_candidates : []
  let top0 =
    tops.find((c) => Number(c?.page_index) === pageIdx) || (tops.length ? tops[0] : null)
  const matchScore = Number(top0?.match_score ?? ag.best_match_score ?? 0)
  const kwCov = Number(top0?.keyword_coverage ?? 0)
  let title = String(top0?.title || ag.best_title || '').trim()
  const pages = Array.isArray(pptPages) ? pptPages : []
  const pageRow = pages.find((p) => Number(p?.page_index) === pageIdx)
  if (!title && pageRow?.title) title = String(pageRow.title).trim()
  if (!title) title = `第 ${pageIdx} 页`
  let matchedKw = []
  let missingKw = []
  if (top0 && Array.isArray(top0.matched_keywords)) {
    matchedKw = top0.matched_keywords.map((k) => String(k).trim()).filter(Boolean)
    missingKw = Array.isArray(top0.missing_keywords)
      ? top0.missing_keywords.map((k) => String(k).trim()).filter(Boolean)
      : []
  } else if (pageRow && Array.isArray(pageRow.keywords)) {
    missingKw = pageRow.keywords.map((k) => String(k).trim()).filter(Boolean)
  }
  return {
    page_index: pageIdx,
    title,
    match_score: matchScore,
    keyword_coverage: kwCov,
    matched_keywords: matchedKw,
    missing_keywords: missingKw,
    comment: `自动猜页（置信度 ${ag.confidence ?? 0}；规则分 ${matchScore}）`,
    match_source: 'auto_guess',
  }
}

/** 每次猜页成功后写入 raw + 正式 plain；供 stop 与追问接口 */
const recordLectureAutoGuessSnapshot = (response) => {
  console.log('[Training] lecture auto guess raw', response)
  if (!autoGuessApiResponseLooksSuccessful(response)) {
    console.warn(
      '[Training] lecture auto guess unsuccessful response; preserve existing lecture content chain (no clear)'
    )
    return
  }
  const snap = JSON.parse(JSON.stringify(response))
  lectureLatestAutoGuessRaw.value = snap
  lastAutoPptMatchResult.value = snap
  const score = Number(snap.best_match_score ?? 0)
  const prev = bestLectureAutoGuessRaw.value
  const prevScore = prev != null ? Number(prev.best_match_score ?? 0) : -Infinity
  if (score >= prevScore) {
    bestLectureAutoGuessRaw.value = snap
  }
  const plain = convertAutoGuessToPlainPptMatch(snap, pptInfo.value?.pages || [])
  if (plain) {
    const pcopy = JSON.parse(JSON.stringify(plain))
    lectureLatestAutoPptMatchPlain.value = pcopy
    console.log('[Training] lecture auto guess converted plain ppt_match', pcopy)
    const prevPlain = bestLectureAutoPptMatchPlain.value
    const prevMs = prevPlain != null ? Number(prevPlain.match_score) : -Infinity
    if (Number(plain.match_score) >= prevMs) {
      bestLectureAutoPptMatchPlain.value = JSON.parse(JSON.stringify(plain))
    }
    console.log('[Training] bestLecturePptMatchPlain', bestLectureAutoPptMatchPlain.value)
  } else {
    lectureLatestAutoPptMatchPlain.value = null
  }
  console.log('[Training] lecture latest auto ppt match', {
    page: snap.best_page_index,
    score: snap.best_match_score,
    confidence: snap.confidence,
    bestPage: bestLectureAutoGuessRaw.value?.best_page_index,
    bestScore: bestLectureAutoGuessRaw.value?.best_match_score,
  })
}

const resolveLectureAutoGuessRawForStop = () =>
  bestLectureAutoGuessRaw.value || lectureLatestAutoGuessRaw.value || lastAutoPptMatchResult.value

/** 手动 / 自动猜页 */
const pptMatchMode = ref('manual')
const autoGuessResult = ref(null)
const mockQuestionsList = ref([])
const currentQaQuestion = ref('')
const currentQaExpectedKeywords = ref([])
const qaAnswerText = ref('')
const qaEvaluationResult = ref(null)
const lastQaResult = ref(null)
/** 问答作答：默认语音；文本仅兜底/调试（独立录音链，不写 audioAnalysis） */
const qaAnswerMode = ref('voice')
/** 问答阶段：是否正在录制语音作答（与讲解 isRecording 分离） */
const isQaAnswerRecording = ref(false)
const isAnalyzingQaAudio = ref(false)
/** 是否正在请求 /qa/evaluate（语音结束后的自动评估或文本评估） */
const qaAnswerEvaluatePending = ref(false)
const qaAnswerAudioBlob = ref(null)
const qaAnswerTranscript = ref('')
const lastQaAnswerInputMode = ref('voice')
const qaTextFallbackExpanded = ref(false)
const qaAnswerMediaStream = ref(null)
const qaAnswerMediaRecorder = ref(null)
const qaAnswerChunks = ref([])
const qaAnswerRecordingMimeType = ref('')
const isRecording = ref(false)
/** 讲解阶段麦克风录制状态（与问答 isQaAnswerRecording 分离，供 UI 与语音作答互斥判断） */
const isLectureRecordingAudio = computed(() => isRecording.value)

/** 语音作答链路日志：首轮老师题 vs 规则追问 */
const resolveQaAnswerLogSource = () =>
  qaRoundSource.value === 'followup_generated' ? 'followup' : 'first_question'
const mediaRecorder = ref(null)
const mediaStream = ref(null)
const audioChunks = ref([])
const audioAnalysis = ref(null)
const recordingMimeType = ref('')
const videoRecorder = ref(null)
const videoStream = ref(null)
const videoChunks = ref([])
const visionAnalysis = ref(null)
const videoMimeType = ref('')
const isVideoRecording = ref(false)
const cameraPreviewRef = ref(null)
const videoStopRequested = ref(false)
/** 预留：若后续增加轮询/心跳，在此注册并在 stopLocalRecording 中清理 */
const recordingIntervalIds = ref([])
const recordingTimeoutIds = ref([])

/** 讲解阶段文本上下文（口述框 + 讲解音频转写）；仅用于日志，与 QA 作答文本分离 */
const lectureTranscriptContextSummary = computed(() => {
  const st = String(spokenText.value ?? '').trim()
  const tr =
    audioAnalysis.value && typeof audioAnalysis.value === 'object'
      ? String(audioAnalysis.value.transcript ?? '').trim()
      : ''
  return { spokenTextLen: st.length, lectureTranscriptLen: tr.length }
})

/** 与后端 ppt_store 对齐：上传写入 + localStorage，避免刷新后丢 ref */
const cachedPptIdFallback = ref('')

const resolveCurrentPptId = () => {
  const fromPptInfo = String(pptInfo.value?.ppt_id ?? '').trim()
  if (fromPptInfo) return fromPptInfo
  const cached = String(cachedPptIdFallback.value ?? '').trim()
  if (cached) return cached
  try {
    return String(readUserScopedItem(localStorage, LAST_PPT_ID_STORAGE_KEY) ?? '').trim() || ''
  } catch {
    return ''
  }
}

const hasPptContext = computed(() => !!resolveCurrentPptId())
const displayPptId = computed(() => resolveCurrentPptId())
const pptPagesForUi = computed(() => (Array.isArray(pptInfo.value?.pages) ? pptInfo.value.pages : []))

const hasSelectedPptFile = computed(() => !!selectedFile.value)

/** 后端 pages 或 document 是否具备训练/猜页所需结构（与 qa.py 等 gate 对齐） */
const pptServerPayloadLooksReady = (pages, document) => {
  if (Array.isArray(pages) && pages.length > 0) return true
  if (document && typeof document === 'object') {
    if (Array.isArray(document.pages) && document.pages.length > 0) return true
    if (Array.isArray(document.outline) && document.outline.length > 0) return true
  }
  return false
}

/**
 * 仅当本轮在前端持有完整上传结果：有效 ppt_id + pages 或 document。
 * 不将「仅 localStorage / 仅选中文件」视为就绪。
 */
const hasUploadedPptReady = computed(() => {
  const pid = String(pptInfo.value?.ppt_id ?? '').trim()
  if (!pid) return false
  const pages = pptInfo.value?.pages
  const document = pptInfo.value?.document
  return pptServerPayloadLooksReady(
    Array.isArray(pages) ? pages : [],
    document,
  )
})

/** 存在 ppt_id 兜底（内存/localStorage）但本轮未验证到可解析结构 */
const hasStalePptIdOnly = computed(() => {
  if (hasUploadedPptReady.value) return false
  if (hasSelectedPptFile.value) return false
  if (pptUploadFailed.value) return false
  if (isUploadingPpt.value) return false
  return !!String(resolveCurrentPptId() || '').trim()
})

/**
 * PPT 状态机（仅展示）：no_file | selected_not_uploaded | uploading | ready | failed | stale_cache
 */
const pptUxStatus = computed(() => {
  if (isUploadingPpt.value) return 'uploading'
  if (pptUploadFailed.value) return 'failed'
  if (hasUploadedPptReady.value) return 'ready'
  if (hasSelectedPptFile.value) return 'selected_not_uploaded'
  if (hasStalePptIdOnly.value) return 'stale_cache'
  return 'no_file'
})

const pptStatusUserMessage = computed(() => {
  switch (pptUxStatus.value) {
    case 'uploading':
      return '课件正在上传解析，请稍候'
    case 'failed':
      return '课件上传或解析失败，请重试或在本场不使用课件时改选「无课件答辩」'
    case 'ready':
      return '课件已就绪，本轮可启用内容匹配与课件增强提问。'
    case 'selected_not_uploaded':
      return '已选择课件文件，请点击「上传 PPT」完成解析；若本场不用课件可改选「无课件答辩」'
    case 'stale_cache':
      return '检测到此前保存的课件编号；需要课件时请重新上传，或改选「无课件答辩」直接训练'
    case 'no_file':
    default:
      return '尚未上传课件：请在下方选择 .pptx 并点击「上传 PPT」；若本轮不需要课件，可改选「无课件答辩」。'
  }
})

/** 训练前自检（V1）：不改动主流程，仅门控「开始训练」与提示 */
const preflightLoading = ref(false)
const preflightRows = ref([])
const preflightDebugPayload = ref(null)
const lastPreflightNoBlockers = ref(false)

const resolveBackendHealthUrl = () => {
  const raw = String(import.meta.env.VITE_API_BASE || '').trim()
  if (/^https?:\/\//i.test(raw)) {
    let u = raw.replace(/\/+$/, '')
    if (/\/api$/i.test(u)) u = u.slice(0, -4)
    return `${u}/health`
  }
  return 'http://127.0.0.1:8000/health'
}

const queryMediaPermissionState = async (kind) => {
  try {
    if (!navigator.permissions?.query) return 'unsupported'
    const name = kind === 'camera' ? 'camera' : 'microphone'
    const r = await navigator.permissions.query({ name })
    return r?.state || 'unknown'
  } catch {
    return 'unsupported'
  }
}

const preflightDebugText = computed(() => {
  if (!preflightDebugPayload.value) return ''
  try {
    return JSON.stringify(preflightDebugPayload.value, null, 2)
  } catch {
    return ''
  }
})

const preflightHasBlockers = computed(() => {
  if (sessionId.value) return false
  return preflightRows.value.some((r) => r.status === 'block')
})

const preflightHasWarnings = computed(() => {
  if (sessionId.value) return false
  return preflightRows.value.some((r) => r.status === 'warn')
})

const preflightWarningBanner = computed(() => {
  if (sessionId.value || preflightLoading.value) return ''
  if (preflightHasBlockers.value || !preflightHasWarnings.value) return ''
  const msgs = preflightRows.value.filter((r) => r.status === 'warn').map((r) => r.message)
  return `可以开始训练。请注意：${[...new Set(msgs)].join('；')}`
})

const deckPreflightCapabilityHint = computed(() => {
  if (sessionId.value) return ''
  if (trainingDeckMode.value === 'none') {
    if (hasUploadedPptReady.value) {
      return '提示：无课件模式下主界面不展示课件上传区；若仍需课件能力，请切回「有课件答辩」。'
    }
    return ''
  }
  if (hasUploadedPptReady.value) {
    return '当前为「有课件答辩」且课件已就绪：内容匹配与课件相关能力可用。'
  }
  return '当前为「有课件答辩」：请完成课件上传与解析（见下方课件区），或暂切「无课件答辩」跳过课件要求。'
})

const preflightStatusLabel = (s) => {
  if (s === 'pass') return '通过'
  if (s === 'warn') return '提示'
  if (s === 'block') return '未通过'
  return String(s || '')
}

const runPreflightChecks = async (opts = {}) => {
  const fromButton = opts.fromButton === true
  console.log('[Training.preflight] begin')
  preflightLoading.value = true
  preflightDebugPayload.value = null
  const rows = []
  const add = (row) => rows.push(row)

  const st = pptUxStatus.value
  const deckMode = trainingDeckMode.value
  const requireDeck = deckMode === 'with_deck'

  if (st === 'ready') {
    add({
      id: 'ppt',
      label: '课件',
      status: 'pass',
      message: '课件已就绪，本轮可启用内容匹配与课件增强提问。',
    })
  } else if (st === 'uploading') {
    add({
      id: 'ppt',
      label: '课件',
      status: 'block',
      message: '课件正在上传解析，请稍候完成后再开始训练。',
    })
  } else if (st === 'failed') {
    if (requireDeck) {
      add({
        id: 'ppt',
        label: '课件',
        status: 'block',
        message: '「有课件答辩」模式下课件上传或解析失败，请重新选择文件并上传后再开始。',
      })
    } else {
      add({
        id: 'ppt',
        label: '课件',
        status: 'warn',
        message:
          '上次课件上传未成功；仍可开始训练，但本轮不进行内容匹配与基于课件的问题增强。',
      })
    }
  } else if (st === 'selected_not_uploaded') {
    if (requireDeck) {
      add({
        id: 'ppt',
        label: '课件',
        status: 'block',
        message: '「有课件答辩」模式下请先点击「上传 PPT」完成解析后再开始训练。',
      })
    } else {
      add({
        id: 'ppt',
        label: '课件',
        status: 'warn',
        message:
          '已选择课件文件但尚未完成上传。若本场不使用课件可直接开始；需要课件时请先上传。',
      })
    }
  } else if (st === 'stale_cache') {
    if (requireDeck) {
      add({
        id: 'ppt',
        label: '课件',
        status: 'block',
        message: '「有课件答辩」模式下检测到旧课件记录，请重新上传并解析课件后再开始。',
      })
    } else {
      add({
        id: 'ppt',
        label: '课件',
        status: 'warn',
        message:
          '检测到旧课件记录；无课件模式下仍可开始训练。若需课件能力请重新上传。',
      })
    }
  } else {
    if (requireDeck) {
      add({
        id: 'ppt',
        label: '课件',
        status: 'block',
        message: '当前为「有课件答辩」模式，请先上传并解析课件后再开始训练。',
      })
    } else {
      add({
        id: 'ppt',
        label: '课件',
        status: 'pass',
        message:
          '当前为无课件答辩：不要求上传课件。若需内容匹配或猜页，请切换为「有课件答辩」后上传课件。',
      })
    }
  }

  let healthJson = null
  let providerJson = null

  try {
    const hUrl = resolveBackendHealthUrl()
    const hr = await fetch(hUrl, { method: 'GET', headers: { Accept: 'application/json' } })
    if (!hr.ok) {
      console.log('[Training.load] preflight_error=', 'health_http')
      add({
        id: 'backend',
        label: '训练服务',
        status: 'block',
        message: '无法连接训练服务，请确认后端已启动后点击「重新检查」。',
      })
    } else {
      healthJson = await hr.json()
      add({ id: 'backend', label: '训练服务', status: 'pass', message: '训练服务已连接，可以开始会话。' })
    }
  } catch {
    console.log('[Training.load] preflight_error=', 'health_check')
    add({
      id: 'backend',
      label: '训练服务',
      status: 'block',
      message: '无法连接训练服务，请检查网络或确认后端已启动后点击「重新检查」。',
    })
  }

  const backendBlocked = rows.some((r) => r.id === 'backend' && r.status === 'block')
  if (!backendBlocked) {
    try {
      providerJson = await getJson('/system/provider-status')
      const speech = String(providerJson.speech_provider || '').toLowerCase()
      const vision = String(providerJson.vision_provider || '').toLowerCase()
      const baseConfigured = !!providerJson.ascend_base_url_configured
      const asc = providerJson.ascend_health_check || {}
      const reachable = asc.reachable

      const speechHint = speech === 'ascend' ? '当前使用开发板进行语音分析' : '当前使用本机进行语音分析'
      const visionHint = vision === 'ascend' ? '当前使用开发板进行画面与仪态分析' : '当前使用本机进行画面与仪态分析'

      if (speech === 'ascend') {
        if (!baseConfigured) {
          add({
            id: 'speech_provider',
            label: '语音分析',
            status: 'block',
            message: '已配置为使用开发板，但未设置开发板地址，请联系管理员检查后端环境变量。',
          })
        } else if (reachable === false) {
          add({
            id: 'speech_provider',
            label: '语音分析',
            status: 'block',
            message: '开发板服务暂不可达，将无法使用当前配置的语音分析。',
          })
        } else {
          add({ id: 'speech_provider', label: '语音分析', status: 'pass', message: `${speechHint}。` })
        }
      } else {
        add({ id: 'speech_provider', label: '语音分析', status: 'pass', message: `${speechHint}。` })
      }

      if (vision === 'ascend') {
        if (!baseConfigured) {
          add({
            id: 'vision_provider',
            label: '画面分析',
            status: 'block',
            message: '已配置为使用开发板，但未设置开发板地址，请联系管理员检查后端环境变量。',
          })
        } else if (reachable === false) {
          add({
            id: 'vision_provider',
            label: '画面分析',
            status: 'block',
            message: '开发板服务暂不可达，将无法使用当前配置的视觉与仪态分析。',
          })
        } else {
          add({ id: 'vision_provider', label: '画面分析', status: 'pass', message: `${visionHint}。` })
        }
      } else {
        add({ id: 'vision_provider', label: '画面分析', status: 'pass', message: `${visionHint}。` })
      }

      const dp = String(providerJson.document_parser_provider || 'basic')
      add({
        id: 'doc_parser',
        label: '课件解析',
        status: 'pass',
        message: `解析线路为「${dp}」，可与当前课件上传流程配合使用。`,
      })
    } catch {
      console.log('[Training.load] preflight_error=', 'provider_status')
      add({
        id: 'providers',
        label: '运行配置',
        status: 'warn',
        message: '暂时无法读取语音/视觉运行配置（可能网络或服务繁忙）。可先尝试开始训练；若异常请点「重新检查」。',
      })
    }
  }

  const [micState, camState] = await Promise.all([
    queryMediaPermissionState('microphone'),
    queryMediaPermissionState('camera'),
  ])

  const addMedia = (state, label, id) => {
    if (state === 'denied') {
      add({
        id,
        label,
        status: 'block',
        message: `未授权${label}，请在浏览器设置中允许本站使用${label}后再试。`,
      })
    } else if (state === 'prompt' || state === 'unknown') {
      add({
        id,
        label,
        status: 'warn',
        message: `尚未确认${label}权限，开始训练时浏览器将请求授权，请选择「允许」。`,
      })
    } else if (state === 'granted') {
      add({ id, label, status: 'pass', message: `${label}权限已就绪。` })
    } else {
      add({
        id,
        label,
        status: 'warn',
        message: `无法自动检测${label}状态，请确认设备已连接，开始训练时按提示授权。`,
      })
    }
  }
  addMedia(micState, '麦克风', 'mic')
  addMedia(camState, '摄像头', 'cam')

  preflightRows.value = rows
  preflightDebugPayload.value = {
    health: healthJson,
    provider_status: providerJson,
    media: { microphone: micState, camera: camState },
    ppt_ux: st,
    training_deck_mode: deckMode,
    ppt_require_deck: requireDeck,
  }

  const blockers = rows.filter((r) => r.status === 'block')
  const warnings = rows.filter((r) => r.status === 'warn')
  lastPreflightNoBlockers.value = blockers.length === 0
  console.log(
    '[Training.preflight] ppt optional status=',
    JSON.stringify({
      deckMode,
      pptUx: st,
      requireDeck,
      pptRow: rows.find((r) => r.id === 'ppt') || null,
    })
  )
  console.log('[Training.preflight] blockers=', blockers.map((r) => r.id))
  console.log('[Training.preflight] warnings=', warnings.map((r) => r.id))
  preflightLoading.value = false

  if (fromButton) {
    if (blockers.length > 0) {
      const first = blockers[0]
      trainingFeedback(
        'preflight_check',
        'warning',
        `自检未通过：${first.message}。处理后可再点「重新检查」。`
      )
    } else if (warnings.length > 0) {
      trainingFeedback(
        'preflight_check',
        'warning',
        `自检已完成：有 ${warnings.length} 项需要你留意，多数情况下仍可尝试开始；若涉及麦克风或摄像头，开始训练时请点「允许」。`
      )
    } else {
      trainingFeedback('preflight_check', 'success', '自检已完成：关键项已通过，可按当前配置开始训练。')
    }
  }
}

watch(preflightLoading, (v) => {
  console.log('[Training.load] preflight_loading=', v)
})

watch(trainingDeckMode, (nv, ov) => {
  if (ov !== undefined) {
    console.log('[Training.mode] switched defenseMaterialMode=', defenseMaterialMode.value)
  }
  if (nv === 'with_deck') {
    contentFocusDowngraded.value = false
  }
  if (nv === 'none' && recommendedTrainingFocus.value === 'content') {
    recommendedTrainingFocus.value = null
    trainingFocusSource.value = 'manual'
    contentFocusDowngraded.value = true
    logTrainingFocus({ guidance_mode: 'normal', downgraded_from_content: true })
  }
  if (!sessionId.value) {
    runPreflightChecks()
  }
})

const sessionPhaseLabel = computed(() =>
  sessionPhase.value === 'qa' ? '答辩问答' : '讲解阶段'
)

/** 默认主流程顶部标题（非调试时偏答辩情景） */
const pageHeroTitle = computed(() => {
  const interview = trainingScoringProfile.value === 'interview'
  if (!sessionId.value) return interview ? '面试训练' : '答辩训练'
  if (trainingFlowDebugMode.value) return interview ? '面试训练（调试视图）' : '答辩训练（调试视图）'
  return interview ? '面试训练进行中' : '答辩训练进行中'
})

/** 正式会话 + 主流程：主流程区副标题（与「当前环节」长条、下方问答区呼应） */
const defenseStageHeadline = computed(() => {
  if (!sessionId.value) return ''
  if (sessionPhase.value === 'lecture') {
    return '讲解中：先完成陈述，再进入老师提问'
  }
  if (qaRoundSource.value === 'followup_generated') {
    return '老师追问中：在上一轮主问题与评估之后，继续补充说明'
  }
  return '主问题答辩中：请回答老师当前提问'
})

/** 主流程下是否展示完整追问列表（否则仅保留已自动选中的当前追问题干） */
const showQaFollowupPickerList = computed(
  () =>
    trainingFlowDebugMode.value ||
    qaRoundSource.value !== 'followup_generated' ||
    selectedFollowupIndex.value < 0
)

/**
 * 批量出题 / 备用题库：仅无会话准备期或调试模式展示（正式会话中由流程自动选题，避免测试台观感）。
 */
const showMockGenerateSection = computed(
  () => !sessionId.value || trainingFlowDebugMode.value
)

/** 无会话、答辩问答阶段、或调试模式：展示问答区 */
const showQaSection = computed(
  () => !sessionId.value || sessionPhase.value === 'qa' || trainingFlowDebugMode.value
)

/**
 * 「生成追问」：仅调试 / 无会话兜底；正式答辩主流程由首轮评估后自动追问，不依赖此按钮。
 */
const showGenerateFollowupButton = computed(() => {
  if (!qaEvaluationResult.value) return false
  if (!primaryTeacherQaEvalDone.value) return false
  if (!sessionId.value) return true
  return trainingFlowDebugMode.value === true
})

/** 兼容后端/历史字段：question | text | q */
const displayMockQuestionText = (item) => {
  if (!item || typeof item !== 'object') return ''
  const raw = item.question ?? item.text ?? item.q ?? ''
  return String(raw ?? '').trim()
}

/** 批量列表中第一条可展示题干的下标，用于默认老师当前问题 */
const pickFirstValidMockIndex = (list) => {
  if (!Array.isArray(list)) return -1
  for (let i = 0; i < list.length; i++) {
    if (displayMockQuestionText(list[i])) return i
  }
  return -1
}

const pickFirstValidFollowupIndex = (list) => {
  if (!Array.isArray(list)) return -1
  for (let i = 0; i < list.length; i++) {
    const q = String(list[i]?.question ?? list[i]?.text ?? list[i]?.q ?? '').trim()
    if (q) return i
  }
  return -1
}

watch(trainingFlowDebugMode, (on) => {
  if (on) mockQuestionBankExpanded.value = true
})

/** 规则追问 source → 用户可读方向（不改接口字段） */
const followupDirectionLabel = (source) => {
  const s = String(source || '').trim()
  if (s === 'qa_weak_point') return '追问方向：回答不够聚焦'
  if (s === 'content_gap') return '追问方向：内容补充'
  if (s === 'outline_gap') return '追问方向：结构延展'
  return ''
}

const pickApiDetailMessage = (e, fallback) => {
  const raw = String(e?.message ?? '')
  if (/status:\s*404/i.test(raw) || /\b404\b/.test(raw)) {
    return (
      '无法连接追问接口（404）：请确认后端已更新并重启，且地址为 /api/qa/followup。' +
      '若使用 VITE_API_BASE 直连后端，请设为 http://127.0.0.1:8000/api（末尾需含 /api）。'
    )
  }
  const i = raw.indexOf('body: ')
  if (i >= 0) {
    try {
      const j = JSON.parse(raw.slice(i + 6).trim())
      const d = j?.detail
      if (typeof d === 'string' && d.trim()) return d.trim()
    } catch (_) {}
  }
  return fallback
}

const mapFriendlyPptUploadError = (e, fallback) => {
  const detail = pickApiDetailMessage(e, fallback)
  const msg = String(detail || '').trim()
  if (!msg) return fallback
  if (msg.includes('当前仅支持上传 .pptx 文件')) {
    return '当前仅支持 .pptx 文件，请先另存为 .pptx 后上传。'
  }
  if (msg.includes('后端缺少 python-pptx 依赖')) {
    return '后端缺少 python-pptx 依赖，请在 backend 目录执行：pip install python-pptx'
  }
  if (/status:\s*500/i.test(msg) || /http error/i.test(msg) || /\btraceback\b/i.test(msg)) {
    return 'PPT 解析服务暂时不可用，请稍后重试或联系管理员检查后端依赖。'
  }
  return msg
}

/** 供 /qa/followup：手动匹配优先，否则用讲解阶段已转换的正式 plain ppt_match */
const buildPptMatchForApi = () => {
  if (lastPptMatchResult.value) {
    try {
      return JSON.parse(JSON.stringify(lastPptMatchResult.value))
    } catch (_) {
      return { ...lastPptMatchResult.value }
    }
  }
  const p =
    lectureAutoGuessFinalMatch.value ||
    bestLectureAutoPptMatchPlain.value ||
    lectureLatestAutoPptMatchPlain.value
  if (p) {
    try {
      return JSON.parse(JSON.stringify(p))
    } catch (_) {
      return { ...p }
    }
  }
  const ag = resolveLectureAutoGuessRawForStop()
  return convertAutoGuessToPlainPptMatch(ag, pptInfo.value?.pages || [])
}

const fetchPptStatus = async (pptId) => {
  const id = String(pptId ?? '').trim()
  if (!id) return null
  return await getJson(`/ppt/status/${encodeURIComponent(id)}`)
}

const buildInvalidAudioAnalysis = (message = '未检测到有效语音，请靠近麦克风后重试') => ({
  transcript: '',
  speech_rate: 0,
  pause_count: 0,
  avg_pause_sec: 0,
  filler_count: 0,
  audio_valid: false,
  audio_message: message,
})

const normalizeAudioAnalysis = (response) => {
  const invalidByFlag = response?.audio_valid === false
  const transcript = typeof response?.transcript === 'string' ? response.transcript : ''
  const invalidByEmptyTranscript = transcript.trim() === ''
  const invalid = invalidByFlag || invalidByEmptyTranscript
  if (invalid) {
    return buildInvalidAudioAnalysis(
      response?.audio_message || '未检测到有效语音，请靠近麦克风后重试'
    )
  }
  return {
    transcript,
    speech_rate: response?.speech_rate ?? 0,
    pause_count: response?.pause_count ?? 0,
    avg_pause_sec: response?.avg_pause_sec ?? 0,
    filler_count: response?.filler_count ?? 0,
    audio_valid: true,
    audio_message: response?.audio_message || '',
  }
}

const autoGuessTopCandidates = computed(() => {
  const raw = autoGuessResult.value?.top_candidates
  return Array.isArray(raw) ? raw : []
})

const autoGuessBestPageDisplay = computed(() => {
  const r = autoGuessResult.value
  if (!r) return '—'
  const v = r.best_page_index
  if (v === null || v === undefined || v === '') return '—'
  return v
})

const autoGuessShowLowMatchTip = computed(() => {
  const r = autoGuessResult.value
  if (!r) return false
  const msg = (r.message || '').trim()
  const noPage =
    r.best_page_index === null || r.best_page_index === undefined || r.best_page_index === ''
  if (msg && (noPage || Number(r.confidence) === 0)) return true
  return false
})

const autoGuessBestTitleDisplay = computed(() => {
  const r = autoGuessResult.value
  if (!r) return '—'
  const v = r.best_page_index
  if (v === null || v === undefined || v === '') return '—'
  return r.best_title || '—'
})

const startDisabledReason = computed(() => {
  if (sessionId.value) {
    return '训练进行中：请完成本轮讲解与答辩，或点击「停止训练」提交结果后再开新轮次。'
  }
  if (unfinishedResumePrompt.value) {
    return '检测到未完成的会话：请先「继续」或「放弃并重新开始」，再使用「开始训练」。'
  }
  if (isStopping.value || isSubmittingSession.value || isAnalyzingAudio.value || isAnalyzingVision.value) {
    return '上一轮训练结果仍在处理中，请稍候'
  }
  if (loading.value) {
    return '正在连接服务器并开始录音，请稍候'
  }
  if (!sessionId.value && preflightHasBlockers.value) {
    const first = preflightRows.value.find((r) => r.status === 'block')
    return first ? `暂不能开始：${first.message}` : '准备检查未通过，请点击「重新检查」。'
  }
  return ''
})

const sessionCompleting = computed(
  () =>
    isStopping.value ||
    isSubmittingSession.value ||
    isAnalyzingAudio.value ||
    isAnalyzingVision.value
)

const uiSessionState = computed(() => {
  if (stopSuccess.value) return UI_SESSION_STATE.SESSION_COMPLETED
  if (!sessionId.value && sessionDiscardedBanner.value) return UI_SESSION_STATE.SESSION_DISCARDED
  if (unfinishedResumePrompt.value && !sessionId.value) {
    return UI_SESSION_STATE.SESSION_PAUSED_RECOVERABLE
  }
  if (sessionId.value) {
    if (sessionCompleting.value) return UI_SESSION_STATE.SESSION_COMPLETING
    if (sessionPhase.value === 'qa') return UI_SESSION_STATE.SESSION_RUNNING_QA
    return UI_SESSION_STATE.SESSION_RUNNING_LECTURE
  }
  if (!preflightHasBlockers.value) return UI_SESSION_STATE.PREFLIGHT_READY
  return UI_SESSION_STATE.IDLE
})

const trainingAllowedActions = computed(() => {
  const completing = sessionCompleting.value
  const none = {
    start: false,
    stop: false,
    continueResume: false,
    abandonResume: false,
  }
  const st = uiSessionState.value
  if (st === UI_SESSION_STATE.SESSION_COMPLETED) {
    return { ...none }
  }
  if (st === UI_SESSION_STATE.SESSION_DISCARDED) {
    const canStartAfterDiscard =
      !completing &&
      !loading.value &&
      !unfinishedResumePrompt.value &&
      !sessionId.value &&
      !preflightHasBlockers.value
    return { ...none, start: canStartAfterDiscard }
  }
  if (st === UI_SESSION_STATE.SESSION_PAUSED_RECOVERABLE) {
    return {
      ...none,
      continueResume: !completing && !loading.value,
      abandonResume: !completing && !loading.value,
    }
  }
  if (
    st === UI_SESSION_STATE.SESSION_RUNNING_LECTURE ||
    st === UI_SESSION_STATE.SESSION_RUNNING_QA ||
    st === UI_SESSION_STATE.SESSION_COMPLETING
  ) {
    return {
      ...none,
      stop: sessionId.value && !completing && !stopSuccess.value,
    }
  }
  const canStart =
    !completing &&
    !loading.value &&
    !unfinishedResumePrompt.value &&
    !sessionId.value &&
    !preflightHasBlockers.value
  return { ...none, start: canStart }
})

const startButtonDisabled = computed(() => !trainingAllowedActions.value.start)

const trainingStateTitle = computed(() => {
  const m = {
    [UI_SESSION_STATE.IDLE]: '先完成环境检查',
    [UI_SESSION_STATE.PREFLIGHT_READY]: '可以开始训练',
    [UI_SESSION_STATE.SESSION_RUNNING_LECTURE]: '进行中 · 讲解',
    [UI_SESSION_STATE.SESSION_RUNNING_QA]: '进行中 · 问答',
    [UI_SESSION_STATE.SESSION_PAUSED_RECOVERABLE]: '上次练到一半，可继续',
    [UI_SESSION_STATE.SESSION_COMPLETING]: '正在收卷与提交',
    [UI_SESSION_STATE.SESSION_COMPLETED]: '本轮已提交',
    [UI_SESSION_STATE.SESSION_DISCARDED]: '已结束上次草稿',
  }
  return m[uiSessionState.value] || uiSessionState.value
})

const trainingStatePhaseLine = computed(() => {
  const st = uiSessionState.value
  if (st === UI_SESSION_STATE.SESSION_PAUSED_RECOVERABLE) {
    return unfinishedResumePhaseDisplay.value || '—'
  }
  if (st === UI_SESSION_STATE.SESSION_RUNNING_LECTURE) return '讲解与陈述'
  if (st === UI_SESSION_STATE.SESSION_RUNNING_QA) {
    return qaRoundSource.value === 'followup_generated' ? '老师追问' : '主问题答辩'
  }
  if (st === UI_SESSION_STATE.SESSION_COMPLETING) {
    if (sessionPhase.value === 'qa') return '答辩与问答（正在汇总并提交）'
    return '讲解（正在汇总并提交）'
  }
  if (st === UI_SESSION_STATE.SESSION_COMPLETED) return '已结束（即将/已前往结果）'
  if (st === UI_SESSION_STATE.SESSION_DISCARDED) return '—'
  if (st === UI_SESSION_STATE.PREFLIGHT_READY) return '尚未开始训练（检查已通过）'
  return '尚未开始训练（需先处理下方检查项）'
})

const trainingStateSidLine = computed(() => {
  if (sessionId.value) return trainingSessionShortId(sessionId.value)
  if (unfinishedResumePrompt.value?.sessionId) {
    return trainingSessionShortId(unfinishedResumePrompt.value.sessionId)
  }
  return ''
})

const trainingStateNextStepLine = computed(() => {
  const st = uiSessionState.value
  if (st === UI_SESSION_STATE.SESSION_COMPLETED) {
    return '等待跳转到结果页；若未自动跳转，请从菜单进入「结果」。'
  }
  if (st === UI_SESSION_STATE.SESSION_DISCARDED) {
    return '检查训练前准备项，确认无误后点击「开始训练」。'
  }
  if (st === UI_SESSION_STATE.SESSION_PAUSED_RECOVERABLE) {
    return unfinishedResumePrompt.value?.hasSnapshot
      ? `点击「${continueResumeButtonLabel.value}」恢复上下文；若不需继续，请点击「放弃并重新开始」。`
      : '建议先尝试「继续」以恢复服务器会话；若无本地缓存，可能需重新进入问答流程。也可「放弃并重新开始」。'
  }
  if (st === UI_SESSION_STATE.SESSION_COMPLETING) {
    return '请稍候，正在上传录音/录像并提交训练结果，勿关闭页面。'
  }
  if (st === UI_SESSION_STATE.SESSION_RUNNING_LECTURE) {
    return '先完成本环节讲解与录像；再点「结束讲解，进入答辩问答」进入主问题。若需提前交卷，可点「停止训练」。'
  }
  if (st === UI_SESSION_STATE.SESSION_RUNNING_QA) {
    return '按主流程答完主问题/追问，并在每问后完成评估；全部结束后可点「停止训练」生成本轮结果。'
  }
  if (st === UI_SESSION_STATE.PREFLIGHT_READY) {
    return '点击「开始训练」；若需调整模式或课件，请在开始训练前修改。'
  }
  return '请根据下方「训练前准备检查」逐项处理阻塞项，或点击「重新检查」。'
})

function buildStageStepList(activeIdx) {
  return TRAINING_STAGE_TRACK.map((s, i) => {
    let statusClass = 'tsg-track-item--upcoming'
    if (activeIdx >= 0) {
      if (i < activeIdx) statusClass = 'tsg-track-item--done'
      else if (i === activeIdx) statusClass = 'tsg-track-item--active'
    }
    return {
      ...s,
      index: i + 1,
      statusClass,
    }
  })
}

const trainingStageGuide = computed(() => {
  const empty = {
    visible: false,
    logKey: 'hidden',
    stageTitle: '',
    goal: '',
    nextAction: '',
    doneSummary: '',
    steps: [],
  }
  const st = uiSessionState.value

  if (unfinishedResumePrompt.value && !sessionId.value) {
    const snap = unfinishedResumePrompt.value.snapshot
    const ph = snap?.session_phase
    const qrs = snap?.qa_round_source
    let activeIdx = 0
    let logKey = 'recover_pending'
    if (ph === 'qa') {
      activeIdx = qrs === 'followup_generated' ? 3 : 1
    }
    return {
      visible: true,
      logKey,
      stageTitle: '未完成会话 · 待恢复',
      goal: '在不影响服务器会话的前提下，选择继续上次进度或放弃后重新开始。',
      nextAction: '请先点击「继续…」恢复上下文，或「放弃并重新开始」；继续后请按提示重新授权麦克风/摄像头。',
      doneSummary: snap
        ? ph === 'qa'
          ? qrs === 'followup_generated'
            ? '上次进度：已进入老师追问环节。'
            : '上次进度：曾在答辩问答环节。'
          : '上次进度：曾在讲解阶段。'
        : '本地未缓存完整页面状态时，恢复后可能需重新生成或选题。',
      steps: buildStageStepList(activeIdx),
    }
  }

  if (stopSuccess.value || st === UI_SESSION_STATE.SESSION_COMPLETED) {
    return {
      visible: true,
      logKey: 'completed',
      stageTitle: '训练完成',
      goal: '本轮训练已提交，正在进入结果总结。',
      nextAction: '等待自动跳转结果页；也可从菜单进入「结果」查看本轮得分与建议。',
      doneSummary: '讲解与答辩相关操作已随本次会话提交（具体以结果页展示为准）。',
      steps: buildStageStepList(4),
    }
  }

  if (st === UI_SESSION_STATE.SESSION_COMPLETING && sessionId.value) {
    return {
      visible: true,
      logKey: 'wrapping_up',
      stageTitle: '正在汇总提交',
      goal: '系统正在整理本轮录音、录像与答辩数据并生成结果。',
      nextAction: '请保持本页开启并稍候，勿关闭浏览器或刷新页面。',
      doneSummary:
        sessionPhase.value === 'qa'
          ? '现场答辩问答与评估相关步骤已执行完毕，正在写入结果。'
          : '本轮在讲解阶段结束训练，结果将按当前进度生成。',
      steps: buildStageStepList(4),
    }
  }

  if (!sessionId.value) {
    return empty
  }

  if (sessionPhase.value === 'lecture') {
    return {
      visible: true,
      logKey: 'lecture',
      stageTitle: '讲解阶段',
      goal: '完整陈述本轮内容：配合课件（如有）完成讲解，并完成本阶段录音与录像采集。',
      nextAction:
        '当前正在进行讲解，请先按自己的节奏完成陈述；准备好后点击「结束讲解，进入答辩问答」。',
      doneSummary: '尚未进入答辩问答；无需抢时间，讲清楚比赶进度更重要。',
      steps: buildStageStepList(0),
    }
  }

  if (sessionPhase.value === 'qa') {
    if (qaRoundSource.value === 'followup_generated') {
      return {
        visible: true,
        logKey: 'followup',
        stageTitle: '老师追问阶段',
        goal: '围绕上一轮回答中的薄弱点，做更有针对性的补充说明。',
        nextAction: '当前为老师追问阶段，请围绕刚才的薄弱点继续补充；完成语音或文本作答后提交评估。',
        doneSummary: '已完成首轮问答及评估；当前处于老师追问轮次。',
        steps: buildStageStepList(3),
      }
    }
    if (isAnalyzingQaAudio.value || qaAnswerEvaluatePending.value) {
      return {
        visible: true,
        logKey: 'answer_eval',
        stageTitle: '回答评估',
        goal: '系统正在基于你的作答生成评估与反馈。',
        nextAction: '请稍候；评估完成后可按提示继续后续问答或结束训练。',
        doneSummary: '本题作答已提交，正在等待评估结果。',
        steps: buildStageStepList(2),
      }
    }
    return {
      visible: true,
      logKey: 'teacher_qa',
      stageTitle: '答辩问答阶段',
      goal: '听清题干后，用语音（或文本兜底）完整、清晰地回答老师当前问题。',
      nextAction: '已进入答辩问答，请优先回答屏幕上方的「老师提问」，再提交评估。',
      doneSummary: primaryTeacherQaEvalDone.value
        ? '已完成至少一次主问题评估，可按流程继续后续问答，或点击「停止训练」生成结果。'
        : '尚未完成本题评估；请先作答再提交。',
      steps: buildStageStepList(1),
    }
  }

  return {
    visible: true,
    logKey: 'in_session',
    stageTitle: '训练进行中',
    goal: '请按页面主流程与提示完成本轮训练。',
    nextAction: trainingStateNextStepLine.value,
    doneSummary: '',
    steps: buildStageStepList(0),
  }
})

/** 会话开始后页面中上部的「当前环节」长条：与 trainingStageGuide 同源描述，不新增业务状态 */
const defenseFlowRibbonVisible = computed(() => sessionId.value && !stopSuccess.value)

const defenseFlowRibbonEyebrow = computed(() => {
  const isInterview = trainingScoringProfile.value === 'interview'
  const base = isInterview ? '面试训练' : '答辩训练'
  if (trainingFlowDebugMode.value) {
    return `${base} · 当前环节（额外调试辅助已开，不改动当前会话已记录的内容）`
  }
  return `${base} · 当前环节`
})

const defenseFlowRibbonTitle = computed(() => {
  if (!sessionId.value || stopSuccess.value) return ''
  const g = trainingStageGuide.value
  if (g.visible && g.stageTitle) return g.stageTitle
  return trainingStateTitle.value
})

const defenseFlowNowText = computed(() => {
  if (!sessionId.value || stopSuccess.value) return ''
  const g = trainingStageGuide.value
  if (g.visible && g.nextAction) return g.nextAction
  return trainingStateNextStepLine.value
})

const defenseFlowAfterText = computed(() => {
  if (!sessionId.value || stopSuccess.value) return ''
  const g = trainingStageGuide.value
  if (!g.visible) return trainingStateNextStepLine.value
  const k = g.logKey
  if (k === 'wrapping_up' || k === 'completed') {
    return g.nextAction || '请稍候，正在收尾并进入结果说明。'
  }
  if (k === 'recover_pending') {
    return '继续后将回到上次的讲解或问答进度；必要时请重新允许麦克风与摄像头。'
  }
  if (k === 'lecture') {
    return '进入答辩后，你会先看到老师「主问题」；主问题答评之后，视情况可能进入「追问」环节。'
  }
  if (k === 'teacher_qa') {
    return '每题在评估后，系统可能依表现生成下一问（追问），也可在答完主问题后结束本轮并查看报告。'
  }
  if (k === 'followup') {
    return '追问评估结束后，可继续其它问答，或在适当时点结束训练、查看总评。'
  }
  if (k === 'answer_eval') {
    return '评估结果返回后，可继续答下一问，或结束训练生成本轮成绩与建议。'
  }
  if (k === 'in_session' || k === 'hidden') {
    return trainingStateNextStepLine.value
  }
  return g.nextAction || trainingStateNextStepLine.value
})

/** 主卡片「现在 / 接下来」：合并原会话条 + 答辩带，避免顶栏重复 */
const primaryStatusNowLine = computed(() => {
  if (stopSuccess.value) return ''
  if (defenseFlowRibbonVisible.value) return defenseFlowNowText.value
  if (unfinishedResumePrompt.value && !sessionId.value) {
    return '先决定是接着上次的进度继续，还是放弃后重新开一轮。'
  }
  return ''
})
const primaryStatusAfterLine = computed(() => {
  if (stopSuccess.value) return ''
  if (defenseFlowRibbonVisible.value) return defenseFlowAfterText.value
  return trainingStateNextStepLine.value
})

const missionPrimaryActionHint = computed(() => {
  if (stopSuccess.value) return ''
  if (unfinishedResumePrompt.value && !sessionId.value) return ''
  if (sessionId.value) {
    return '在下方「训练控制」中继续或结束本轮。讲解、答辩、课件等操作在页面中下部完成。'
  }
  return '在下方先选择「训练模式」、完成环境检查与课件（若有），然后在「开始训练」中启动本轮。'
})

const supplementalPanelVisible = computed(() => {
  if (demoModeUi.value?.active) return true
  if (resumeSessionCheckFailed.value && !sessionId.value) return true
  if (!sessionId.value && !unfinishedResumePrompt.value && showRecentValidTrainingReminder.value) {
    return true
  }
  if (sessionId.value && resumeMediaHintVisible.value) return true
  return false
})

const lastTrainingStageLogSig = ref('')
watch(
  () => trainingStageGuide.value,
  (g) => {
    if (!g.visible) return
    const sig = `${g.logKey}|${g.goal}|${g.nextAction}`
    if (sig === lastTrainingStageLogSig.value) return
    lastTrainingStageLogSig.value = sig
    console.log('[Training.stage] current_stage=', g.logKey)
    console.log('[Training.stage] current_goal=', g.goal)
    console.log('[Training.stage] next_action=', g.nextAction)
  },
  { flush: 'post' }
)

watch(
  () => ({
    state: uiSessionState.value,
    phase: sessionPhase.value,
    actions: { ...trainingAllowedActions.value },
  }),
  (cur, prev) => {
    console.log('[Training.state] ui_session_state=', cur.state)
    console.log('[Training.state] phase=', cur.phase)
    console.log('[Training.state] allowed_actions=', cur.actions)
    const pk = `${cur.state}|${cur.phase}|${JSON.stringify(cur.actions)}`
    if (pk !== lastLoggedUiStateKey.value) {
      if (prev && prev.state !== cur.state) {
        console.log('[Training.state] state_transition=', prev.state, '->', cur.state)
      }
      lastLoggedUiStateKey.value = pk
    }
  },
  { flush: 'post' }
)

function cloneJsonSafe(v) {
  if (v == null) return null
  try {
    return JSON.parse(JSON.stringify(v))
  } catch (_) {
    return null
  }
}

function readTrainingRuntimeSnapshot() {
  try {
    const raw = readUserScopedItem(localStorage, TRAINING_RUNTIME_SNAPSHOT_KEY)
    if (!raw) return null
    const o = JSON.parse(raw)
    return o && typeof o === 'object' ? o : null
  } catch (_) {
    return null
  }
}

function clearTrainingRuntimeSnapshot() {
  try {
    removeUserScopedItem(localStorage, TRAINING_RUNTIME_SNAPSHOT_KEY, undefined, true)
  } catch (_) {}
}

function scheduleTrainingRuntimeSnapshot() {
  if (!sessionId.value) return
  clearTimeout(runtimeSnapshotTimer)
  runtimeSnapshotTimer = setTimeout(() => saveTrainingRuntimeSnapshotNow(), 450)
}

function saveTrainingRuntimeSnapshotNow() {
  if (!sessionId.value) return
  try {
    const payload = {
      v: 1,
      ts: Date.now(),
      session_id: sessionId.value,
      session_phase: sessionPhase.value,
      scoring_profile: trainingScoringProfile.value,
      defense_material_mode: defenseMaterialModeFromDeck(),
      training_deck_mode: trainingDeckMode.value,
      recommended_training_focus: recommendedTrainingFocus.value,
      training_focus_source: trainingFocusSource.value,
      content_focus_downgraded: contentFocusDowngraded.value,
      qa_round_source: qaRoundSource.value,
      current_qa_question: currentQaQuestion.value,
      current_qa_expected_keywords: cloneJsonSafe(currentQaExpectedKeywords.value),
      primary_teacher_qa_eval_done: primaryTeacherQaEvalDone.value,
      selected_mock_question_index: selectedMockQuestionIndex.value,
      selected_mock_question: cloneJsonSafe(selectedMockQuestion.value),
      last_manual_qa_result: cloneJsonSafe(lastManualQaResult.value),
      last_auto_qa_result: cloneJsonSafe(lastAutoQaResult.value),
      last_followup_qa_result: cloneJsonSafe(lastFollowupQaResult.value),
      last_qa_result: cloneJsonSafe(lastQaResult.value),
      qa_evaluation_result: cloneJsonSafe(qaEvaluationResult.value),
      followup_questions: cloneJsonSafe(followupQuestions.value),
      selected_followup_index: selectedFollowupIndex.value,
      followup_section_visible: followupSectionVisible.value,
      last_followup_questions_snapshot: cloneJsonSafe(lastFollowupQuestionsSnapshot.value),
      selected_followup_question: cloneJsonSafe(selectedFollowupQuestion.value),
      mock_questions_list: cloneJsonSafe(mockQuestionsList.value),
      spoken_text: spokenText.value,
      selected_page_index: selectedPageIndex.value,
      ppt_match_mode: pptMatchMode.value,
      ppt_info: cloneJsonSafe(pptInfo.value),
      last_question_generation_context: cloneJsonSafe(lastQuestionGenerationContext.value),
      last_followup_generation_context: cloneJsonSafe(lastFollowupGenerationContext.value),
    }
    writeUserScopedItem(localStorage, TRAINING_RUNTIME_SNAPSHOT_KEY, JSON.stringify(payload))
  } catch (e) {
    console.warn('[Training] runtime snapshot save failed', e)
  }
}

function applyTrainingResumeFromServer(server) {
  if (!server) return
  const sp = String(server.scoring_profile || '').trim().toLowerCase()
  if (sp === 'interview' || sp === 'defense') {
    trainingScoringProfile.value = sp
  }
  const dm = String(server.defense_material_mode || '').trim().toLowerCase()
  if (dm === 'without_ppt') {
    trainingDeckMode.value = 'none'
  } else if (dm === 'with_ppt') {
    trainingDeckMode.value = 'with_deck'
  }
  const tf = String(server.training_focus ?? 'none').trim().toLowerCase()
  if (!tf || tf === 'none') {
    recommendedTrainingFocus.value = null
    trainingFocusSource.value = 'none'
  } else {
    const k = normalizeIncomingFocusKey(tf)
    recommendedTrainingFocus.value = k
    trainingFocusSource.value = k ? 'manual' : 'none'
  }
}

function resetQaStateForPartialResume() {
  contentFocusDowngraded.value = false
  sessionPhase.value = 'lecture'
  primaryTeacherQaEvalDone.value = false
  currentQaQuestion.value = ''
  currentQaExpectedKeywords.value = []
  qaRoundSource.value = 'manual'
  selectedMockQuestionIndex.value = -1
  selectedMockQuestion.value = null
  lastManualQaResult.value = null
  lastAutoQaResult.value = null
  lastFollowupQaResult.value = null
  lastQaResult.value = null
  qaEvaluationResult.value = null
  followupQuestions.value = []
  selectedFollowupIndex.value = -1
  followupSectionVisible.value = false
  lastFollowupQuestionsSnapshot.value = null
  selectedFollowupQuestion.value = null
  mockQuestionsList.value = []
}

function applyTrainingRuntimeSnapshotPayload(snap) {
  if (!snap || snap.v !== 1) return
  sessionPhase.value = snap.session_phase === 'qa' ? 'qa' : 'lecture'
  trainingScoringProfile.value =
    snap.scoring_profile === 'interview' ? 'interview' : 'defense'
  const deck = String(snap.training_deck_mode || 'with_deck')
  trainingDeckMode.value = deck === 'none' ? 'none' : 'with_deck'
  recommendedTrainingFocus.value = normalizeIncomingFocusKey(snap.recommended_training_focus)
  const srcRaw = String(snap.training_focus_source || 'manual').trim().toLowerCase()
  const allowed = new Set([
    'result_page',
    'overview_hint',
    'resume_last_config',
    'apply_recommended_focus',
    'manual',
    'none',
  ])
  trainingFocusSource.value = allowed.has(srcRaw)
    ? srcRaw
    : recommendedTrainingFocus.value
      ? 'manual'
      : 'none'
  contentFocusDowngraded.value = !!snap.content_focus_downgraded
  qaRoundSource.value = ['manual', 'auto_generated', 'followup_generated'].includes(snap.qa_round_source)
    ? snap.qa_round_source
    : 'manual'
  currentQaQuestion.value = String(snap.current_qa_question || '')
  currentQaExpectedKeywords.value = Array.isArray(snap.current_qa_expected_keywords)
    ? [...snap.current_qa_expected_keywords]
    : []
  primaryTeacherQaEvalDone.value = !!snap.primary_teacher_qa_eval_done
  selectedMockQuestionIndex.value =
    typeof snap.selected_mock_question_index === 'number' ? snap.selected_mock_question_index : -1
  selectedMockQuestion.value = cloneJsonSafe(snap.selected_mock_question)
  lastManualQaResult.value = cloneJsonSafe(snap.last_manual_qa_result)
  lastAutoQaResult.value = cloneJsonSafe(snap.last_auto_qa_result)
  lastFollowupQaResult.value = cloneJsonSafe(snap.last_followup_qa_result)
  lastQaResult.value = cloneJsonSafe(snap.last_qa_result)
  qaEvaluationResult.value = cloneJsonSafe(snap.qa_evaluation_result)
  followupQuestions.value = Array.isArray(snap.followup_questions)
    ? cloneJsonSafe(snap.followup_questions) || []
    : []
  selectedFollowupIndex.value =
    typeof snap.selected_followup_index === 'number' ? snap.selected_followup_index : -1
  followupSectionVisible.value = !!snap.followup_section_visible
  lastFollowupQuestionsSnapshot.value = cloneJsonSafe(snap.last_followup_questions_snapshot)
  selectedFollowupQuestion.value = cloneJsonSafe(snap.selected_followup_question)
  mockQuestionsList.value = Array.isArray(snap.mock_questions_list)
    ? cloneJsonSafe(snap.mock_questions_list) || []
    : []
  spokenText.value = String(snap.spoken_text || '')
  selectedPageIndex.value =
    snap.selected_page_index != null && snap.selected_page_index !== '' ? snap.selected_page_index : null
  pptMatchMode.value = snap.ppt_match_mode === 'auto' ? 'auto' : 'manual'
  pptInfo.value = cloneJsonSafe(snap.ppt_info)
  lastQuestionGenerationContext.value = cloneJsonSafe(snap.last_question_generation_context)
  lastFollowupGenerationContext.value = cloneJsonSafe(snap.last_followup_generation_context)
  const pid = String(snap.ppt_info?.ppt_id || '').trim()
  if (pid) {
    cachedPptIdFallback.value = pid
    try {
      writeUserScopedItem(localStorage, LAST_PPT_ID_STORAGE_KEY, pid)
    } catch (_) {}
  }
  if (recommendedTrainingFocus.value === 'content' && trainingDeckMode.value === 'none') {
    recommendedTrainingFocus.value = null
    trainingFocusSource.value = 'none'
    contentFocusDowngraded.value = true
  }
}

function continueUnfinishedTraining() {
  const ctx = unfinishedResumePrompt.value
  if (!ctx) return
  const sid = String(ctx.sessionId || '').trim()
  if (!sid) return
  console.log('[Training.cleanup] scenario=', 'resume')
  cleanupMediaResources('resume')
  resetTrainingRuntimeState('resume')
  let snap = ctx.hasSnapshot && ctx.snapshot ? ctx.snapshot : readTrainingRuntimeSnapshot()
  if (!snap || snap.session_id !== sid || snap.v !== 1) {
    snap = null
  }
  applyTrainingResumeFromServer(ctx.server)
  if (snap) {
    applyTrainingRuntimeSnapshotPayload(snap)
  } else {
    resetQaStateForPartialResume()
  }
  sessionId.value = sid
  try {
    persistCurrentSessionId(sid)
  } catch (_) {}
  unfinishedResumePrompt.value = null
  resumeMediaHintVisible.value = true
  saveTrainingRuntimeSnapshotNow()
  console.log('[Training.resume_session] restored_phase=', sessionPhase.value)
  trainingFeedback(
    'resume_unfinished',
    'success',
    '已恢复本轮训练进度，请按页面提示继续；若浏览器请求麦克风或摄像头，请点击「允许」。'
  )
}

async function abandonUnfinishedTraining() {
  const ok = await trainingConfirmDanger({
    title: '放弃本轮未完成的训练？',
    message:
      '未提交的进度将作废，服务器上的该会话也会被放弃；确认后将回到准备页，需要重新通过自检才能再开始训练。若想继续，请先点「取消」并选择「继续本轮训练」。',
    confirmButtonText: '确认放弃',
    cancelButtonText: '取消',
  })
  if (!ok) return

  const ctx = unfinishedResumePrompt.value
  const sid =
    String(ctx?.sessionId || '').trim() ||
    String(readUserScopedItem(localStorage, CURRENT_SESSION_ID_KEY) || '').trim()
  if (sid) {
    try {
      await postJson('/session/abandon', { session_id: sid })
    } catch (e) {
      console.warn('[Training.resume_session] abandon request failed', e)
    }
  }
  console.log('[Training.cleanup] scenario=', 'discard')
  cleanupMediaResources('discard')
  clearRecoverableSessionState('discard')
  resetTrainingRuntimeState('discard')
  sessionDiscardedBanner.value = '已放弃未完成的会话，准备检查通过后可重新「开始训练」。'
  setTimeout(() => {
    sessionDiscardedBanner.value = ''
  }, 12000)
  console.log('[Training.resume_session] discarded_session=', true, sid || null)
  const incomingRes = applyIncomingTrainingFocus()
  const usedSessionStorage = incomingRes?.usedSessionStorage === true
  if (hasExplicitTrainingRouteQuery()) {
    /* URL 显式参数已生效 */
  } else if (!usedSessionStorage) {
    restoreTrainingPageDraftFromLocal()
  }
  saveTrainingPageDraft()
  trainingFeedback(
    'abandon_unfinished',
    'success',
    '已放弃本轮训练，当前可以重新开始；请先看清上方准备检查，再点击「开始训练」。'
  )
}

// 开始训练
const startTraining = async () => {
  console.log('startTraining clicked')
  if (sessionId.value) {
    errorMessage.value = '当前已有进行中的训练会话，请先完成本轮或点击「停止训练」提交结果。'
    return
  }
  if (unfinishedResumePrompt.value) {
    trainingFeedback(
      'session_start',
      'warning',
      '检测到未完成的训练：请先点「继续本轮训练」恢复进度，或「放弃并重新开始」后再开新轮次。'
    )
    return
  }
  console.log('[Training.cleanup] scenario=', 'restart')
  cleanupMediaResources('restart')
  resetTrainingRuntimeState('restart')
  if (isStopping.value || isSubmittingSession.value || isAnalyzingAudio.value || isAnalyzingVision.value) {
    errorMessage.value = '上一轮训练结果仍在处理中，请稍候'
    return
  }
  if (loading.value) {
    return
  }
  if (!sessionId.value && preflightHasBlockers.value) {
    const first = preflightRows.value.find((r) => r.status === 'block')
    errorMessage.value = first ? `暂不能开始：${first.message}` : '准备检查未通过，请先完成课件与设备准备。'
    return
  }
  errorMessage.value = ''
  audioAnalysis.value = null
  visionAnalysis.value = null
  loading.value = true
  try {
    const startPayload = {
      scoring_profile: trainingScoringProfile.value,
      training_focus: finalTrainingFocus.value,
      defense_material_mode: defenseMaterialMode.value,
    }
    console.log(
      '[Training.focus] recommended_training_focus=',
      recommendedTrainingFocus.value ?? '(none)'
    )
    console.log('[Training.focus] final training_focus=', finalTrainingFocus.value)
    console.log('[Training.start] training_focus=', finalTrainingFocus.value)
    console.log(
      '[Training] start: selected scoring_profile =',
      trainingScoringProfile.value,
      'start payload =',
      startPayload
    )
    const response = await postJson('/session/start', startPayload)
    console.log('session start success', response)
    console.log('[Training.mode] defenseMaterialMode=', defenseMaterialMode.value)
    sessionId.value = response.session_id
    clearTrainingPageDraftStorage()
    try {
      removeUserScopedItem(sessionStorage, RECOMMENDED_FOCUS_STORAGE_KEY, undefined, true)
    } catch (_) {}
    sessionPhase.value = 'lecture'
    primaryTeacherQaEvalDone.value = false
    clearLectureAutoGuessPersistence()
    console.log('[Training] session phase reset -> lecture (defense flow), lecture auto-guess snapshots cleared')
    apiResult.value = JSON.stringify(response, null, 2)
    persistCurrentSessionId(response.session_id)
    if (lastPreflightNoBlockers.value) {
      try {
        writeUserScopedItem(localStorage, preflightOkBaseKey(response.session_id), '1')
      } catch (_) {}
    }
    await startRecording()
    await startVideoRecording()
    saveTrainingRuntimeSnapshotNow()
    trainingFeedback(
      'session_start',
      'success',
      '训练已开始并进入讲解阶段，请按引导完成讲解与后续问答；结束后记得提交结果。'
    )
  } catch (e) {
    console.error('开始训练失败:', e)
    apiResult.value = `错误: ${e.message}`
    errorMessage.value = `开始训练失败：${e.message || '请检查网络或稍后重试'}`
  } finally {
    loading.value = false
  }
}

/** 停止麦克风流上的所有轨道（释放硬件、停止「正在录音」指示灯） */
const stopAllMediaTracks = (stream) => {
  if (!stream || typeof stream.getTracks !== 'function') return
  stream.getTracks().forEach((track) => {
    try {
      console.log('[stopLocalRecording] MediaStreamTrack.stop', track.kind, track.label)
      track.stop()
    } catch (e) {
      console.error('[frontend.stop] cleanup error', e)
    }
  })
}

/** 清理定时器（当前项目未使用，预留与排查） */
const clearRecordingTimers = () => {
  recordingIntervalIds.value.forEach((id) => {
    try {
      clearInterval(id)
    } catch (_) {}
  })
  recordingIntervalIds.value = []
  recordingTimeoutIds.value.forEach((id) => {
    try {
      clearTimeout(id)
    } catch (_) {}
  })
  recordingTimeoutIds.value = []
  console.log('[stopLocalRecording] clearRecordingTimers done (intervals/timeouts cleared)')
}

/**
 * 立即停止本地录音链路：MediaRecorder.stop → MediaStream tracks stop → isRecording=false
 * 不包含上传；必须先于 /session/stop 调用，避免长时间占用麦克风。
 */
const stopLocalRecording = async () => {
  console.log('[stopLocalRecording] step 1: begin')
  console.log('[stopLocalRecording] (本页未使用 WebSocket / AudioContext，无额外关闭)')
  clearRecordingTimers()

  const rec = mediaRecorder.value
  const stream = mediaStream.value

  if (!rec || rec.state === 'inactive') {
    console.log('[stopLocalRecording] step 2: recorder missing or inactive, only cleanup stream')
    try {
      stopAllMediaTracks(stream)
    } catch (e) {
      console.error('[frontend.stop] cleanup error', e)
    }
    mediaStream.value = null
    mediaRecorder.value = null
    isRecording.value = false
    console.log('[frontend.stop] local media stopped')
    console.log('[stopLocalRecording] step 3: isRecording=false (no active recorder)')
    return { blob: null, mimeType: recordingMimeType.value || 'audio/webm' }
  }

  const mimeHint = rec.mimeType || recordingMimeType.value || 'audio/webm'

  const result = await new Promise((resolve) => {
    let settled = false
    const finish = (payload) => {
      if (settled) return
      settled = true
      resolve(payload)
    }

    const onStop = () => {
      console.log('[stopLocalRecording] step 4: MediaRecorder "stop" event fired')
      const blob = new Blob(audioChunks.value, { type: mimeHint })
      console.log('[stopLocalRecording] step 6: Blob built', { size: blob.size, type: blob.type })
      console.log('[frontend.stop] recorder blob ready', { size: blob.size, type: blob.type })

      mediaRecorder.value = null
      console.log('[stopLocalRecording] step 7: mediaRecorder ref cleared')

      finish({ blob, mimeType: mimeHint })
    }

    rec.addEventListener('stop', onStop, { once: true })

    try {
      if (rec.state === 'recording' && typeof rec.requestData === 'function') {
        rec.requestData()
        console.log('[stopLocalRecording] requestData() for flush')
      }
    } catch (e) {
      console.warn('[stopLocalRecording] requestData optional failed', e)
    }

    try {
      rec.stop()
      console.log('[stopLocalRecording] step 8: recorder.stop() called, state=', rec.state)
      try {
        stopAllMediaTracks(stream)
      } catch (e) {
        console.error('[frontend.stop] cleanup error', e)
      }
      mediaStream.value = null
      isRecording.value = false
      console.log('[frontend.stop] local media stopped')
      console.log('[stopLocalRecording] step 5: isRecording=false (UI 应不再显示「正在录音」)')
    } catch (e) {
      console.error('[stopLocalRecording] recorder.stop() threw', e)
      console.error('[frontend.stop] cleanup error', e)
      isRecording.value = false
      try {
        stopAllMediaTracks(stream)
      } catch (e2) {
        console.error('[frontend.stop] cleanup error', e2)
      }
      mediaStream.value = null
      mediaRecorder.value = null
      console.log('[frontend.stop] local media stopped')
      finish({ blob: null, mimeType: mimeHint })
    }
  })

  console.log('[stopLocalRecording] step 9: stopLocalRecording finished')
  return result
}

const startVideoRecording = async () => {
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    const msg = '当前浏览器不支持视频录制，请更换浏览器或使用最新版 Chrome / Edge'
    errorMessage.value = msg
    console.warn(msg)
    return
  }
  try {
    videoStream.value = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
    if (cameraPreviewRef.value) {
      cameraPreviewRef.value.srcObject = videoStream.value
    }
    videoChunks.value = []
    videoStopRequested.value = false
    const preferredTypes = [
      'video/webm;codecs=vp9,opus',
      'video/webm;codecs=vp8,opus',
      'video/webm'
    ]
    let selectedMimeType = ''
    if (window.MediaRecorder && typeof window.MediaRecorder.isTypeSupported === 'function') {
      selectedMimeType = preferredTypes.find((type) => window.MediaRecorder.isTypeSupported(type)) || ''
    }
    videoRecorder.value = selectedMimeType
      ? new MediaRecorder(videoStream.value, { mimeType: selectedMimeType })
      : new MediaRecorder(videoStream.value)
    videoMimeType.value = videoRecorder.value.mimeType || selectedMimeType || 'video/webm'
    videoRecorder.value.ondataavailable = (event) => {
      // 停止请求后不再持续收集 chunk，仅保留 stop 后最终 flush 的片段
      if (videoStopRequested.value && videoRecorder.value && videoRecorder.value.state !== 'inactive') {
        return
      }
      if (event.data && event.data.size > 0) {
        videoChunks.value.push(event.data)
      }
    }
    videoRecorder.value.start()
    isVideoRecording.value = true
    console.log('[startVideoRecording] MediaRecorder started, isVideoRecording=true')
  } catch (e) {
    console.error('视频录制启动失败:', e)
    const name = e && e.name
    let detail = e && e.message ? String(e.message) : '未知错误'
    if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
      detail = '摄像头权限被拒绝，请在浏览器设置中允许本站使用摄像头后重试'
    } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
      detail = '未检测到可用摄像头设备，请连接摄像头后重试'
    }
    errorMessage.value = `浏览器视频初始化失败：${detail}`
  }
}

const stopLocalVideoRecording = async () => {
  console.log('video recording stop requested')
  const rec = videoRecorder.value
  const stream = videoStream.value

  // 立即 UI 收尾：先把录像状态和预览关掉，避免用户误以为仍在录制
  isVideoRecording.value = false
  videoStopRequested.value = true
  if (cameraPreviewRef.value) {
    cameraPreviewRef.value.srcObject = null
  }
  if (stream) {
    try {
      stopAllMediaTracks(stream)
    } catch (e) {
      console.error('[frontend.stop] cleanup error', e)
    }
    console.log('video tracks stopped')
    videoStream.value = null
  }
  console.log('[frontend.stop] local media stopped')

  if (!rec || rec.state === 'inactive') {
    videoRecorder.value = null
    console.log('video recorder stopped')
    return { blob: null, mimeType: videoMimeType.value || 'video/webm' }
  }

  const mimeHint = rec.mimeType || videoMimeType.value || 'video/webm'
  const result = await new Promise((resolve) => {
    let settled = false
    let fallbackTimer = null
    const finish = (payload) => {
      if (settled) return
      settled = true
      if (fallbackTimer) {
        clearTimeout(fallbackTimer)
      }
      videoRecorder.value = null
      videoStopRequested.value = false
      resolve(payload)
    }
    const onStop = () => {
      console.log('video recorder stopped')
      const blob = new Blob(videoChunks.value, { type: mimeHint })
      console.log('[frontend.stop] recorder blob ready', { size: blob.size, type: blob.type })
      finish({ blob, mimeType: mimeHint })
    }
    rec.addEventListener('stop', onStop, { once: true })
    fallbackTimer = setTimeout(() => {
      console.warn('[stopLocalVideoRecording] stop event timeout, force cleanup')
      console.warn('video recorder stopped')
      finish({ blob: null, mimeType: mimeHint })
    }, 2000)
    try {
      if (rec.state === 'recording' && typeof rec.requestData === 'function') {
        rec.requestData()
      }
    } catch (_) {}
    try {
      rec.stop()
    } catch (e) {
      console.error('[stopLocalVideoRecording] recorder.stop error', e)
      console.error('[frontend.stop] cleanup error', e)
      console.warn('video recorder stopped')
      finish({ blob: null, mimeType: mimeHint })
    }
  })
  return result
}

/** 上传录音 blob 做转写/分析（在本地已完全停止录音之后） */
const uploadRecordedAudioForAnalysis = async (blob, mimeType) => {
  console.log('[Training] lecture audio analyze phase=lecture')
  console.log('[uploadRecordedAudioForAnalysis] begin', { size: blob?.size, mimeType })
  if (!blob || blob.size === 0) {
    console.warn('[uploadRecordedAudioForAnalysis] empty blob, skip upload')
    return null
  }
  const blobType = mimeType || 'audio/webm'
  const filename = blobType.includes('ogg') ? 'recording.ogg' : 'recording.webm'
  const formData = new FormData()
  formData.append('file', blob, filename)
  const response = await uploadFile('/audio/analyze?analysis_phase=lecture', formData)
  console.log('[audio/analyze] raw JSON response', response)
  console.log('[audio/analyze] raw transcript field', response?.transcript)
  const normalized = normalizeAudioAnalysis(response)
  audioAnalysis.value = normalized
  if (
    normalized.audio_valid === false &&
    typeof normalized.audio_message === 'string' &&
    normalized.audio_message.includes('超时')
  ) {
    errorMessage.value = '语音分析超时，本轮仅保留视觉结果；可缩短录音时长后重试'
  }
  console.log('[audio/analyze] normalized transcript written', audioAnalysis.value.transcript)
  apiResult.value = JSON.stringify(normalized, null, 2)
  console.log('[uploadRecordedAudioForAnalysis] success', normalized)
  return normalized
}

/** 问答语音：同 /audio/analyze 协议，但不写入讲解用的 audioAnalysis，避免覆盖主录音链 */
const uploadQaAudioForTranscript = async (blob, mimeType) => {
  console.log('[Training] qa voice analyze phase=qa_answer (POST /audio/analyze?analysis_phase=qa_answer)')
  console.log('[uploadQaAudioForTranscript] begin', { size: blob?.size, mimeType })
  if (!blob || blob.size === 0) {
    console.warn('[uploadQaAudioForTranscript] empty blob')
    return null
  }
  const blobType = mimeType || 'audio/webm'
  const filename = blobType.includes('ogg') ? 'qa_answer.ogg' : 'qa_answer.webm'
  const formData = new FormData()
  formData.append('file', blob, filename)
  const response = await uploadFile('/audio/analyze?analysis_phase=qa_answer', formData)
  const normalized = normalizeAudioAnalysis(response)
  console.log(
    '[uploadQaAudioForTranscript] done transcript_len=',
    (normalized?.transcript || '').length,
    'audio_valid=',
    normalized?.audio_valid
  )
  return normalized
}

const stopQaAnswerLocalRecording = async () => {
  const rec = qaAnswerMediaRecorder.value
  const stream = qaAnswerMediaStream.value
  if (!rec || rec.state === 'inactive') {
    try {
      stopAllMediaTracks(stream)
    } catch (e) {
      console.error('[stopQaAnswerLocalRecording] cleanup', e)
    }
    qaAnswerMediaStream.value = null
    qaAnswerMediaRecorder.value = null
    isQaAnswerRecording.value = false
    return { blob: null, mimeType: qaAnswerRecordingMimeType.value || 'audio/webm' }
  }
  const mimeHint = rec.mimeType || qaAnswerRecordingMimeType.value || 'audio/webm'
  const result = await new Promise((resolve) => {
    let settled = false
    const finish = (payload) => {
      if (settled) return
      settled = true
      resolve(payload)
    }
    const onStop = () => {
      const blob = new Blob(qaAnswerChunks.value, { type: mimeHint })
      qaAnswerMediaRecorder.value = null
      finish({ blob, mimeType: mimeHint })
    }
    rec.addEventListener('stop', onStop, { once: true })
    try {
      if (rec.state === 'recording' && typeof rec.requestData === 'function') {
        rec.requestData()
      }
    } catch (_) {}
    try {
      rec.stop()
      try {
        stopAllMediaTracks(stream)
      } catch (e) {
        console.error('[stopQaAnswerLocalRecording] tracks', e)
      }
      qaAnswerMediaStream.value = null
      isQaAnswerRecording.value = false
    } catch (e) {
      console.error('[stopQaAnswerLocalRecording] stop threw', e)
      isQaAnswerRecording.value = false
      try {
        stopAllMediaTracks(stream)
      } catch (_) {}
      qaAnswerMediaStream.value = null
      qaAnswerMediaRecorder.value = null
      finish({ blob: null, mimeType: mimeHint })
    }
  })
  return result
}

const startQaAnswerRecording = async () => {
  if (isLectureRecordingAudio.value) {
    errorMessage.value = '请先停止讲解录音后再进行语音作答'
    return
  }
  if (isQaAnswerRecording.value) return
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    errorMessage.value = '当前浏览器不支持录音，请使用 Chrome / Edge 或改用文本兜底'
    return
  }
  errorMessage.value = ''
  try {
    qaAnswerMediaStream.value = await navigator.mediaDevices.getUserMedia({ audio: true })
    qaAnswerChunks.value = []
    const preferredTypes = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/ogg',
    ]
    let selectedMimeType = ''
    if (window.MediaRecorder && typeof window.MediaRecorder.isTypeSupported === 'function') {
      selectedMimeType = preferredTypes.find((type) => window.MediaRecorder.isTypeSupported(type)) || ''
    }
    qaAnswerMediaRecorder.value = selectedMimeType
      ? new MediaRecorder(qaAnswerMediaStream.value, { mimeType: selectedMimeType })
      : new MediaRecorder(qaAnswerMediaStream.value)
    qaAnswerRecordingMimeType.value = qaAnswerMediaRecorder.value.mimeType || selectedMimeType || ''
    qaAnswerMediaRecorder.value.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        qaAnswerChunks.value.push(event.data)
      }
    }
    qaAnswerMediaRecorder.value.start()
    isQaAnswerRecording.value = true
    qaAnswerMode.value = 'voice'
    qaAnswerAudioBlob.value = null
    qaAnswerTranscript.value = ''
    console.log('[Training] qa voice record start')
    console.log('[Training] qa current source=' + resolveQaAnswerLogSource())
  } catch (e) {
    console.error('[startQaAnswerRecording]', e)
    errorMessage.value = `问答录音启动失败：${e?.message || e}`
    try {
      stopAllMediaTracks(qaAnswerMediaStream.value)
    } catch (_) {}
    qaAnswerMediaStream.value = null
    qaAnswerMediaRecorder.value = null
    isQaAnswerRecording.value = false
  }
}

const cleanupQaAnswerRecordingHard = () => {
  try {
    const rec = qaAnswerMediaRecorder.value
    if (rec && rec.state === 'recording') {
      try {
        rec.stop()
      } catch (_) {}
    }
  } catch (_) {}
  qaAnswerMediaRecorder.value = null
  try {
    stopAllMediaTracks(qaAnswerMediaStream.value)
  } catch (_) {}
  qaAnswerMediaStream.value = null
  isQaAnswerRecording.value = false
  qaAnswerChunks.value = []
}

function readCurrentSessionIdFromLs() {
  try {
    return String(readUserScopedItem(localStorage, CURRENT_SESSION_ID_KEY) || '').trim()
  } catch (_) {
    return ''
  }
}

/**
 * 释放麦克风/摄像头流、录制器与相关缓冲；不修改 localStorage 恢复标记（除 scenario 另有约定外）。
 */
function cleanupMediaResources(scenario = 'unknown') {
  console.log('[Training.cleanup] cleanupMediaResources', { scenario })
  try {
    clearRecordingTimers()
  } catch (_) {}
  try {
    cleanupQaAnswerRecordingHard()
  } catch (_) {}
  try {
    if (mediaStream.value) {
      stopAllMediaTracks(mediaStream.value)
    }
  } catch (_) {}
  mediaStream.value = null
  mediaRecorder.value = null
  audioChunks.value = []
  isRecording.value = false
  try {
    if (videoStream.value) {
      stopAllMediaTracks(videoStream.value)
    }
  } catch (_) {}
  videoStream.value = null
  videoRecorder.value = null
  videoChunks.value = []
  isVideoRecording.value = false
  videoStopRequested.value = false
  try {
    if (cameraPreviewRef.value) {
      cameraPreviewRef.value.srcObject = null
    }
  } catch (_) {}
  recordingMimeType.value = ''
  console.log('[Training.cleanup] cleanupMediaResources done', { scenario })
}

/**
 * 清理可恢复会话相关的本地标记（current_session_id / runtime snapshot / 恢复卡片）。
 * resume / route_leave / beforeunload 不应调用会抹掉可恢复会话的分支。
 */
function clearRecoverableSessionState(scenario = 'unknown') {
  const before = readCurrentSessionIdFromLs()
  console.log('[Training.cleanup] clearRecoverableSessionState', { scenario })
  console.log('[Training.cleanup] current_session_id before=', before || '(empty)')
  if (scenario === 'discard') {
    try {
      removeUserScopedItem(localStorage, CURRENT_SESSION_ID_KEY, undefined, true)
    } catch (_) {}
    clearTrainingRuntimeSnapshot()
    unfinishedResumePrompt.value = null
  } else if (scenario === 'stop_success') {
    clearTrainingRuntimeSnapshot()
  }
  const after = readCurrentSessionIdFromLs()
  console.log('[Training.cleanup] current_session_id after=', after || '(empty)')
}

/**
 * 重置运行期 UI 状态（phase / QA / 提交中标志等），按场景收口，避免污染下一轮。
 */
function resetTrainingRuntimeState(scenario = 'unknown') {
  console.log('[Training.cleanup] resetTrainingRuntimeState', { scenario })
  if (scenario === 'resume') {
    isStopping.value = false
    isSubmittingSession.value = false
    isAnalyzingAudio.value = false
    isAnalyzingVision.value = false
    loading.value = false
    errorMessage.value = ''
    return
  }
  if (scenario === 'restart') {
    isStopping.value = false
    isSubmittingSession.value = false
    isAnalyzingAudio.value = false
    isAnalyzingVision.value = false
    stopSuccess.value = false
    errorMessage.value = ''
    return
  }
  if (scenario === 'stop_finally') {
    loading.value = false
    isSubmittingSession.value = false
    isAnalyzingAudio.value = false
    isAnalyzingVision.value = false
    isStopping.value = false
    return
  }
  if (scenario === 'stop_failed') {
    isGeneratingMockBatch.value = false
    isGeneratingFollowup.value = false
    loading.value = false
    isSubmittingSession.value = false
    isAnalyzingAudio.value = false
    isAnalyzingVision.value = false
    isStopping.value = false
    return
  }
  if (scenario === 'stop_success') {
    resetQaStateForPartialResume()
    qaAnswerText.value = ''
    qaAnswerTranscript.value = ''
    qaAnswerAudioBlob.value = null
    qaAnswerEvaluatePending.value = false
    qaTextFallbackExpanded.value = false
    isAnalyzingQaAudio.value = false
    isQaAnswerRecording.value = false
    sessionId.value = ''
    resumeMediaHintVisible.value = false
    isGeneratingMockBatch.value = false
    isGeneratingFollowup.value = false
    stopSuccess.value = true
    isStopping.value = false
    isSubmittingSession.value = false
    isAnalyzingAudio.value = false
    isAnalyzingVision.value = false
    loading.value = false
    return
  }
  if (scenario === 'discard') {
    resetQaStateForPartialResume()
    qaAnswerText.value = ''
    qaAnswerTranscript.value = ''
    qaAnswerAudioBlob.value = null
    qaAnswerEvaluatePending.value = false
    qaTextFallbackExpanded.value = false
    isAnalyzingQaAudio.value = false
    isQaAnswerRecording.value = false
    sessionId.value = ''
    sessionPhase.value = 'lecture'
    primaryTeacherQaEvalDone.value = false
    resumeMediaHintVisible.value = false
    stopSuccess.value = false
    isGeneratingMockBatch.value = false
    isGeneratingFollowup.value = false
    isStopping.value = false
    isSubmittingSession.value = false
    isAnalyzingAudio.value = false
    isAnalyzingVision.value = false
    loading.value = false
    errorMessage.value = ''
    return
  }
}

const uploadRecordedVideoForAnalysis = async (blob, mimeType) => {
  console.log('[uploadRecordedVideoForAnalysis] begin', { size: blob?.size, mimeType })
  if (!blob || blob.size === 0) {
    console.warn('[uploadRecordedVideoForAnalysis] empty blob, skip upload')
    return null
  }
  const blobType = mimeType || 'video/webm'
  const filename = blobType.includes('mp4') ? 'recording.mp4' : 'recording.webm'
  const formData = new FormData()
  formData.append('file', blob, filename)
  console.log('vision analyze start')
  const response = await uploadFile('/vision/analyze', formData)
  console.log('vision analyze response:', response)
  console.log('vision analyze done')
  const inferredInvalidByZeros =
    response?.vision_valid == null &&
    Number(response?.forward_gaze_ratio ?? NaN) === 0 &&
    Number(response?.downward_head_ratio ?? NaN) === 0 &&
    Number(response?.posture_stability ?? NaN) === 0
  const normalized = {
    forward_gaze_ratio: response?.forward_gaze_ratio,
    downward_head_ratio: response?.downward_head_ratio,
    posture_stability: response?.posture_stability,
    vision_valid: inferredInvalidByZeros ? false : response?.vision_valid,
    vision_message:
      response?.vision_message ||
      (inferredInvalidByZeros ? '有效检测帧过少，无法生成稳定视觉指标' : ''),
    vision_debug_source: response?.vision_debug_source,
    vision_debug_provider: response?.vision_debug_provider,
    vision_debug_request_id: response?.vision_debug_request_id,
  }
  /** /vision/analyze 长时会话摘要字段：原样并入 stop payload（与 backend vision.py 透传一致） */
  const VISION_ANALYZE_EXTRA_KEYS = [
    'processed_frames',
    'skipped_frames',
    'total_video_duration_sec',
    'sampled_mode_used',
    'sampled_fps',
    'valid_detection_frames',
    'total_frames',
    'vision_original_fps',
    'vision_sampled_fps',
    'vision_skipped_frames',
    'vision_sampled_mode_used',
    'vision_analysis_elapsed_ms',
    'vision_metrics_scope',
  ]
  if (response && typeof response === 'object') {
    for (const k of VISION_ANALYZE_EXTRA_KEYS) {
      if (Object.prototype.hasOwnProperty.call(response, k) && response[k] != null) {
        normalized[k] = response[k]
      }
    }
  }
  visionAnalysis.value = normalized
  if (normalized.vision_valid === false) {
    const msg = normalized.vision_message || '有效检测帧过少，请调整机位、光照或靠近镜头后重试'
    errorMessage.value = `本次视觉分析未成功：${msg}`
  }
  if (normalized.vision_valid !== false) {
    if (normalized.forward_gaze_ratio != null) {
      metrics.value.forward_gaze_ratio = Number(normalized.forward_gaze_ratio)
    }
    if (normalized.downward_head_ratio != null) {
      metrics.value.downward_head_ratio = Number(normalized.downward_head_ratio)
    }
    if (normalized.posture_stability != null) {
      metrics.value.posture_stability = Number(normalized.posture_stability)
    }
  }
  console.log('[uploadRecordedVideoForAnalysis] success', normalized)
  return normalized
}

// 停止会话
const stopSession = async () => {
  if (!sessionId.value) {
    errorMessage.value = '请先开始训练'
    return
  }

  const stopDebugTranscript = () => {
    const spoken = String(spokenText.value ?? '').trim()
    const aa = audioAnalysis.value
    let tr = ''
    let merged = ''
    if (aa && typeof aa === 'object') {
      tr = String(aa.transcript ?? '').trim()
      merged = String(aa.merged_transcript ?? '').trim()
    }
    const parts = [tr, merged, spoken].filter(Boolean)
    const finalForContent = parts.length ? [...parts].sort((a, b) => b.length - a.length)[0] : ''
    return { spoken, transcript: tr, merged, finalForContent }
  }
  const _stopDbgCtx = stopDebugTranscript()
  console.log('[Training.stop.debug] bestLectureAutoPptMatchPlain=', bestLectureAutoPptMatchPlain.value)
  console.log('[Training.stop.debug] lectureLatestAutoPptMatchPlain=', lectureLatestAutoPptMatchPlain.value)
  console.log('[Training.stop.debug] lectureAutoGuessFinalMatch=', lectureAutoGuessFinalMatch.value)
  console.log('[Training.stop.debug] lastPptMatchResult=', lastPptMatchResult.value)
  console.log('[Training.stop.debug] resolved ppt_id=', resolveCurrentPptId() || null)
  console.log('[Training.stop.debug] lectureTranscriptContext=', _stopDbgCtx)
  console.log(
    '[Training.stop.debug] final transcript text for content=',
    _stopDbgCtx.finalForContent || '(empty)'
  )
  console.log('[Training.stop.debug] last auto_guess raw=', resolveLectureAutoGuessRawForStop())

  console.log('[frontend.stop] clicked')
  const stopFlowT0 = performance.now()
  let stopCleanupSuccess = false
  errorMessage.value = ''
  isStopping.value = true
  stopSuccess.value = false

  const shouldStopAudio = isRecording.value || mediaRecorder.value
  const shouldStopVideo = isVideoRecording.value || videoRecorder.value

  try {
    let audioStopResult = {
      blob: null,
      mimeType: recordingMimeType.value || 'audio/webm',
    }
    let videoStopResult = {
      blob: null,
      mimeType: videoMimeType.value || 'video/webm',
    }

    const stopTasks = []
    if (shouldStopAudio) {
      stopTasks.push(
        (async () => {
          isAnalyzingAudio.value = true
          try {
            console.log('[stopSession] A: stopLocalRecording() (parallel)')
            audioStopResult = await stopLocalRecording()
            console.log('[stopSession] B: stopLocalRecording done, blob size=', audioStopResult?.blob?.size)
          } finally {
            isAnalyzingAudio.value = false
            console.log('[stopSession] D: isAnalyzingAudio=false')
          }
        })()
      )
    } else {
      console.log('[stopSession] skip recording: not recording')
      if (mediaStream.value) {
        try {
          stopAllMediaTracks(mediaStream.value)
        } catch (e) {
          console.error('[frontend.stop] cleanup error', e)
        }
        mediaStream.value = null
        mediaRecorder.value = null
      }
      isRecording.value = false
    }

    if (shouldStopVideo) {
      stopTasks.push(
        (async () => {
          isAnalyzingVision.value = true
          try {
            console.log('[stopSession] V1: stopLocalVideoRecording() (parallel)')
            videoStopResult = await stopLocalVideoRecording()
            console.log('[stopSession] V2: stopLocalVideoRecording done, blob size=', videoStopResult?.blob?.size)
          } finally {
            isAnalyzingVision.value = false
          }
        })()
      )
    } else {
      console.log('[stopSession] skip video recording: not recording')
      if (videoStream.value) {
        try {
          stopAllMediaTracks(videoStream.value)
        } catch (e) {
          console.error('[frontend.stop] cleanup error', e)
        }
        videoStream.value = null
        if (cameraPreviewRef.value) {
          cameraPreviewRef.value.srcObject = null
        }
      }
      isVideoRecording.value = false
    }

    await Promise.all(stopTasks)

    console.log('[stopSession.baseline] audio_blob_bytes=', audioStopResult?.blob?.size ?? 0)
    console.log('[stopSession.baseline] video_blob_bytes=', videoStopResult?.blob?.size ?? 0)

    let audioAnalyzeMs = null
    let visionAnalyzeMs = null

    if (audioStopResult.blob && audioStopResult.blob.size > 0) {
      console.log('[stopSession] C: uploadRecordedAudioForAnalysis (backend /audio/analyze)')
      try {
        const _a0 = performance.now()
        await uploadRecordedAudioForAnalysis(audioStopResult.blob, audioStopResult.mimeType)
        audioAnalyzeMs = Math.round(performance.now() - _a0)
        console.log('[stopSession.baseline] audio_analyze_elapsed_ms=', audioAnalyzeMs)
      } catch (e) {
        console.error('[stopSession] audio analyze failed', e)
        const msg = String(e?.message || e || '')
        if (msg.includes('超时') || msg.toLowerCase().includes('timeout')) {
          errorMessage.value = '语音分析超时，本轮仅保留视觉结果；可缩短录音时长后重试'
          audioAnalysis.value = buildInvalidAudioAnalysis(
            '语音分析超时，请缩短录音时长或稍后重试'
          )
        } else {
          errorMessage.value = `音频分析失败：${e.message || e}`
          audioAnalysis.value = buildInvalidAudioAnalysis(
            e?.message || '音频分析失败，请稍后重试'
          )
        }
      }
    } else if (shouldStopAudio) {
      console.warn('[stopSession] no audio blob to upload')
    }

    if (videoStopResult.blob && videoStopResult.blob.size > 0) {
      console.log('[stopSession] V3: uploadRecordedVideoForAnalysis (backend /vision/analyze)')
      try {
        const _v0 = performance.now()
        await uploadRecordedVideoForAnalysis(videoStopResult.blob, videoStopResult.mimeType)
        visionAnalyzeMs = Math.round(performance.now() - _v0)
        console.log('[stopSession.baseline] vision_analyze_elapsed_ms=', visionAnalyzeMs)
      } catch (e) {
        console.error('[stopSession] vision analyze failed', e)
        errorMessage.value = `视觉分析失败：${e.message || e}`
      }
    } else if (shouldStopVideo) {
      console.warn('[stopSession] no video blob to upload')
    }

    let plainPptMatch = null
    let pptMatchSourcePayload = null
    let pptMatchSourceDecision = 'none'
    if (lastPptMatchResult.value) {
      plainPptMatch = JSON.parse(JSON.stringify(lastPptMatchResult.value))
      plainPptMatch.match_source = plainPptMatch.match_source || 'manual'
      pptMatchSourcePayload = 'manual'
      pptMatchSourceDecision = 'manual'
    } else if (bestLectureAutoPptMatchPlain.value) {
      plainPptMatch = JSON.parse(JSON.stringify(bestLectureAutoPptMatchPlain.value))
      pptMatchSourcePayload = 'auto_guess'
      pptMatchSourceDecision = 'bestLectureAutoPptMatchPlain'
    } else if (lectureAutoGuessFinalMatch.value) {
      plainPptMatch = JSON.parse(JSON.stringify(lectureAutoGuessFinalMatch.value))
      pptMatchSourcePayload = 'auto_guess'
      pptMatchSourceDecision = 'lectureAutoGuessFinalMatch'
    } else if (lectureLatestAutoPptMatchPlain.value) {
      plainPptMatch = JSON.parse(JSON.stringify(lectureLatestAutoPptMatchPlain.value))
      pptMatchSourcePayload = 'auto_guess'
      pptMatchSourceDecision = 'lectureLatestAutoPptMatchPlain'
    } else {
      const ag = resolveLectureAutoGuessRawForStop()
      plainPptMatch = convertAutoGuessToPlainPptMatch(ag, pptInfo.value?.pages || [])
      if (plainPptMatch) {
        pptMatchSourcePayload = 'auto_guess'
        pptMatchSourceDecision = 'convertAutoGuessRaw'
      }
    }

    if (!plainPptMatch) {
      const agRaw = resolveLectureAutoGuessRawForStop()
      const convOut = convertAutoGuessToPlainPptMatch(agRaw, pptInfo.value?.pages || [])
      console.log('[Training.stop.debug] no plain ppt_match after primary chain; last auto_guess raw=', agRaw)
      console.log('[Training.stop.debug] convertAutoGuessToPlainPptMatch input pages len=', (pptInfo.value?.pages || []).length)
      console.log('[Training.stop.debug] convertAutoGuessToPlainPptMatch output=', convOut)
    }

    let plainAudioAnalysis = audioAnalysis.value
      ? JSON.parse(JSON.stringify(audioAnalysis.value))
      : null
    const plainVisionAnalysis = visionAnalysis.value
      ? JSON.parse(JSON.stringify(visionAnalysis.value))
      : null
    const plainPptTextData = pptTextData.value
      ? JSON.parse(JSON.stringify(pptTextData.value))
      : null

    // 无效语音：仍提交 session/stop，但不把幻听转写当作有效语言内容写入会话
    if (plainAudioAnalysis && plainAudioAnalysis.audio_valid === false) {
      plainAudioAnalysis = buildInvalidAudioAnalysis(
        plainAudioAnalysis.audio_message || '未检测到有效语音，请靠近麦克风后重试'
      )
    }
    if (
      !plainVisionAnalysis ||
      plainVisionAnalysis.forward_gaze_ratio == null ||
      plainVisionAnalysis.downward_head_ratio == null ||
      plainVisionAnalysis.posture_stability == null
    ) {
      errorMessage.value = '视觉分析未完成，本次视觉结果将标记为无效'
    }

    let plainQa = null
    let qaSourcePayload = null
    const hasManualQa =
      lastManualQaResult.value != null && typeof lastManualQaResult.value === 'object'
    const hasFollowupQa =
      lastFollowupQaResult.value != null && typeof lastFollowupQaResult.value === 'object'
    const hasAutoQa =
      lastAutoQaResult.value != null && typeof lastAutoQaResult.value === 'object'
    if (hasManualQa) {
      plainQa = JSON.parse(JSON.stringify(lastManualQaResult.value))
      qaSourcePayload = 'manual'
    } else if (hasFollowupQa) {
      plainQa = JSON.parse(JSON.stringify(lastFollowupQaResult.value))
      qaSourcePayload = 'followup_generated'
    } else if (hasAutoQa) {
      plainQa = JSON.parse(JSON.stringify(lastAutoQaResult.value))
      qaSourcePayload = 'auto_generated'
    }
    if (plainQa) {
      plainQa.qa_source = qaSourcePayload
    }
    if (plainQa && qaSourcePayload === 'followup_generated' && lastFollowupGenerationContext.value) {
      const ctx = lastFollowupGenerationContext.value
      if (ctx.followup_provider_kind != null) plainQa.followup_provider_kind = ctx.followup_provider_kind
      if (ctx.followup_generation_meta != null) plainQa.followup_generation_meta = ctx.followup_generation_meta
      if (ctx.followup_fallback_to_rule != null) plainQa.followup_fallback_to_rule = ctx.followup_fallback_to_rule
      console.log('[Training.followup.source] provider_kind=', plainQa.followup_provider_kind)
      console.log(
        '[Training.followup.source] provider_label=',
        plainQa.followup_generation_meta?.provider_label
      )
      console.log('[Training.followup.source] fallback_to_rule=', plainQa.followup_fallback_to_rule)
      console.log(
        '[Training.followup.source] resolved display label=',
        resolveFollowupTaxonomyShortLabel(plainQa)
      )
    }
    console.log('[Training] stop payload qa_result', plainQa, 'qa_source=', qaSourcePayload)

    console.log('[Training.stop] defenseMaterialMode=', defenseMaterialMode.value)
    console.log(
      '[Training.focus] recommended_training_focus=',
      recommendedTrainingFocus.value ?? '(none)'
    )
    console.log('[Training.focus] final training_focus=', finalTrainingFocus.value)
    console.log('[Training.stop] training_focus=', finalTrainingFocus.value)
    const payload = {
      session_id: sessionId.value,
      training_focus: finalTrainingFocus.value,
      defense_material_mode: defenseMaterialMode.value,
      ppt_id: resolveCurrentPptId() || null,
      lecture_spoken_text: String(spokenText.value ?? '').trim() || null,
      client_audio_blob_bytes: audioStopResult?.blob?.size ?? null,
      client_video_blob_bytes: videoStopResult?.blob?.size ?? null,
      client_audio_analyze_elapsed_ms: audioAnalyzeMs,
      client_vision_analyze_elapsed_ms: visionAnalyzeMs,
      scoring_profile: trainingScoringProfile.value,
      metrics: {
        speech_rate: Number(metrics.value.speech_rate),
        pause_count: Number(metrics.value.pause_count),
        avg_pause_sec: Number(metrics.value.avg_pause_sec),
        filler_count: Number(metrics.value.filler_count),
        forward_gaze_ratio: Number(metrics.value.forward_gaze_ratio),
        downward_head_ratio: Number(metrics.value.downward_head_ratio),
        posture_stability: Number(metrics.value.posture_stability)
      },
      ppt_match: plainPptMatch,
      ppt_match_source: pptMatchSourcePayload,
      ppt_text_data: plainPptTextData,
      qa_result: plainQa,
      qa_source: qaSourcePayload,
      followup_questions_chain: lastFollowupQuestionsSnapshot.value,
      followup_chain_depth: qaSourcePayload === 'followup_generated' ? 1 : null,
      followup_used: qaSourcePayload === 'followup_generated' ? true : null,
      selected_followup_reason:
        qaSourcePayload === 'followup_generated'
          ? plainQa?.followup_reason || selectedFollowupMeta.value?.reason || null
          : null,
      audio_analysis: plainAudioAnalysis,
      vision_analysis: plainVisionAnalysis
    }
    console.log('[Training] final stop payload ppt_match', plainPptMatch)
    console.log('[Training] final stop payload ppt_match_source', payload.ppt_match_source ?? null)
    console.log('[Training] source decision =', pptMatchSourceDecision)
    const decisionTri =
      pptMatchSourceDecision === 'manual'
        ? 'manual'
        : pptMatchSourceDecision === 'bestLectureAutoPptMatchPlain'
          ? 'bestLectureAutoPptMatchPlain'
          : plainPptMatch
            ? 'other_resolved'
            : 'none'
    console.log('[Training.stop.debug] source decision (manual|bestLectureAutoPptMatchPlain|none~)=', decisionTri)
    console.log(
      '[Training] stop payload qa_source',
      payload.qa_source ?? null,
      'followup_used=',
      payload.followup_used,
      'selected_followup_reason=',
      payload.selected_followup_reason
    )
    console.log(
      '[Training] stop: scoring_profile / mode in payload =',
      payload.scoring_profile,
      'full stop payload keys:',
      Object.keys(payload)
    )
    console.log('stop payload audio_analysis:', payload.audio_analysis)
    console.log('stop payload vision_analysis:', payload.vision_analysis)
    console.log('stop payload:', payload)
    isSubmittingSession.value = true
    try {
      console.log('session stop start')
      console.log('[stopSession] F: POST /session/stop')
      const _stop0 = performance.now()
      const response = await postJson('/session/stop', payload)
      const stopTotalMs = Math.round(performance.now() - _stop0)
      console.log('[stopSession.baseline] session_stop_total_elapsed_ms=', stopTotalMs)
      apiResult.value = JSON.stringify(response, null, 2)
      console.log('[stopSession] G: /session/stop response', response)
      console.log('[frontend.stop] session stop done')
      console.log('session stop done')
      if (response.status !== 'completed') {
        errorMessage.value =
          response.message || '结束训练未成功完成，服务器未保存结果，已取消跳转结果页'
        console.warn('[stopSession] stop API status not completed; 本地录音已停止，不会恢复录音')
        return
      }
      const sid = response.session_id || sessionId.value
      if (!sid) {
        errorMessage.value = '结束训练成功但未返回会话 ID，无法跳转结果页'
        return
      }
      persistCurrentSessionId(sid)
      clearRecoverableSessionState('stop_success')
      resetTrainingRuntimeState('stop_success')
      stopCleanupSuccess = true
      const goResult = () => {
        router.push({
          name: 'Result',
          params: { sessionId: sid },
          query: { session_id: sid },
        })
      }
      setTimeout(goResult, 500)
    } finally {
      isSubmittingSession.value = false
    }
  } catch (e) {
    console.error('[stopSession] stop training failed:', e)
    apiResult.value = `错误: ${e.message}`
    errorMessage.value = `结束训练失败：${e.message}`
    console.warn('[stopSession] 接口失败；本地录音已停止，不会自动恢复录音')
  } finally {
    console.log(
      '[stopSession.baseline] stop_flow_total_elapsed_ms=',
      Math.round(performance.now() - stopFlowT0)
    )
    console.log('[Training.cleanup] scenario=', 'stop')
    cleanupMediaResources('stop')
    if (!stopCleanupSuccess) {
      resetTrainingRuntimeState('stop_failed')
    } else {
      resetTrainingRuntimeState('stop_finally')
    }
  }
}

// 处理文件选择
const handleFileChange = (file) => {
  console.log('文件选择事件:', file)
  const fileName = file.name || ''
  const fileExt = fileName.split('.').pop().toLowerCase()
  if (fileExt !== 'pptx') {
    errorMessage.value = '当前仅支持 .pptx 文件，请先另存为 .pptx 后上传。'
    selectedFile.value = null
    return
  }
  selectedFile.value = file.raw
  pptUploadFailed.value = false
  isUploadingPpt.value = false
  pptInfo.value = null
  cachedPptIdFallback.value = ''
  try {
    removeUserScopedItem(localStorage, LAST_PPT_ID_STORAGE_KEY, undefined, true)
  } catch (_) {}
  console.log('[Training.ppt.status] selected file=', fileName || '(unnamed)')
  errorMessage.value = ''
  if (!sessionId.value) {
    runPreflightChecks()
  }
}

// 上传 PPT
const uploadPPT = async () => {
  errorMessage.value = ''
  console.log('点击上传按钮')
  if (!selectedFile.value) {
    console.log('没有选择文件')
    errorMessage.value = '请先选择 PPT 文件'
    return
  }

  pptUploadFailed.value = false
  isUploadingPpt.value = true
  console.log('[Training.ppt.status] upload started')
  console.log('开始上传 PPT（先 /ppt/upload 再 /ppt/parse）:', selectedFile.value)
  try {
    const file = selectedFile.value

    // 1) 必须先 /ppt/upload：后端生成真实 ppt_id 并写入 ppt_store，单页 /ppt/match 与 /qa/* 依赖此 ID
    const formUpload = new FormData()
    formUpload.append('file', file)
    const uploadResponse = await uploadFile('/ppt/upload', formUpload)
    console.log('PPT upload 成功:', uploadResponse)
    const pages = Array.isArray(uploadResponse?.pages) ? uploadResponse.pages : []
    const newPptId = String(uploadResponse?.ppt_id ?? '').trim()
    const document = uploadResponse?.document ?? null
    console.log('[Training.ppt.status] upload success ppt_id=', newPptId || '(empty)')
    const ready = pptServerPayloadLooksReady(pages, document)
    console.log('[Training.ppt.status] upload ready=', ready)
    if (!newPptId || !ready) {
      throw new Error('服务器未返回可用的课件结构（需有效 ppt_id 且含页面或文档大纲）')
    }
    pptInfo.value = {
      ppt_id: newPptId,
      pages,
      ...(document && typeof document === 'object' ? { document } : {}),
    }
    if (newPptId) {
      cachedPptIdFallback.value = newPptId
      try {
        writeUserScopedItem(localStorage, LAST_PPT_ID_STORAGE_KEY, newPptId)
      } catch (_) {}
      console.log('[Training] upload persisted ppt_id for store alignment', newPptId)
    }
    clearLectureAutoGuessPersistence()

    // 2) 再请求 /ppt/parse，得到 full_text + slides，供 session/stop 的 ppt_text_data；404 则用语义页拼装
    let parseResponse = null
    try {
      const formParse = new FormData()
      formParse.append('file', file)
      parseResponse = await uploadFile('/ppt/parse', formParse)
      console.log('PPT parse 成功:', parseResponse)
    } catch (e) {
      const msg = String(e?.message || e || '')
      if (!/status:\s*404/i.test(msg)) {
        throw e
      }
      console.warn('后端未提供 /ppt/parse，ppt_text_data 由 upload 的 pages 构造')
    }

    if (parseResponse && Array.isArray(parseResponse.slides) && parseResponse.slides.length > 0) {
      pptTextData.value = {
        full_text: parseResponse.full_text || '',
        slides: parseResponse.slides.map((s, idx) => ({
          page: Number(s?.page) || idx + 1,
          text: s?.text || '',
        })),
      }
    } else {
      const fallbackSlides = pages.map((p, idx) => {
        const page = Number(p?.page_index) || idx + 1
        const title = p?.title || `第${page}页`
        const keywords = Array.isArray(p?.keywords) ? p.keywords : []
        const text = [title, ...keywords].filter(Boolean).join('；')
        return { page, text }
      })
      pptTextData.value = {
        full_text: fallbackSlides.map((s) => s.text).join('\n').trim(),
        slides: fallbackSlides,
      }
    }

    if (!selectedPageIndex.value && Array.isArray(pptInfo.value?.pages) && pptInfo.value.pages.length > 0) {
      selectedPageIndex.value = pptInfo.value.pages[0].page_index
    }

    apiResult.value = JSON.stringify(
      {
        mode: 'upload_then_parse',
        ppt_id: pptInfo.value.ppt_id,
        full_text: pptTextData.value.full_text,
        slides_count: pptTextData.value.slides.length,
        slides_preview: pptTextData.value.slides.slice(0, 3),
      },
      null,
      2
    )
    trainingFeedback(
      'ppt_upload_parse',
      'success',
      '课件已上传并解析完成，可按页面提示继续并完成准备检查。'
    )
  } catch (e) {
    console.error('上传错误:', e)
    console.log('[Training.ppt.status] upload failed=', e?.message || e)
    pptUploadFailed.value = true
    pptInfo.value = null
    apiResult.value = `上传错误: ${e.message}`
    errorMessage.value = mapFriendlyPptUploadError(e, 'PPT 上传失败，请确认文件后重试。')
  } finally {
    isUploadingPpt.value = false
  }
  if (!sessionId.value) {
    runPreflightChecks()
  }
}

// 测试匹配度
const guessCurrentPage = async () => {
  errorMessage.value = ''
  autoGuessResult.value = null
  const pid = resolveCurrentPptId()
  console.log('[Training] resolved current ppt id', pid || '(empty)')
  if (!pid) {
    errorMessage.value = '请先上传并解析 PPT'
    return
  }
  if (!String(spokenText.value ?? '').trim()) {
    errorMessage.value = '请先输入口述 / 讲解文本'
    return
  }
  try {
    const status = await fetchPptStatus(pid)
    console.log('[Training] ppt status before auto guess', status)
    if (status && status.exists === false) {
      errorMessage.value = '当前 PPT 解析状态丢失，请重新上传'
      return
    }
  } catch (err) {
    console.warn('[Training] ppt status check failed (continuing)', err)
  }
  const autoGuessBody = {
    ppt_id: pid,
    spoken_text: String(spokenText.value ?? ''),
  }
  console.log('[Training] auto guess request body', JSON.stringify(autoGuessBody))
  try {
    const response = await postJson('/ppt/match_v1', autoGuessBody)
    console.log('[Training] auto guess response body', response)
    autoGuessResult.value = response
    recordLectureAutoGuessSnapshot(response)
    apiResult.value = JSON.stringify(response, null, 2)
  } catch (e) {
    console.error('[Training] auto guess failed (full error)', e)
    apiResult.value = ''
    errorMessage.value = pickApiDetailMessage(
      e,
      '猜当前页失败，请确认已上传 PPT 并填写讲解文本后重试'
    )
  }
}

const testMatch = async () => {
  errorMessage.value = ''
  const pid = resolveCurrentPptId()
  if (!pid) {
    errorMessage.value = '请先上传 PPT'
    return
  }
  if (!selectedPageIndex.value) {
    errorMessage.value = '请选择页面'
    return
  }
  if (!spokenText.value) {
    errorMessage.value = '请输入讲解文本'
    return
  }
  try {
    const response = await postJson('/ppt/match', {
      ppt_id: pid,
      page_index: selectedPageIndex.value,
      spoken_text: spokenText.value
    })
    matchResult.value = response
    lastPptMatchResult.value = { ...response, match_source: 'manual' }
    console.log('saved ppt match result:', lastPptMatchResult.value)
    apiResult.value = JSON.stringify(response, null, 2)
  } catch (e) {
    console.error('匹配错误:', e)
    apiResult.value = `匹配错误: ${e.message}`
    errorMessage.value = `PPT 匹配失败：${e.message}`
  }
}

const selectMockQuestionForQa = (idx) => {
  const item = mockQuestionsList.value[idx]
  const qText = displayMockQuestionText(item)
  console.log('[Training] selected mock question', { idx, item, qText })
  if (!qText) {
    errorMessage.value =
      '该条未能解析为题干，请重新生成列表。若持续出现，请检查接口返回是否包含 question 字段。'
    console.warn('[Training] selected mock question: empty text', item)
    return
  }
  selectedMockQuestionIndex.value = idx
  selectedMockQuestion.value = item && typeof item === 'object' ? { ...item } : { question: qText }
  currentQaQuestion.value = qText
  const ek = item?.expected_keywords ?? item?.keywords
  currentQaExpectedKeywords.value = Array.isArray(ek) ? ek.map((x) => String(x)) : []
  qaAnswerText.value = ''
  qaEvaluationResult.value = null
  lastQaResult.value = null
  lastManualQaResult.value = null
  lastAutoQaResult.value = null
  lastFollowupQaResult.value = null
  followupQuestions.value = []
  followupSectionVisible.value = false
  selectedFollowupIndex.value = -1
  selectedFollowupQuestion.value = null
  lastFollowupQuestionsSnapshot.value = null
  lastFollowupGenerationContext.value = null
  selectedFollowupMeta.value = null
  qaRoundSource.value = 'auto_generated'
  primaryTeacherQaEvalDone.value = false
  errorMessage.value = ''
  autoFollowupFirstRoundAttempted.value = false
  qaAutoFollowupHint.value = ''
  resetQaAnswerWorkspaceOnly()
  console.log('[Training] current qa question', currentQaQuestion.value)
}

/**
 * 仅清问答语音作答硬件与表单；禁止触碰 lecture 自动猜页 / ppt_match 链。
 * 进入答辩前完整清空问答 UI 请用 clearTrainingQaWorkspaceForQaPhase（内部会先调用本函数）。
 */
const resetQaAnswerWorkspaceOnly = () => {
  cleanupQaAnswerRecordingHard()
  qaAnswerMode.value = 'voice'
  qaTextFallbackExpanded.value = false
  qaAnswerTranscript.value = ''
  qaAnswerAudioBlob.value = null
  lastQaAnswerInputMode.value = 'voice'
  isAnalyzingQaAudio.value = false
  qaAnswerEvaluatePending.value = false
}

/** 进入答辩问答阶段前清空上一轮问答与追问 UI（不含 lecture 内容链） */
const clearTrainingQaWorkspaceForQaPhase = () => {
  resetQaAnswerWorkspaceOnly()
  qaEvaluationResult.value = null
  lastQaResult.value = null
  lastManualQaResult.value = null
  lastAutoQaResult.value = null
  lastFollowupQaResult.value = null
  currentQaQuestion.value = ''
  currentQaExpectedKeywords.value = []
  qaAnswerText.value = ''
  mockQuestionsList.value = []
  selectedMockQuestionIndex.value = -1
  selectedMockQuestion.value = null
  followupQuestions.value = []
  followupSectionVisible.value = false
  selectedFollowupIndex.value = -1
  selectedFollowupQuestion.value = null
  lastFollowupQuestionsSnapshot.value = null
  lastFollowupGenerationContext.value = null
  lastQuestionGenerationContext.value = null
  selectedFollowupMeta.value = null
  qaRoundSource.value = 'manual'
  primaryTeacherQaEvalDone.value = false
  qaPhaseAutoQuestionTip.value = ''
  mockQuestionBankExpanded.value = false
  autoFollowupFirstRoundAttempted.value = false
  qaAutoFollowupHint.value = ''
}

/**
 * 讲解阶段可用文本（优先 lecture 转写上下文 transcript / merged_transcript，其次口述框），供进入 QA 时自动猜页。
 * 不依赖 audio_valid：只要转写非空即可用于 match_v1（与 stop 侧 fallback 一致）。
 */
const resolveEnterQaPhaseSpokenTextForAutoGuess = () => {
  const aa = audioAnalysis.value
  let tr = ''
  let merged = ''
  if (aa && typeof aa === 'object') {
    tr = String(aa.transcript ?? '').trim()
    merged = String(aa.merged_transcript ?? '').trim()
  }
  const spoken = String(spokenText.value ?? '').trim()
  if (tr) return tr
  if (merged) return merged
  if (spoken) return spoken
  return ''
}

/**
 * 讲解结束进入答辩：无手动匹配时自动调用 match_v1，落成 lecture 持久链与 lectureAutoGuessFinalMatch。
 * @param {string} [preferredTextFromPreStop] 在收口讲解录音/上传覆盖 audioAnalysis 之前快照的文本（优先使用）
 */
const runEnterQaPhaseAutoGuess = async (preferredTextFromPreStop = '') => {
  if (lastPptMatchResult.value) {
    console.log('[Training.auto_guess] skip: manual ppt_match already set')
    return
  }
  const pid = resolveCurrentPptId()
  const spokenForGuess =
    String(preferredTextFromPreStop ?? '').trim() || resolveEnterQaPhaseSpokenTextForAutoGuess()
  if (!pid) {
    console.log('[Training.auto_guess] skip: no ppt_id')
    return
  }
  if (!spokenForGuess) {
    console.log('[Training.auto_guess] skip: no lecture text (transcript/merged/spoken all empty)')
    return
  }
  console.log('[Training.auto_guess] trigger on enter qa phase', { ppt_id: pid, text_len: spokenForGuess.length })
  try {
    const status = await fetchPptStatus(pid)
    if (status && status.exists === false) {
      console.warn('[Training.auto_guess] skipped: ppt not in store')
      return
    }
  } catch (err) {
    console.warn('[Training.auto_guess] ppt status check failed (continuing)', err)
  }
  const autoGuessBody = {
    ppt_id: pid,
    spoken_text: spokenForGuess,
  }
  console.log('[Training.auto_guess] request body', JSON.stringify(autoGuessBody))
  try {
    const response = await postJson('/ppt/match_v1', autoGuessBody)
    console.log('[Training.auto_guess] response body', response)
    if (autoGuessApiResponseLooksSuccessful(response)) {
      recordLectureAutoGuessSnapshot(response)
      console.log('[Training.auto_guess] saved raw', lectureLatestAutoGuessRaw.value)
      console.log('[Training.auto_guess] saved plain ppt_match', lectureLatestAutoPptMatchPlain.value)
      const plain = lectureLatestAutoPptMatchPlain.value
      if (plain) {
        lectureAutoGuessFinalMatch.value = JSON.parse(JSON.stringify(plain))
        console.log('[Training.auto_guess] lectureAutoGuessFinalMatch', lectureAutoGuessFinalMatch.value)
      }
    }
  } catch (e) {
    console.error('[Training.auto_guess] request failed', e)
  }
}

/** 进入答辩前收口讲解麦克风录制（不等于整场停止训练；讲解视频录制可按主链继续） */
const autoStopLectureAudioForQaPhase = async () => {
  const rec = mediaRecorder.value
  const lectureAudioBusy =
    isRecording.value || (rec != null && typeof rec.state === 'string' && rec.state !== 'inactive')
  if (!lectureAudioBusy) {
    return
  }
  console.log('[Training] auto stop lecture audio for qa phase')
  isAnalyzingAudio.value = true
  try {
    const lec = await stopLocalRecording()
    console.log('[Training] lecture audio stopped for qa phase', {
      blobBytes: lec?.blob?.size ?? 0,
    })
    if (lec?.blob && lec.blob.size > 0) {
      try {
        await uploadRecordedAudioForAnalysis(lec.blob, lec.mimeType)
      } catch (e) {
        console.warn('[Training] lecture audio analyze after qa transition failed', e)
      }
    }
  } finally {
    isAnalyzingAudio.value = false
  }
}

/** 真实答辩时序：讲解结束后进入问答，并自动生成批量题目 */
const finishLectureEnterQa = async () => {
  if (!sessionId.value) {
    errorMessage.value = '请先开始训练'
    return
  }
  const ctx0 = lectureTranscriptContextSummary.value
  console.log('[Training] before enter qa keep lecture content context', {
    ...ctx0,
    bestLectureAutoPptMatchPlain: bestLectureAutoPptMatchPlain.value,
    lectureLatestAutoPptMatchPlain: lectureLatestAutoPptMatchPlain.value,
    lectureAutoGuessFinalMatch: lectureAutoGuessFinalMatch.value,
    hasManualPptMatch: !!lastPptMatchResult.value,
  })
  console.log(
    '[Training] before enter qa bestLectureAutoPptMatchPlain preserved=',
    bestLectureAutoPptMatchPlain.value != null
  )
  console.log(
    '[Training] before enter qa lecture transcript context preserved=',
    ctx0.lectureTranscriptLen > 0 || ctx0.spokenTextLen > 0
  )
  console.log('[Training] enter qa phase begin')
  const lectureGuessTextSnapshot = resolveEnterQaPhaseSpokenTextForAutoGuess()
  console.log('[Training.auto_guess] snapshot before lecture audio stop (enter qa)', {
    len: lectureGuessTextSnapshot.length,
  })
  await autoStopLectureAudioForQaPhase()
  if (!lastPptMatchResult.value) {
    if (bestLectureAutoPptMatchPlain.value) {
      lectureAutoGuessFinalMatch.value = JSON.parse(JSON.stringify(bestLectureAutoPptMatchPlain.value))
    } else if (lectureLatestAutoPptMatchPlain.value) {
      lectureAutoGuessFinalMatch.value = JSON.parse(JSON.stringify(lectureLatestAutoPptMatchPlain.value))
    }
  }
  clearTrainingQaWorkspaceForQaPhase()
  sessionPhase.value = 'qa'
  errorMessage.value = ''
  const ctx1 = lectureTranscriptContextSummary.value
  console.log('[Training] after enter qa keep lecture content context', {
    ...ctx1,
    bestLectureAutoPptMatchPlain: bestLectureAutoPptMatchPlain.value,
    lectureLatestAutoPptMatchPlain: lectureLatestAutoPptMatchPlain.value,
    lectureAutoGuessFinalMatch: lectureAutoGuessFinalMatch.value,
    hasManualPptMatch: !!lastPptMatchResult.value,
  })
  console.log(
    '[Training] after enter qa bestLectureAutoPptMatchPlain preserved=',
    bestLectureAutoPptMatchPlain.value != null
  )
  console.log(
    '[Training] after enter qa lecture transcript context preserved=',
    ctx1.lectureTranscriptLen > 0 || ctx1.spokenTextLen > 0
  )
  console.log('[Training] enter qa phase keep ppt context', {
    latestAutoGuessRaw: lectureLatestAutoGuessRaw.value,
    bestLectureAutoGuessRaw: bestLectureAutoGuessRaw.value,
    latestAutoPptMatchPlain: lectureLatestAutoPptMatchPlain.value,
    bestLecturePptMatchPlain: bestLectureAutoPptMatchPlain.value,
    manualMatch: lastPptMatchResult.value,
    latestAutoPptMatchPlainPreserved: lectureLatestAutoPptMatchPlain.value != null,
    bestLecturePptMatchPlainPreserved: bestLectureAutoPptMatchPlain.value != null,
  })
  console.log('[Training] finish lecture -> qa phase, auto mock batch')
  await runEnterQaPhaseAutoGuess(lectureGuessTextSnapshot)
  await generateMockQuestionsBatch({ fromEnterQa: true })
  console.log('[Training] qa phase ready for voice answer')
}

const generateMockQuestionsBatch = async (options = {}) => {
  const fromEnterQa = options.fromEnterQa === true
  if (fromEnterQa) {
    console.log('[Training] enter qa phase auto generate questions')
  }

  errorMessage.value = ''
  qaPhaseAutoQuestionTip.value = ''
  mockQuestionsList.value = []
  lastQuestionGenerationContext.value = null
  selectedMockQuestionIndex.value = -1
  selectedMockQuestion.value = null
  currentQaQuestion.value = ''
  currentQaExpectedKeywords.value = []
  qaAnswerText.value = ''
  autoFollowupFirstRoundAttempted.value = false
  qaAutoFollowupHint.value = ''

  const pid = resolveCurrentPptId()
  console.log('[Training] resolved current ppt id', pid || '(empty)')
  if (!pid) {
    errorMessage.value = '请先上传并解析 PPT'
    mockQuestionBankExpanded.value = true
    return
  }
  isGeneratingMockBatch.value = true
  try {
    try {
      const status = await fetchPptStatus(pid)
      console.log('[Training] ppt status before qa batch', status)
      if (status && status.exists === false) {
        errorMessage.value = '当前 PPT 解析状态丢失，请重新上传'
        mockQuestionBankExpanded.value = true
        return
      }
    } catch (err) {
      console.warn('[Training] ppt status check failed (continuing)', err)
    }
    const qaBatchBody = {
      ppt_id: pid,
      count: 3,
    }
    console.log('[Training] qa batch request body', JSON.stringify(qaBatchBody))
    try {
      const response = await postJson('/qa/generate', qaBatchBody)
      console.log('[Training] qa batch response body', response)
      lastQuestionGenerationContext.value = {
        question_provider_kind: response?.question_provider_kind,
        question_generation_meta: response?.question_generation_meta,
        question_fallback_to_rule: response?.question_fallback_to_rule,
      }
      const list = Array.isArray(response?.questions) ? response.questions : []
      mockQuestionsList.value = list
      selectedMockQuestionIndex.value = -1
      selectedMockQuestion.value = null
      apiResult.value = JSON.stringify(response, null, 2)

      if (list.length > 0) {
        const idx = pickFirstValidMockIndex(list)
        if (idx >= 0) {
          const qText = displayMockQuestionText(list[idx])
          console.log('[Training] default current qa question', qText)
          selectMockQuestionForQa(idx)
          console.log('[Training] qa mode default teacher question ready')
          if (fromEnterQa) {
            qaPhaseAutoQuestionTip.value = '已进入答辩问答阶段，系统已生成老师当前问题。'
          }
          mockQuestionBankExpanded.value = !!trainingFlowDebugMode.value
        } else {
          mockQuestionBankExpanded.value = true
          errorMessage.value =
            '题目列表已返回，但无法解析题干。请展开备用题库检查，或点击「重新生成问题列表」。'
        }
      } else {
        mockQuestionBankExpanded.value = true
        errorMessage.value =
          errorMessage.value ||
          '未生成到可用题目，请展开备用题库后重试，或确认课件已解析。'
      }
    } catch (e) {
      console.error('[Training] qa batch failed (full error)', e)
      lastQuestionGenerationContext.value = null
      apiResult.value = ''
      errorMessage.value = pickApiDetailMessage(
        e,
        '生成问题失败，请先上传并解析 PPT 后重试'
      )
      mockQuestionBankExpanded.value = true
    }
  } finally {
    isGeneratingMockBatch.value = false
  }
}

// 生成答辩问题
const generateQaQuestion = async () => {
  errorMessage.value = ''
  const pid = resolveCurrentPptId()
  if (!pid || !selectedPageIndex.value) {
    errorMessage.value = '请先上传 PPT 并选择页面'
    return
  }

  try {
    qaRoundSource.value = 'manual'
    primaryTeacherQaEvalDone.value = false
    selectedMockQuestionIndex.value = -1
    selectedMockQuestion.value = null
    lastManualQaResult.value = null
    lastAutoQaResult.value = null
    lastFollowupQaResult.value = null
    lastQaResult.value = null
    followupQuestions.value = []
    followupSectionVisible.value = false
    selectedFollowupIndex.value = -1
    selectedFollowupQuestion.value = null
    lastFollowupQuestionsSnapshot.value = null
    lastFollowupGenerationContext.value = null
    lastQuestionGenerationContext.value = null
    selectedFollowupMeta.value = null
    autoFollowupFirstRoundAttempted.value = false
    qaAutoFollowupHint.value = ''
    resetQaAnswerWorkspaceOnly()
    qaTextFallbackExpanded.value = false
    qaAnswerText.value = ''
    const response = await postJson('/qa/generate', {
      ppt_id: pid,
      page_index: selectedPageIndex.value
    })
    lastQuestionGenerationContext.value = {
      question_provider_kind: response?.question_provider_kind,
      question_generation_meta: response?.question_generation_meta,
      question_fallback_to_rule: response?.question_fallback_to_rule,
    }
    currentQaQuestion.value = response.question || ''
    currentQaExpectedKeywords.value = Array.isArray(response.expected_keywords) ? response.expected_keywords : []
    qaEvaluationResult.value = null
  } catch (e) {
    console.error('生成问答失败:', e)
    errorMessage.value = `生成问答失败：${e.message}`
  }
}

const generateFollowupQuestions = async () => {
  if (!lastQaResult.value && !qaEvaluationResult.value) {
    errorMessage.value = '请先完成一次「评估回答」'
    return
  }
  const pid = resolveCurrentPptId()
  if (!pid) {
    errorMessage.value = '请先上传 PPT'
    return
  }
  const qaPayload = lastQaResult.value
    ? JSON.parse(JSON.stringify(lastQaResult.value))
    : { ...qaEvaluationResult.value }
  isGeneratingFollowup.value = true
  errorMessage.value = ''
  try {
    const body = {
      ppt_id: pid,
      current_question: currentQaQuestion.value,
      current_answer: qaAnswerText.value,
      qa_result: qaPayload,
      ppt_match: buildPptMatchForApi(),
      content_breakdown: null,
    }
    console.log('[Training] followup request body', JSON.stringify(body))
    const res = await postJson('/qa/followup', body)
    console.log('[Training] followup response body', res)
    const list = Array.isArray(res?.followup_questions) ? res.followup_questions : []
    followupQuestions.value = list
    followupSectionVisible.value = true
    lastFollowupQuestionsSnapshot.value = list.length ? JSON.parse(JSON.stringify(list)) : null
    lastFollowupGenerationContext.value = {
      followup_provider_kind: res?.followup_provider_kind,
      followup_generation_meta: res?.followup_generation_meta,
      followup_fallback_to_rule: res?.followup_fallback_to_rule,
    }
    console.log('[Training.followup.source] provider_kind=', res?.followup_provider_kind)
    console.log('[Training.followup.source] provider_label=', res?.followup_generation_meta?.provider_label)
    console.log('[Training.followup.source] fallback_to_rule=', res?.followup_fallback_to_rule)
    console.log(
      '[Training.followup.source] resolved display label=',
      resolveFollowupTaxonomyShortLabel(lastFollowupGenerationContext.value)
    )
    selectedFollowupIndex.value = -1
    selectedFollowupQuestion.value = null
    selectedFollowupMeta.value = null
    qaAutoFollowupHint.value = ''
  } catch (e) {
    console.error('[Training] followup failed', e)
    followupSectionVisible.value = false
    errorMessage.value = pickApiDetailMessage(e, '生成追问失败，请稍后重试')
  } finally {
    isGeneratingFollowup.value = false
  }
}

/** 首轮主问题评估成功后：自动请求追问并默认选中第一条 */
const runAutoFollowupAfterFirstEvaluation = async () => {
  console.log('[Training] auto followup trigger after first qa evaluation')
  const plain = lastQaResult.value
  if (!plain || typeof plain !== 'object') return
  const pid = resolveCurrentPptId()
  if (!pid) return
  autoFollowupFirstRoundAttempted.value = true
  const qaPayload = JSON.parse(JSON.stringify(plain))
  const cq = String(plain.question ?? currentQaQuestion.value ?? '').trim()
  const ca = String(plain.answer_text ?? qaAnswerText.value ?? '').trim()
  isGeneratingFollowup.value = true
  errorMessage.value = ''
  try {
    const body = {
      ppt_id: pid,
      current_question: cq,
      current_answer: ca,
      qa_result: qaPayload,
      ppt_match: buildPptMatchForApi(),
      content_breakdown: null,
      client_followup_trigger: 'auto_after_first_eval',
    }
    console.log('[Training] followup request body (auto)', JSON.stringify(body))
    const res = await postJson('/qa/followup', body)
    console.log('[Training] auto followup response', res)
    const list = Array.isArray(res?.followup_questions) ? res.followup_questions : []
    followupQuestions.value = list
    followupSectionVisible.value = true
    lastFollowupQuestionsSnapshot.value = list.length ? JSON.parse(JSON.stringify(list)) : null
    lastFollowupGenerationContext.value = {
      followup_provider_kind: res?.followup_provider_kind,
      followup_generation_meta: res?.followup_generation_meta,
      followup_fallback_to_rule: res?.followup_fallback_to_rule,
    }
    console.log('[Training.followup.source] provider_kind=', res?.followup_provider_kind)
    console.log('[Training.followup.source] provider_label=', res?.followup_generation_meta?.provider_label)
    console.log('[Training.followup.source] fallback_to_rule=', res?.followup_fallback_to_rule)
    console.log(
      '[Training.followup.source] resolved display label=',
      resolveFollowupTaxonomyShortLabel(lastFollowupGenerationContext.value)
    )
    const fidx = pickFirstValidFollowupIndex(list)
    if (fidx >= 0) {
      console.log('[Training] default followup question selected', { index: fidx, item: list[fidx] })
      selectFollowupQuestion(fidx, { skipClearAutoHint: true })
      qaAutoFollowupHint.value = '已根据上一轮回答自动生成老师追问，请继续语音回答。'
      console.log('[Training] current qa source=followup_generated')
    } else {
      qaAutoFollowupHint.value = ''
      selectedFollowupIndex.value = -1
      selectedFollowupQuestion.value = null
      selectedFollowupMeta.value = null
    }
  } catch (e) {
    console.error('[Training] auto followup failed', e)
    errorMessage.value = pickApiDetailMessage(e, '自动追问生成失败，可在调试模式下点击「生成追问」重试')
  } finally {
    isGeneratingFollowup.value = false
  }
}

const selectFollowupQuestion = (idx, opts = {}) => {
  if (!opts.skipClearAutoHint) qaAutoFollowupHint.value = ''
  const item = followupQuestions.value[idx]
  const qText = String(item?.question ?? '').trim()
  if (!qText) return
  selectedFollowupIndex.value = idx
  selectedFollowupQuestion.value =
    item && typeof item === 'object'
      ? {
          question: qText,
          reason: String(item?.reason ?? ''),
          source: String(item?.source ?? ''),
          target_topic: String(item?.target_topic ?? ''),
        }
      : { question: qText, reason: '', source: '', target_topic: '' }
  selectedFollowupMeta.value = {
    reason: String(item?.reason ?? ''),
    target_topic: String(item?.target_topic ?? ''),
    source: String(item?.source ?? ''),
  }
  currentQaQuestion.value = qText
  const tt = selectedFollowupMeta.value.target_topic
  currentQaExpectedKeywords.value = tt ? [tt] : []
  qaAnswerText.value = ''
  qaEvaluationResult.value = null
  lastQaResult.value = null
  lastManualQaResult.value = null
  lastAutoQaResult.value = null
  lastFollowupQaResult.value = null
  qaRoundSource.value = 'followup_generated'
  errorMessage.value = ''
  resetQaAnswerWorkspaceOnly()
  console.log('[Training] selected followup question', idx, qText, selectedFollowupQuestion.value)
  console.log('[Training] current qa source', 'followup_generated')
}

// 评估回答
const evaluateQaAnswer = async (opts = {}) => {
  errorMessage.value = ''
  if (!currentQaQuestion.value) {
    errorMessage.value = '请先生成问题'
    return
  }
  if (!qaAnswerText.value || !String(qaAnswerText.value).trim()) {
    errorMessage.value = '请先完成语音作答，或展开文本兜底输入回答'
    return
  }

  const inputMode = opts.inputMode === 'voice' ? 'voice' : 'text'
  lastQaAnswerInputMode.value = inputMode
  console.log(
    '[Training] qa current source=' + resolveQaAnswerLogSource(),
    'input_mode=' + inputMode
  )
  if (inputMode === 'voice') {
    console.log('[Training] qa evaluate from voice transcript')
  } else {
    console.log('[Training] qa evaluate from text fallback')
  }

  qaAnswerEvaluatePending.value = true
  try {
    const evalBody = {
      question: currentQaQuestion.value,
      expected_keywords: currentQaExpectedKeywords.value,
      answer_text: qaAnswerText.value,
    }
    if (qaRoundSource.value === 'followup_generated') {
      console.log('[Training] followup evaluate request body', JSON.stringify(evalBody))
    } else {
      console.log('[Training] qa evaluate request body', JSON.stringify(evalBody))
    }
    const response = await postJson('/qa/evaluate', evalBody)
    if (qaRoundSource.value === 'followup_generated') {
      console.log('[Training] followup evaluate response body', JSON.stringify(response))
    } else {
      console.log('[Training] qa evaluate response body', response)
    }
    let src = 'manual'
    if (qaRoundSource.value === 'auto_generated') src = 'auto_generated'
    else if (qaRoundSource.value === 'followup_generated') src = 'followup_generated'
    const plain = {
      ...response,
      question: currentQaQuestion.value,
      expected_keywords: Array.isArray(currentQaExpectedKeywords.value)
        ? [...currentQaExpectedKeywords.value]
        : [],
      answer_text: qaAnswerText.value,
      qa_source: src,
      answer_input_mode: lastQaAnswerInputMode.value,
    }
    if (src === 'followup_generated' && selectedFollowupMeta.value) {
      plain.followup_reason = selectedFollowupMeta.value.reason
      plain.followup_target_topic = selectedFollowupMeta.value.target_topic
    }
    if (src === 'followup_generated' && lastFollowupGenerationContext.value) {
      const ctx = lastFollowupGenerationContext.value
      if (ctx.followup_provider_kind != null) plain.followup_provider_kind = ctx.followup_provider_kind
      if (ctx.followup_generation_meta != null) plain.followup_generation_meta = ctx.followup_generation_meta
      if (ctx.followup_fallback_to_rule != null) plain.followup_fallback_to_rule = ctx.followup_fallback_to_rule
    }
    if ((src === 'manual' || src === 'auto_generated') && lastQuestionGenerationContext.value) {
      const qctx = lastQuestionGenerationContext.value
      if (qctx.question_provider_kind != null) plain.question_provider_kind = qctx.question_provider_kind
      if (qctx.question_generation_meta != null) plain.question_generation_meta = qctx.question_generation_meta
      if (qctx.question_fallback_to_rule != null) plain.question_fallback_to_rule = qctx.question_fallback_to_rule
    }
    qaEvaluationResult.value = response
    lastQaResult.value = plain
    if (src === 'manual' || src === 'auto_generated') {
      primaryTeacherQaEvalDone.value = true
    }
    if (src === 'followup_generated') {
      lastFollowupQaResult.value = plain
      lastManualQaResult.value = null
      lastAutoQaResult.value = null
      console.log('[Training] current qa source', plain.qa_source)
    } else if (src === 'auto_generated') {
      lastAutoQaResult.value = plain
      lastManualQaResult.value = null
      lastFollowupQaResult.value = null
    } else {
      lastManualQaResult.value = plain
      lastAutoQaResult.value = null
      lastFollowupQaResult.value = null
    }

    if (
      (src === 'manual' || src === 'auto_generated') &&
      sessionId.value &&
      sessionPhase.value === 'qa' &&
      !autoFollowupFirstRoundAttempted.value
    ) {
      await runAutoFollowupAfterFirstEvaluation()
    }
  } catch (e) {
    console.error('问答评估失败:', e)
    errorMessage.value = `问答评估失败：${e.message}`
  } finally {
    qaAnswerEvaluatePending.value = false
  }
}

const onQaTextFallbackFocus = () => {
  qaAnswerMode.value = 'text'
}

const stopQaVoiceAnswer = async () => {
  if (!isQaAnswerRecording.value && !qaAnswerMediaRecorder.value) return
  console.log('[Training] qa voice record stop')
  console.log('[Training] qa current source=' + resolveQaAnswerLogSource())
  isAnalyzingQaAudio.value = true
  errorMessage.value = ''
  try {
    const { blob, mimeType } = await stopQaAnswerLocalRecording()
    qaAnswerAudioBlob.value = blob
    if (!blob || blob.size === 0) {
      errorMessage.value = '未录制到有效语音，请重试或展开文本兜底输入'
      qaTextFallbackExpanded.value = true
      return
    }
    const normalized = await uploadQaAudioForTranscript(blob, mimeType)
    if (!normalized) {
      errorMessage.value = '语音分析无返回，请重试或使用文本兜底'
      qaTextFallbackExpanded.value = true
      return
    }
    const tr = typeof normalized.transcript === 'string' ? normalized.transcript.trim() : ''
    console.log('[Training] qa voice transcript', tr)
    qaAnswerTranscript.value = tr
    if (normalized.audio_valid === false) {
      errorMessage.value =
        normalized.audio_message || '未识别到有效语音，请重试或使用文本兜底'
      qaTextFallbackExpanded.value = true
      return
    }
    if (!tr) {
      errorMessage.value = '转写为空，请重试或使用文本兜底'
      qaTextFallbackExpanded.value = true
      return
    }
    qaAnswerText.value = tr
    lastQaAnswerInputMode.value = 'voice'
    await evaluateQaAnswer({ inputMode: 'voice' })
  } catch (e) {
    console.error('[stopQaVoiceAnswer]', e)
    errorMessage.value = `语音作答处理失败：${e?.message || e}`
    qaTextFallbackExpanded.value = true
  } finally {
    isAnalyzingQaAudio.value = false
  }
}

const startRecording = async () => {
  if (isQaAnswerRecording.value) {
    errorMessage.value = '请先结束问答语音作答后再开始讲解录音'
    return
  }
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    const msg = '当前浏览器不支持录音功能，请更换浏览器或使用最新版 Chrome / Edge'
    errorMessage.value = msg
    console.warn(msg)
    return
  }
  try {
    mediaStream.value = await navigator.mediaDevices.getUserMedia({ audio: true })
    try {
      const tracks = mediaStream.value.getAudioTracks()
      tracks.forEach((track, idx) => {
        let settings = {}
        try {
          settings = typeof track.getSettings === 'function' ? track.getSettings() : {}
        } catch (e) {
          console.warn('[startRecording] getSettings failed', e)
        }
        console.log('[startRecording] 输入设备 / 音频轨道', idx, {
          label: track.label,
          id: track.id,
          enabled: track.enabled,
          muted: track.muted,
          settings,
        })
      })
    } catch (e) {
      console.warn('[startRecording] 打印设备信息失败', e)
    }
    audioChunks.value = []
    const preferredTypes = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/ogg'
    ]
    let selectedMimeType = ''
    if (window.MediaRecorder && typeof window.MediaRecorder.isTypeSupported === 'function') {
      selectedMimeType = preferredTypes.find((type) => window.MediaRecorder.isTypeSupported(type)) || ''
    }
    mediaRecorder.value = selectedMimeType
      ? new MediaRecorder(mediaStream.value, { mimeType: selectedMimeType })
      : new MediaRecorder(mediaStream.value)
    recordingMimeType.value = mediaRecorder.value.mimeType || selectedMimeType || ''
    console.log('record mimeType:', recordingMimeType.value)
    mediaRecorder.value.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        audioChunks.value.push(event.data)
      }
    }
    mediaRecorder.value.start()
    isRecording.value = true
    console.log('[startRecording] MediaRecorder started, isRecording=true')
  } catch (e) {
    console.error('录音启动失败:', e)
    const name = e && e.name
    let detail = e && e.message ? String(e.message) : '未知错误'
    if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
      detail = '麦克风权限被拒绝，请在浏览器设置中允许本站使用麦克风后重试'
    } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
      detail = '未检测到可用麦克风设备，请连接麦克风后重试'
    }
    errorMessage.value = `浏览器录音初始化失败：${detail}`
  }
}

watch(
  [
    sessionId,
    sessionPhase,
    trainingScoringProfile,
    trainingDeckMode,
    recommendedTrainingFocus,
    trainingFocusSource,
    contentFocusDowngraded,
    qaRoundSource,
    currentQaQuestion,
    primaryTeacherQaEvalDone,
    selectedMockQuestionIndex,
    followupSectionVisible,
    selectedFollowupIndex,
    spokenText,
    selectedPageIndex,
    pptMatchMode,
    lastQaResult,
    qaEvaluationResult,
    followupQuestions,
    lastManualQaResult,
    lastAutoQaResult,
    lastFollowupQaResult,
    mockQuestionsList,
    pptInfo,
  ],
  () => {
    scheduleTrainingRuntimeSnapshot()
  },
  { flush: 'post' }
)

if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    try {
      saveTrainingRuntimeSnapshotNow()
    } catch (_) {}
    console.log('[Training.cleanup] scenario=', 'beforeunload')
    cleanupMediaResources('beforeunload')
  })
}

onBeforeUnmount(() => {
  try {
    clearTimeout(runtimeSnapshotTimer)
  } catch (_) {}
  try {
    window.removeEventListener(APP_PREFERENCES_CHANGED_EVENT, onAppPreferencesExternalChange)
  } catch (_) {}
  try {
    window.removeEventListener(TRAINING_GOALS_CHANGED_EVENT, onTrainingGoalsExternalChange)
  } catch (_) {}
  console.log('[Training.cleanup] scenario=', 'route_leave')
  cleanupMediaResources('route_leave')
})

onMounted(async () => {
  try {
    window.addEventListener(APP_PREFERENCES_CHANGED_EVENT, onAppPreferencesExternalChange)
  } catch (_) {}
  try {
    window.addEventListener(TRAINING_GOALS_CHANGED_EVENT, onTrainingGoalsExternalChange)
  } catch (_) {}

  try {
    const { hydrateAccountSettings } = await import('../utils/accountSettingsSync.js')
    await hydrateAccountSettings()
    preferencesRevision.value++
    trainingGoalsRevision.value++
  } catch (_) {}

  if (activateDemoModeFromRouteQuery(route.query)) {
    refreshTrainingDemoMode()
    const q = stripDemoQueryKeys({ ...route.query })
    if (JSON.stringify(q) !== JSON.stringify(route.query)) {
      router.replace({ path: route.path, query: q })
    }
  } else {
    refreshTrainingDemoMode()
  }
  if (demoModeUi.value.active) {
    trainingFlowDebugMode.value = false
  }
  console.log('[Training.demo_mode] active=', demoModeUi.value.active)
  console.log(
    '[Training.demo_mode] hidden_low_priority_sections=',
    demoModeUi.value.active
      ? ['debug_flow_toggle', 'debug_side_panels_when_off', 'soft_stage_disclaimer', 'soft_recent_valid_block']
      : []
  )

  ;(async () => {
    try {
      trainingPageProviderStatus.value = await getJson('/system/provider-status')
    } catch (_) {
      trainingPageProviderStatus.value = null
    }
  })()

  console.log('[Training.mode] default defenseMaterialMode=', defenseMaterialMode.value)
  sessionId.value = ''
  sessionPhase.value = 'lecture'
  primaryTeacherQaEvalDone.value = false

  console.log('[Training.user_scope] user_id=', getActiveUserId() ?? '(none)')

  let storedSid = ''
  try {
    storedSid = String(readUserScopedItem(localStorage, CURRENT_SESSION_ID_KEY) || '').trim()
  } catch (_) {}

  let resumePayload = null
  if (storedSid) {
    try {
      resumePayload = await getJson(
        `/session/resume_status?session_id=${encodeURIComponent(storedSid)}`
      )
    } catch (e) {
      console.warn('[Training.resume_session] resume_status request failed', e)
      resumePayload = { recoverable: false, reason: 'request_failed' }
      if (storedSid) {
        resumeSessionCheckFailed.value = true
        console.log('[Training.load] recoverable_session_error=', 'request_failed')
      }
    }
  }

  if (resumePayload?.recoverable === true) {
    const snap = readTrainingRuntimeSnapshot()
    const snapMatch = !!(snap && snap.session_id === storedSid && snap.v === 1)
    unfinishedResumePrompt.value = {
      sessionId: storedSid,
      server: resumePayload,
      snapshot: snapMatch ? snap : null,
      hasSnapshot: snapMatch,
    }
    console.log('[Training.resume_session] found_unfinished_session=', true, 'has_snapshot=', snapMatch)
  } else {
    console.log(
      '[Training.resume_session] found_unfinished_session=',
      false,
      resumePayload?.reason || (storedSid ? 'no_active' : 'no_local_id')
    )
    if (storedSid && resumePayload && resumePayload.reason !== 'request_failed') {
      clearTrainingRuntimeSnapshot()
      if (
        resumePayload.reason === 'already_completed' ||
        resumePayload.reason === 'not_found_or_server_restarted' ||
        resumePayload.reason === 'not_owner' ||
        resumePayload.reason === 'session_missing_owner'
      ) {
        console.log('[Training.user_scope] ignored_foreign_state=', resumePayload.reason || 'stale_session')
        try {
          removeUserScopedItem(localStorage, CURRENT_SESSION_ID_KEY, undefined, true)
        } catch (_) {}
      }
    }
  }

  try {
    const s = readUserScopedItem(localStorage, LAST_PPT_ID_STORAGE_KEY)
    if (s?.trim()) {
      cachedPptIdFallback.value = s.trim()
      console.log(
        '[Training] restored ppt_id from localStorage (not marking ready until re-upload)',
        cachedPptIdFallback.value
      )
    }
  } catch (_) {}
  pptInfo.value = null
  pptUploadFailed.value = false
  isUploadingPpt.value = false
  const incomingRes = applyIncomingTrainingFocus()
  console.log('[Training.entry] source=', resolveTrainingEntrySource())
  const usedSessionStorage = incomingRes?.usedSessionStorage === true
  const explicitQ = hasExplicitTrainingRouteQuery()
  let hadDraft = false
  try {
    hadDraft = !!readUserScopedItem(localStorage, TRAINING_PAGE_DRAFT_STORAGE_KEY)
  } catch (_) {}

  let draftRestored = false
  if (explicitQ) {
    console.log('[Training.restore] found_saved_config=', hadDraft)
    console.log('[Training.restore] restored_from=', 'explicit_query')
    console.log('[Training.restore] incoming_focus_priority=', incomingFocusPriority.value)
  } else if (usedSessionStorage) {
    console.log('[Training.restore] found_saved_config=', hadDraft)
    console.log('[Training.restore] restored_from=', 'session_storage_handoff')
    console.log('[Training.restore] incoming_focus_priority=', incomingFocusPriority.value)
  } else if (!unfinishedResumePrompt.value) {
    draftRestored = restoreTrainingPageDraftFromLocal()
  }

  let appliedFrom = 'fallback'
  if (explicitQ || usedSessionStorage) {
    appliedFrom = 'explicit'
  } else if (draftRestored) {
    appliedFrom = 'draft'
  } else if (!unfinishedResumePrompt.value) {
    applyGlobalTrainingDefaultsFromPrefs()
    appliedFrom = 'global_default'
  } else {
    appliedFrom = 'fallback'
  }
  console.log('[Training.preferences] applied_from=', appliedFrom)
  if (appliedFrom === 'global_default') {
    console.log('[Training.settings] applied_global_preferences=', preferencesSnapshotForLog())
  }

  const _scopeRestored = []
  if (unfinishedResumePrompt.value) _scopeRestored.push('resume_prompt')
  if (draftRestored) _scopeRestored.push('draft')
  if (usedSessionStorage) _scopeRestored.push('session_handoff')
  if (appliedFrom === 'global_default') _scopeRestored.push('global_defaults')
  if (explicitQ) _scopeRestored.push('explicit_query')
  console.log('[Training.user_scope] restored_keys=', _scopeRestored.join(',') || '(none)')

  draftPersistenceReady.value = true
  saveTrainingPageDraft()

  fetchValidTrainingOverview()
  runPreflightChecks()
})
</script>

<style scoped>
.training-page {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  padding: 0;
  min-height: 100vh;
  box-sizing: border-box;
  min-width: 0;
  width: 100%;
  max-width: 100%;
}

.training-session-state-banner {
  width: 100%;
  max-width: 800px;
  margin-bottom: 16px;
  padding: 14px 18px;
  background: var(--ui-surface-subtle);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-lg);
  text-align: left;
  box-shadow: var(--ui-shadow-card);
  transition: box-shadow var(--ui-transition);
}

.training-workbench .training-session-state-banner--v1:hover {
  box-shadow: var(--ui-shadow-card-hover);
}

.training-session-state-banner--session_running_lecture,
.training-session-state-banner--session_running_qa {
  background: var(--ui-accent-soft);
  border-color: var(--ui-accent-muted);
}

.training-session-state-banner--session_paused_recoverable {
  background: var(--brand-warning-soft);
  border-color: #fde68a;
}

.training-session-state-banner--session_completing,
.training-session-state-banner--session_completed {
  background: var(--brand-success-soft);
  border-color: #a7f3d0;
}

.training-session-state-banner--session_discarded {
  background: #faf5ff;
  border-color: #e9d5ff;
}

.tss-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 12px;
  margin-bottom: 8px;
}

.tss-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.tss-title {
  font-size: 1rem;
  color: #0f172a;
}

.tss-line {
  margin: 4px 0;
  font-size: 0.88rem;
  line-height: 1.5;
  color: #334155;
}

.tss-sid {
  font-size: 0.82rem;
  padding: 2px 6px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
}

.tss-next {
  margin-top: 6px;
  color: #1e293b;
}

.training-stage-guide {
  width: 100%;
  max-width: 800px;
  margin-bottom: 16px;
  padding: 18px 20px;
  text-align: left;
}

.training-workbench .training-stage-guide:hover {
  box-shadow: var(--ui-shadow-card-hover);
}

.tsg-heading {
  margin: 0 0 8px;
  font-size: 1rem;
  font-weight: 600;
  color: #0f172a;
}

.tsg-disclaimer {
  margin: 0 0 12px;
  font-size: 0.8rem;
  line-height: 1.45;
}

.tsg-track {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 10px;
  margin: 0 0 14px;
  padding: 0;
  list-style: none;
}

.tsg-track-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  padding: 4px 10px;
  font-size: 0.8rem;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #94a3b8;
}

.tsg-track-item--done {
  color: #64748b;
  border-color: #cbd5e1;
  background: #f8fafc;
}

.tsg-track-item--active {
  color: #0f172a;
  font-weight: 600;
  border-color: #93c5fd;
  background: #eff6ff;
  box-shadow: 0 0 0 1px #bfdbfe inset;
}

.tsg-track-item--upcoming {
  opacity: 0.72;
}

.tsg-track-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.25rem;
  height: 1.25rem;
  font-size: 0.72rem;
  font-weight: 700;
  border-radius: 50%;
  background: #e2e8f0;
  color: #475569;
}

.tsg-track-item--active .tsg-track-num {
  background: #3b82f6;
  color: #fff;
}

.tsg-track-item--done .tsg-track-num {
  background: #cbd5e1;
  color: #334155;
}

.tsg-current-name,
.tsg-goal,
.tsg-done,
.tsg-next {
  margin: 4px 0;
  font-size: 0.88rem;
  line-height: 1.5;
  color: #334155;
}

.tsg-next {
  margin-top: 8px;
  color: #1e293b;
}

.session-discarded-banner {
  width: 100%;
  max-width: 800px;
  margin: -8px 0 16px;
  padding: 8px 12px;
  font-size: 0.88rem;
  color: #6b21a8;
  background: #faf5ff;
  border: 1px solid #e9d5ff;
  border-radius: 6px;
  text-align: left;
}

.recent-valid-training-reminder {
  width: 100%;
  max-width: 800px;
  margin-bottom: 18px;
  padding: 16px 18px;
  text-align: left;
}

.recent-valid-training-reminder__title {
  margin: 0 0 10px;
  font-size: 1.02rem;
  font-weight: 700;
  color: var(--ui-text-primary);
  letter-spacing: -0.015em;
}

.recent-valid-training-reminder__note {
  margin: 0 0 10px;
  font-size: 0.85rem;
  line-height: 1.5;
}

.recent-valid-training-reminder__list {
  margin: 0;
  padding-left: 1.15rem;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--ui-text-secondary);
}

.recent-valid-training-reminder__list li {
  margin-bottom: 6px;
}

.rvr-k {
  color: var(--ui-text-muted);
}

.recent-valid-training-reminder__actions {
  margin-top: 12px;
}

.rvr-actions-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.recent-valid-training-reminder__empty {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.5;
}

.unfinished-session-resume {
  width: 100%;
  max-width: 800px;
  margin-bottom: 18px;
  padding: 16px 18px;
  text-align: left;
  background: var(--brand-warning-soft);
  border-color: #fde68a;
}

.unfinished-session-resume__title {
  margin: 0 0 10px;
  font-size: 1.02rem;
  font-weight: 700;
  color: #9a3412;
  letter-spacing: -0.015em;
}

.unfinished-session-resume__list {
  margin: 0 0 10px;
  padding-left: 1.15rem;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--ui-text-secondary);
}

.usr-k {
  color: var(--ui-text-muted);
}

.usr-sid {
  font-size: 0.85rem;
  background: #fff;
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid #e7e5e4;
}

.usr-note {
  list-style: disc;
}

.unfinished-session-resume__media-hint {
  margin: 0 0 12px;
  font-size: 0.85rem;
  line-height: 1.5;
}

.unfinished-session-resume__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.resume-media-hint {
  width: 100%;
  max-width: 800px;
  margin-bottom: 14px;
  padding: 10px 14px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  font-size: 0.88rem;
  color: #166534;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.resume-media-hint p {
  margin: 0;
  flex: 1;
  min-width: 200px;
  line-height: 1.5;
}

.training-focus-banner {
  width: 100%;
  max-width: 800px;
  margin-bottom: 14px;
  padding: 12px 16px;
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  border-radius: 8px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.training-focus-line {
  margin: 0;
  font-size: 0.92rem;
  color: #303133;
  line-height: 1.5;
}

.training-focus-source-note {
  font-weight: normal;
  font-size: 0.85rem;
  color: #909399;
}

.training-focus-clear {
  flex-shrink: 0;
}

.training-focus-badge {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 8px;
  font-size: 0.75rem;
  font-weight: 600;
  color: #b45309;
  background: #fef3c7;
  border-radius: 4px;
  vertical-align: middle;
}

.training-goal-hint {
  width: 100%;
  max-width: 800px;
  margin-bottom: 14px;
  padding: 12px 16px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  font-size: 0.9rem;
  line-height: 1.55;
  color: #14532d;
}

.training-goal-hint__line {
  margin: 0 0 6px;
}

.training-goal-hint__line:last-child {
  margin-bottom: 0;
}

.training-goal-hint--session {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1e3a5f;
}

.training-rhythm-hint {
  background: #faf5ff;
  border-color: #e9d5ff;
  color: #4c1d95;
}

.specialty-downgrade-hint {
  width: 100%;
  max-width: 800px;
  margin-bottom: 14px;
  padding: 12px 16px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  font-size: 0.9rem;
  line-height: 1.55;
  color: #78350f;
}

.specialty-downgrade-hint p {
  margin: 0;
}

.specialty-guidance-panel {
  width: 100%;
  max-width: 800px;
  margin-bottom: 18px;
  padding: 18px 20px;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  border-left: 4px solid #3b82f6;
}

.specialty-guidance-panel--posture {
  border-left-color: #22c55e;
}

.specialty-guidance-panel--qa {
  border-left-color: #a855f7;
}

.specialty-guidance-panel--content {
  border-left-color: #f59e0b;
}

.specialty-guidance-title {
  margin: 0 0 12px;
  font-size: 1.15rem;
  color: #0f172a;
}

.specialty-label {
  display: block;
  font-size: 0.8rem;
  font-weight: 700;
  color: #64748b;
  text-transform: none;
  letter-spacing: 0.02em;
  margin-bottom: 6px;
}

.specialty-guidance-goal {
  margin: 0 0 16px;
  font-size: 0.95rem;
  line-height: 1.55;
  color: #334155;
}

.specialty-guidance-tips {
  margin: 0 0 14px;
  padding-left: 1.2rem;
  color: #475569;
  font-size: 0.92rem;
  line-height: 1.55;
}

.specialty-guidance-tips li {
  margin-bottom: 6px;
}

.specialty-guidance-start {
  margin: 0;
  padding-top: 10px;
  border-top: 1px dashed #cbd5e1;
  font-size: 0.88rem;
  line-height: 1.5;
  color: #64748b;
}

.normal-training-reminder {
  width: 100%;
  max-width: 800px;
  margin: 0 0 16px;
  padding: 10px 14px;
  font-size: 0.88rem;
  line-height: 1.5;
  color: #64748b;
  background: #f8fafc;
  border-radius: 8px;
}

.training-prep-connector {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.training-workbench-desk {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.training-prep-connector--prep {
  display: flex;
  flex-direction: column;
  gap: 0;
  margin-bottom: var(--ui-stack-gap-sm, 16px);
  border-radius: var(--ui-radius-lg);
  border: 1px solid var(--ui-card-border);
  background: var(--ui-surface);
  box-shadow: var(--ui-shadow-card);
  box-sizing: border-box;
  overflow: hidden;
  width: 100%;
}

.training-page--prep-layout .training-primary-status-card {
  max-width: 100%;
  width: 100%;
  margin: 0;
  border-radius: 0;
  border: none;
  border-bottom: 1px solid var(--ui-border);
  box-shadow: none;
  background: linear-gradient(165deg, #f8fafc 0%, #fff 58%);
  box-sizing: border-box;
}

.training-prep-connector--prep .ui-l-desk-2--prep-cols.training-workbench-desk--prep {
  margin: 0;
  padding: var(--ui-card-pad-y, 22px) var(--ui-card-pad-x, 24px);
  border: none;
  border-radius: 0;
  background: var(--ui-surface-subtle);
  box-sizing: border-box;
  align-items: start;
  width: 100%;
  max-width: 100%;
  gap: 20px 24px;
}

.training-prep-connector--prep .training-desk__left,
.training-prep-connector--prep .training-desk__right {
  min-width: 0;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.training-prep-connector--prep .training-desk__left {
  padding-right: 0;
  margin-right: 0;
  border-right: none;
}

@media (max-width: 1279px) {
  .training-prep-connector--prep .training-desk__left {
    padding-bottom: var(--ui-stack-gap-sm, 16px);
    margin-bottom: var(--ui-stack-gap-sm, 16px);
    border-bottom: 1px solid var(--ui-border);
  }
}

.training-page--prep-layout .training-flow-shell {
  border: 1px solid var(--ui-card-border);
  border-radius: var(--ui-radius-lg);
  background: var(--ui-surface);
  padding: var(--ui-card-pad-y, 22px) var(--ui-card-pad-x, 24px);
  display: flex;
  flex-direction: column;
  gap: 0;
  min-width: 0;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  overflow: hidden;
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04);
}

.training-page--prep-layout .training-flow-shell > * {
  min-width: 0;
  max-width: 100%;
}

.training-page--prep-layout .training-flow-shell .training-mode-panel--nested {
  padding-bottom: var(--ui-stack-gap-sm, 16px);
  margin-bottom: var(--ui-stack-gap-sm, 16px);
  border-bottom: 1px dashed var(--ui-border);
}

.training-page--prep-layout .training-flow-shell .ppt-match-section,
.training-page--prep-layout .training-flow-shell .ppt-match-section--without-deck {
  margin-top: 0;
  padding-top: var(--ui-stack-gap-sm, 16px);
  border-top: none;
}

.training-page--prep-layout .training-flow-shell .mock-qa-generate-section {
  margin-top: 0;
  padding-top: var(--ui-stack-gap-sm, 16px);
  border-top: 1px dashed var(--ui-border);
}

.training-page--prep-layout .training-config-panel {
  padding: 0;
  background: transparent;
  border: none;
  box-shadow: none;
  min-width: 0;
  max-width: 100%;
}

.training-config-panel {
  padding: var(--ui-card-pad-y, 20px) var(--ui-card-pad-x, 22px);
  display: flex;
  flex-direction: column;
  gap: var(--ui-stack-gap-tight, 14px);
}

.training-mode-panel--nested {
  margin-bottom: 0;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 0;
}

.training-mode-panel--nested .mode-section-title {
  margin-top: 0;
}

.training-config-panel .ppt-match-section,
.training-config-panel .ppt-match-section--without-deck {
  margin-top: 4px;
  padding-top: var(--ui-stack-gap-tight, 14px);
  border-top: 1px dashed var(--ui-border);
}

.training-config-panel .ppt-match-section h3,
.training-config-panel .ppt-match-section--without-deck h3 {
  margin: 0 0 10px;
  font-size: var(--ui-typo-section, 22px);
  font-weight: 800;
  color: var(--ui-text-primary);
}

.training-config-panel .ppt-upload .el-button--primary {
  min-height: 44px;
  font-size: var(--font-md, 18px);
}

.training-config-panel .ppt-upload__submit {
  min-height: 44px;
  font-size: var(--font-md, 18px);
}

.training-config-panel .el-upload__tip {
  font-size: var(--font-sm, 15px);
  color: var(--ui-text-secondary);
  line-height: 1.55;
}

.training-page--prep-layout .training-config-panel :deep(.el-upload),
.training-page--prep-layout .training-config-panel :deep(.upload-demo) {
  max-width: 100%;
}

.training-page--prep-layout .ppt-upload {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 12px;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.training-ops-panel {
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--ui-stack-gap-sm, 16px);
  background: transparent;
  border: none;
  box-shadow: none;
}

.training-page--prep-layout .training-ops-panel {
  min-height: 0;
}

.training-page--prep-layout .training-ops-stack {
  border: 1px solid var(--ui-card-border);
  border-radius: var(--ui-radius-lg);
  background: var(--ui-surface);
  padding: var(--ui-card-pad-y, 22px) var(--ui-card-pad-x, 24px);
  display: flex;
  flex-direction: column;
  gap: var(--ui-stack-gap-sm, 16px);
  min-width: 0;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  overflow: hidden;
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04);
}

.training-page--prep-layout .training-ops-stack > * {
  min-width: 0;
  max-width: 100%;
}

.training-ops-next-hint {
  margin: 0;
  padding: 12px 14px;
  border-radius: var(--ui-radius-md, 10px);
  background: var(--ui-accent-soft);
  border: 1px solid var(--ui-accent-muted);
  font-size: var(--font-md, 17px);
  font-weight: 600;
  line-height: 1.55;
  color: var(--ui-text-primary);
  text-align: left;
  box-sizing: border-box;
  width: 100%;
}

.training-controls-dock--prep-nested {
  margin-top: 0;
  border: 1px solid var(--ui-accent-muted);
  border-radius: var(--ui-radius-md);
  background: linear-gradient(165deg, var(--ui-accent-soft) 0%, var(--ui-surface) 52%);
  box-shadow: none;
  flex-shrink: 0;
}

.training-page--prep-layout .training-ops-stack .training-controls-dock--prep-nested {
  margin-bottom: 0;
}

.training-prep-low--sink {
  margin-top: var(--ui-stack-gap-sm, 16px);
  opacity: 0.96;
}

.training-prep-low--sink .preflight-capability-hint {
  max-width: none;
  margin: 0 0 10px;
  font-size: var(--font-base, 17px);
}

.training-page--prep-layout .training-page-error {
  max-width: none;
}

.training-page--prep-layout .preflight-panel {
  max-width: none;
  margin: 0;
  background: var(--ui-surface-subtle);
  border-radius: var(--ui-radius-md);
  border: 1px solid var(--ui-border);
  padding: var(--ui-card-pad-sm-y, 16px) var(--ui-card-pad-sm-x, 18px);
  box-sizing: border-box;
}

.training-page--prep-layout .training-ops-stack .preflight-panel {
  box-shadow: none;
}

.training-page--prep-layout .preflight-title {
  font-size: 26px;
  font-weight: 800;
  line-height: 1.25;
}

.training-page--prep-layout .preflight-intro {
  font-size: var(--font-md, 17px);
  color: var(--ui-text-secondary);
}

.training-page--prep-layout .preflight-row {
  font-size: var(--font-md, 17px);
  padding: 15px 0;
}

.training-page--prep-layout .preflight-badge {
  font-size: var(--font-xs, 14px);
  min-width: 76px;
  flex-shrink: 0;
}

.training-page--prep-layout .preflight-msg {
  font-size: var(--font-sm, 15px);
}

.training-page--prep-layout .mode-radios :deep(.el-radio-button__inner),
.training-page--prep-layout .mode-radios--deck :deep(.el-radio-button__inner) {
  min-height: 38px;
  padding: 0 16px;
  font-size: 15px;
  line-height: 36px;
}

.training-page--prep-layout .mode-section-title {
  font-size: var(--ui-typo-section, 24px);
  font-weight: 800;
  color: var(--ui-text-primary);
}

.training-page--prep-layout .mode-hint,
.training-page--prep-layout .mode-deck-explainer {
  font-size: var(--font-md, 17px);
  color: var(--ui-text-secondary);
  line-height: 1.6;
}

.training-page--prep-layout .mode-selected,
.training-page--prep-layout .mode-selected--subtle {
  font-size: var(--font-md, 17px);
}

.training-page--prep-layout .training-controls-dock--emphasis.training-controls-dock--prep-nested {
  margin-top: 0;
}

.training-page--prep-layout .training-page-title.ui-page-title {
  font-size: clamp(1.9rem, 2.3vw, 2.4rem);
  font-weight: 800;
}

.training-page--prep-layout .training-page-head__sub {
  font-size: var(--font-md, 18px);
  line-height: 1.65;
}

.training-page--prep-layout .normal-training-reminder,
.training-page--prep-layout .training-first-hint,
.training-page--prep-layout .training-resume-fail-alert,
.training-page--prep-layout .preflight-capability-hint {
  max-width: 100%;
  box-sizing: border-box;
}

.training-page--prep-layout .training-primary-start-btn {
  min-width: 11em;
  font-size: var(--font-lg, 21px);
  min-height: 50px;
  padding: 12px 24px;
}

.training-page--prep-layout .training-controls-dock .el-button.is-plain--danger,
.training-page--prep-layout .training-controls-dock .el-button--danger.is-plain {
  opacity: 0.88;
}

.training-desk__left,
.training-desk__right {
  min-width: 0;
}

.training-aux-below {
  width: 100%;
  margin-top: 4px;
}

/* —— 训练中 V2：主区层级、侧栏、全宽问答 —— */
.training-session-hero--v2 {
  margin-bottom: 10px;
  padding: 16px 18px 14px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  border-left: 5px solid #0ea5e9;
  background: linear-gradient(135deg, #f8fafc 0%, #fff 55%);
}

.training-in-session--phase-qa .training-session-hero--v2 {
  border-left-color: #7c3aed;
}

.training-session-hero__eyebrow {
  margin: 0 0 6px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #64748b;
}

.training-session-hero__title {
  margin: 0 0 8px;
  font-size: 1.35rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.25;
  color: #0f172a;
}

.training-session-hero__task {
  margin: 0;
  font-size: 1.02rem;
  font-weight: 600;
  line-height: 1.45;
  color: #334155;
}

.training-session-brief {
  margin-bottom: 10px;
}

.session-brief__line {
  margin: 0 0 4px;
  font-size: 0.92rem;
}

.training-session-brief--rec {
  color: #b45309;
  font-weight: 600;
}

.training-session-stage-video {
  margin-bottom: 12px;
}

.training-session-mission {
  margin-bottom: 12px;
  padding: 14px 16px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #fff;
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04);
}

.session-mission-eyebrow {
  margin: 0 0 8px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #94a3b8;
}

.session-mission__actions {
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.training-phase-hint-details {
  margin-top: 10px;
  font-size: 0.88rem;
}

.training-in-session-aux {
  opacity: 0.98;
}

.training-rail-card--head {
  margin-bottom: 10px;
}

.training-rail__title {
  margin: 0 0 6px;
  font-size: 1.02rem;
  font-weight: 800;
  color: #0f172a;
}

.training-rail__line {
  margin: 0;
  font-size: 0.82rem;
  line-height: 1.45;
}

.training-rail__strong {
  color: #1e293b;
}

.training-rail-question {
  margin-bottom: 12px;
  padding: 10px 12px;
  max-height: 10rem;
  overflow: auto;
}

.training-rail-question__k {
  margin: 0 0 4px;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #7c3aed;
}

.training-rail-question__body {
  margin: 0;
  font-size: 0.86rem;
  line-height: 1.5;
  color: #1e293b;
}

.training-controls-dock--rail {
  margin-top: 0;
  margin-bottom: 0;
}

.training-rail-foot {
  margin: 10px 0 0;
  font-size: 0.75rem;
  line-height: 1.4;
}

.qa-section.training-qa--session-run {
  margin-top: 0;
}

.qa-section.training-qa--pre-session {
  margin-top: 4px;
}

.training-mode-panel {
  width: 100%;
  max-width: 800px;
  margin-bottom: 20px;
  padding: 16px 18px;
  background: #f5f7fa;
  border-radius: var(--ui-radius-md);
  border: 1px solid var(--ui-card-border, #dfe7f2);
}

.training-page--prep-layout .training-config-panel .training-mode-panel {
  max-width: none;
}

.mode-section-title {
  margin: 0 0 8px;
  font-size: var(--font-lg, 20px);
  color: #303133;
}

.mode-hint {
  margin: 0 0 12px;
  font-size: var(--font-md, 17px);
  color: var(--ui-text-secondary);
}

.mode-draft-hint {
  margin: -4px 0 12px;
  font-size: 0.82rem;
  line-height: 1.5;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 10px;
}

.mode-draft-hint__sub {
  color: #909399;
}

.mode-radios {
  margin-bottom: 10px;
}

.mode-selected {
  margin: 0;
  font-size: 0.95rem;
  color: #606266;
}

.mode-hint--spaced {
  margin-top: 16px;
}

.mode-deck-explainer {
  margin: 0 0 10px;
  font-size: 0.86rem;
  color: #909399;
  line-height: 1.5;
}

.mode-radios--deck {
  margin-bottom: 6px;
}

.mode-selected--subtle {
  margin-top: 4px;
  font-size: 0.88rem;
  color: #909399;
}

.preflight-capability-hint {
  width: 100%;
  max-width: 800px;
  margin: 0 auto 14px;
  padding: 10px 14px;
  font-size: 0.88rem;
  color: #606266;
  line-height: 1.5;
  background: #f4f4f5;
  border-radius: 6px;
  border: 1px solid #e9e9eb;
  box-sizing: border-box;
}

.training-first-hint {
  width: 100%;
  max-width: 800px;
  margin-bottom: 14px;
  text-align: left;
}

.training-first-hint-list {
  margin: 0;
  padding-left: 1.15rem;
  font-size: 0.88rem;
  line-height: 1.55;
  color: #334155;
}

.training-first-hint-list li {
  margin-bottom: 6px;
}

.training-first-hint-foot {
  margin: 8px 0 0;
  font-size: 0.8rem;
}

.training-resume-fail-alert {
  width: 100%;
  max-width: 800px;
  margin-bottom: 14px;
  text-align: left;
}

.training-resume-fail-alert__body {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.55;
}

.preflight-loading-hint {
  margin: 0 0 10px;
  font-size: 0.86rem;
}

.preflight-panel {
  width: 100%;
  max-width: 800px;
  margin: 0 auto 20px;
  padding: 18px 20px;
  background: #fafafa;
  border: 1px solid var(--ui-card-border, #dfe7f2);
  border-radius: var(--ui-radius-lg, 14px);
  box-sizing: border-box;
}

.preflight-title {
  margin: 0 0 8px;
  font-size: var(--ui-typo-section, 24px);
  color: #303133;
}

.preflight-intro {
  margin: 0 0 12px;
  font-size: var(--font-md, 17px);
  color: var(--ui-text-secondary);
  line-height: 1.55;
}

.preflight-warn-banner {
  margin: 0 0 12px;
  padding: 10px 12px;
  background: #fdf6ec;
  border: 1px solid #faecd8;
  border-radius: 6px;
  font-size: 0.88rem;
  color: #b88230;
  line-height: 1.5;
}

.preflight-list {
  list-style: none;
  margin: 0 0 12px;
  padding: 0;
}

.preflight-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 0;
  border-bottom: 1px solid var(--ui-card-border, #dfe7f2);
  font-size: var(--font-md, 17px);
}

.preflight-row:last-child {
  border-bottom: none;
}

.preflight-badge {
  flex-shrink: 0;
  min-width: 72px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: var(--font-xs, 14px);
  font-weight: 600;
  text-align: center;
}

.preflight-row--pass .preflight-badge {
  background: #e1f3d8;
  color: #529b2e;
}

.preflight-row--warn .preflight-badge {
  background: #faecd8;
  color: #b88230;
}

.preflight-row--block .preflight-badge {
  background: #fde2e2;
  color: #c45656;
}

.preflight-row-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.preflight-label {
  font-weight: 600;
  color: #303133;
  font-size: var(--font-md, 17px);
}

.preflight-msg {
  color: #606266;
  line-height: 1.5;
  font-size: var(--font-sm, 15px);
}

.preflight-actions {
  margin-top: 4px;
}

.preflight-debug {
  margin-top: 12px;
  font-size: 0.8rem;
  color: #909399;
}

.preflight-debug-pre {
  margin: 8px 0 0;
  padding: 10px;
  background: #1e1e1e;
  color: #d4d4d4;
  border-radius: 6px;
  overflow: auto;
  max-height: 240px;
  font-size: 0.72rem;
}

.session-phase-banner {
  width: 100%;
  max-width: 800px;
  margin: 0 auto 16px;
  padding: 14px 16px;
  background: #f0f9eb;
  border: 1px solid #c2e7b0;
  border-radius: 8px;
}

.session-phase-line {
  margin: 0 0 8px;
  font-size: 0.95rem;
  color: #303133;
}

.phase-hint {
  margin: 0 0 12px;
  font-size: 0.86rem;
  color: #606266;
  line-height: 1.5;
}

.session-phase-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.debug-flow-checkbox {
  margin-left: 4px;
}

.mock-qa-phase-tip {
  margin: 0 0 10px;
  font-size: 0.86rem;
  color: #409eff;
  line-height: 1.45;
}

.qa-phase-auto-tip {
  margin: 0 0 12px;
  padding: 10px 12px;
  font-size: 0.9rem;
  color: #303133;
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  border-radius: 8px;
  line-height: 1.5;
}

.mock-bank-toggle-line {
  margin: 10px 0 6px;
  font-size: 0.86rem;
}

.mock-bank-toggle-hint {
  margin-left: 8px;
  color: #909399;
  font-size: 0.82rem;
}

.error-message {
  width: 100%;
  max-width: 800px;
  margin: 20px 0;
  padding: 15px;
  background: #fef0f0;
  color: #f56c6c;
  border: 1px solid #fbc4c4;
  border-radius: 8px;
  text-align: center;
}

.training-page-error {
  width: 100%;
  max-width: 800px;
  margin: 24px 0 20px;
  padding: 4px;
  border-radius: 14px;
  text-align: left;
}

.training-page-error__body {
  margin: 0 0 10px;
  font-size: 15px;
  line-height: 1.65;
  word-break: break-word;
}

.training-page-error__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.training-page-error :deep(.el-alert) {
  border-radius: 12px;
}

.training-page-error :deep(.el-alert__content) {
  padding-top: 6px;
}

.training-page-error :deep(.el-alert__title) {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.35;
}

.training-page-error__actions :deep(.el-button) {
  font-size: 15px;
  min-height: 36px;
}

.status-message {
  width: 100%;
  max-width: 800px;
  margin: 20px 0;
  padding: 15px;
  border-radius: 8px;
  text-align: center;
}

.status-message.info {
  background: #f0f9ff;
  color: #409eff;
  border: 1px solid #d9ecff;
}

.status-message.success {
  background: #f0f9ff;
  color: #67c23a;
  border: 1px solid #e1f5d9;
}

.api-result {
  width: 100%;
  max-width: 800px;
  margin: 20px 0;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
  overflow: auto;
  max-height: 300px;
}

.api-result pre {
  margin: 0;
  font-family: monospace;
  white-space: pre-wrap;
}

.controls {
  margin-top: 20px;
}

.el-button {
  margin: 0 10px;
  font-size: 1.1em;
  padding: 10px 20px;
}

.session-info {
  margin: 20px 0;
  padding: 10px 15px;
  background: #f5f7fa;
  border-radius: 8px;
}

.recording-status {
  margin: 8px 0 0;
  color: #e6a23c;
  font-weight: 600;
}

.audio-analysis-box {
  width: 100%;
  max-width: 800px;
  margin: 20px 0;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
}

.video-preview-box {
  width: 100%;
  max-width: 800px;
  margin: 20px 0;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
}

.camera-preview {
  width: 100%;
  max-height: 320px;
  border-radius: 8px;
  background: #000;
}

.video-tip {
  margin-top: 8px;
  color: #606266;
}

.audio-invalid-hint {
  margin: 10px 0;
  padding: 10px 12px;
  background: #fdf6ec;
  color: #e6a23c;
  border: 1px solid #faecd8;
  border-radius: 6px;
  font-weight: 600;
}

.metrics-form {
  width: 100%;
  max-width: 800px;
  margin: 30px 0;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.form-row {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  margin: 10px 0;
}

.form-row > * {
  flex: 1;
  min-width: 150px;
}

/* PPT 匹配测试区 */
.ppt-match-section {
  width: 100%;
  max-width: 800px;
  margin: 30px 0;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.ppt-match-section--without-deck {
  margin: 24px 0;
  padding: 18px 20px;
  background: #fafafa;
  border: 1px dashed #dcdfe6;
  border-radius: 8px;
}

.ppt-match-section--without-deck h3 {
  margin-top: 0;
  margin-bottom: 12px;
  font-size: 1rem;
  color: #606266;
}

.without-deck-lead {
  margin: 0 0 8px;
  font-size: 0.92rem;
  color: #606266;
  line-height: 1.55;
}

.without-deck-sub {
  margin: 0;
  font-size: 0.82rem;
  color: #909399;
  line-height: 1.5;
}

.ppt-upload {
  margin: 20px 0 24px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px 12px;
}

.ppt-upload__submit {
  margin-left: 10px;
  font-size: 15px;
}

.ppt-info {
  margin: 20px 0;
  padding: 15px;
  background: white;
  border-radius: 8px;
}

.ppt-id-only-hint {
  margin: 10px 0 0;
  font-size: 14px;
  color: #909399;
  line-height: 1.5;
}

.ppt-upload :deep(.el-upload__tip) {
  font-size: 14px;
}

.match-test {
  margin: 20px 0;
}

.match-result {
  margin: 20px 0;
  padding: 15px;
  background: white;
  border-radius: 8px;
}

.result-item {
  margin: 10px 0;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.result-item:last-child {
  border-bottom: none;
}

/* 匹配成功提示 */
.match-success {
  margin-top: 15px;
  padding: 10px;
  background: #f0f9ff;
  color: #409eff;
  border: 1px solid #d9ecff;
  border-radius: 4px;
  text-align: center;
}

/* 调试信息 */
.debug-info {
  margin-top: 20px;
  padding: 15px;
  background: #f9f0ff;
  border: 1px solid #f0d9ff;
  border-radius: 8px;
}

.debug-item {
  margin: 5px 0;
  padding: 5px 0;
  border-bottom: 1px solid #f0d9ff;
}

.debug-item:last-child {
  border-bottom: none;
}

.qa-section {
  width: 100%;
  max-width: 800px;
  margin: 30px 0;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.qa-current-source {
  margin: 0 0 10px;
  padding: 8px 10px;
  background: #fff;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
  font-size: 0.92rem;
  color: #606266;
}

.qa-tip {
  margin: 10px 0;
  padding: 10px;
  background: #f0f9ff;
  color: #409eff;
  border: 1px solid #d9ecff;
  border-radius: 4px;
  font-size: 0.9em;
  text-align: center;
}

.qa-actions {
  margin: 12px 0;
}

.qa-question, .qa-result {
  margin: 12px 0;
  padding: 12px;
  background: white;
  border-radius: 6px;
}

.qa-answer {
  margin: 12px 0;
}

.qa-voice-answer {
  margin: 12px 0;
  padding: 14px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.qa-voice-title {
  margin: 0 0 10px;
  font-size: 0.95rem;
  font-weight: 600;
  color: #303133;
}

.qa-voice-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 8px;
}

.qa-recording-hint {
  margin: 8px 0 0;
  font-size: 0.88rem;
  color: #e6a23c;
}

.qa-transcript-preview {
  margin: 12px 0 0;
  font-size: 0.86rem;
  color: #606266;
  line-height: 1.5;
}

.qa-transcript-preview .muted-label {
  color: #909399;
  margin-right: 6px;
}

.qa-text-fallback {
  margin: 12px 0;
}

.qa-text-fallback-toggle {
  padding-left: 0 !important;
}

.qa-text-fallback-body {
  margin-top: 10px;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px dashed #dcdfe6;
}

.qa-followup-actions {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.qa-followup-hint {
  font-size: 0.86rem;
  color: #909399;
}

.qa-followup-list {
  margin-top: 16px;
  padding: 12px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.fu-empty-hint {
  margin: 0;
  padding: 10px 12px;
  background: #f4f4f5;
  color: #606266;
  border-radius: 6px;
  font-size: 0.9rem;
}

.fu-main-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.fu-q {
  flex: 1;
  min-width: 0;
  line-height: 1.55;
  color: #303133;
  font-size: 0.95rem;
}

.qa-followup-list h4 {
  margin: 0 0 10px;
  font-size: 0.95rem;
}

.fu-session-source {
  margin: 0 0 10px;
  font-size: 0.85rem;
  color: #909399;
}

.qa-followup-list ol {
  margin: 0;
  padding-left: 1.2rem;
}

.qa-followup-row {
  margin: 10px 0;
  padding: 8px;
  border-radius: 6px;
  line-height: 1.5;
}

.qa-followup-row--picked {
  background: #fdf6ec;
  outline: 1px solid #f5dab1;
}

.fu-direction {
  margin-top: 6px;
  font-size: 0.82rem;
  color: #909399;
  line-height: 1.4;
}

.fu-reason {
  margin: 4px 0 0;
  font-size: 0.8rem;
  color: #a8abb2;
  line-height: 1.45;
}

.ppt-match-mode {
  margin: 12px 0;
}

.match-subtitle {
  margin: 14px 0 8px;
  font-size: 0.95rem;
}

.auto-guess-hint {
  margin: 8px 0 0;
  font-size: 0.88rem;
  color: #606266;
}

.auto-guess-result .top-candidates ul {
  margin: 8px 0 0;
  padding-left: 1.2rem;
}

.auto-guess-low-match {
  margin-bottom: 12px;
  padding: 10px 12px;
  background: #fdf6ec;
  color: #b88230;
  border: 1px solid #faecd8;
  border-radius: 6px;
  font-size: 0.92rem;
}

.tag-hit {
  display: inline-block;
  margin-left: 6px;
  padding: 0 6px;
  font-size: 0.75rem;
  color: #409eff;
  background: #ecf5ff;
  border-radius: 4px;
}

.mock-qa-generate-section {
  width: 100%;
  max-width: 800px;
  margin: 30px 0;
  padding: 20px;
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
  border-radius: 8px;
}

.mock-qa-tip {
  margin: 8px 0 14px;
  font-size: 0.88rem;
  color: #606266;
}

.mock-qa-list {
  margin-top: 16px;
  padding: 12px;
  background: #fff;
  border-radius: 6px;
}

.mock-qa-list ol {
  margin: 8px 0 0;
  padding-left: 1.2rem;
}

.mq-source {
  color: #67c23a;
  font-weight: 600;
  margin-right: 6px;
}

.mock-select-hint {
  font-size: 0.86rem;
  color: #606266;
  margin: 8px 0 10px;
}

.mock-q-picked-banner {
  margin: 10px 0 12px;
  padding: 10px 12px;
  background: #ecf5ff;
  border: 1px solid #b3d8ff;
  border-radius: 6px;
  color: #409eff;
  font-weight: 600;
  font-size: 0.92rem;
}

.qa-auto-followup-banner {
  margin: 8px 0 10px;
  padding: 10px 12px;
  background: #f0f9eb;
  border: 1px solid #c2e7b0;
  border-radius: 6px;
  color: #67c23a;
  font-weight: 600;
  font-size: 0.92rem;
}

.qa-followup-provider-debug {
  margin: 0 0 8px;
  font-size: 0.88rem;
  color: #606266;
  line-height: 1.5;
}

.fu-picked-banner {
  margin: 8px 0 10px;
  padding: 10px 12px;
  background: #fdf6ec;
  border: 1px solid #f5dab1;
  border-radius: 6px;
  color: #e6a23c;
  font-weight: 600;
  font-size: 0.92rem;
}

.fu-picked-inline {
  margin: 0 0 8px;
  font-size: 0.9rem;
  font-weight: 600;
  color: #e6a23c;
}

.mock-qa-row {
  margin: 6px 0;
  line-height: 1.5;
  padding: 6px 8px;
  border-radius: 6px;
  transition: background 0.15s ease;
}

.mock-qa-row--selected {
  background: #f0f9eb;
  outline: 1px solid #c2e7b0;
}

.mock-pick-btn {
  margin-left: 8px;
  vertical-align: baseline;
}

.training-runtime-chain {
  margin: -4px 0 14px;
  font-size: 0.86rem;
  line-height: 1.5;
}

.training-board-env-collapse {
  margin: 0 0 12px;
}

.training-chain-nested-board-env {
  margin-top: 12px;
}

.training-ascend-runtime-hint {
  font-size: 0.82rem;
  line-height: 1.5;
  margin: 0 0 8px;
}

.training-ascend-runtime-pre {
  margin: 0;
  padding: 10px 12px;
  font-size: 0.75rem;
  line-height: 1.4;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 280px;
  overflow: auto;
}

/* —— 默认主流程（答辩情景）收口 —— */
.training-page--defense-main .training-page-title {
  font-size: clamp(1.5rem, 1.2vw + 1.1rem, 1.85rem);
  font-weight: 700;
  color: var(--ui-text-primary);
  letter-spacing: -0.02em;
}

.session-info--main .session-info-muted {
  color: #606266;
  font-size: 0.95rem;
  margin: 0;
}

.session-phase-banner--main {
  background: linear-gradient(180deg, #f8fafc 0%, #f0f2f5 100%);
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 14px;
}

.session-phase-line--hero {
  font-size: 1.08rem;
  margin: 0 0 8px;
  color: #303133;
}

.phase-hint--pending {
  color: #409eff;
  font-weight: 500;
}

.video-preview-box--main {
  border-radius: 10px;
  border: 1px solid #ebeef5;
  padding: 12px 14px;
}

.video-preview-box--main h3 {
  margin-top: 0;
  font-size: 1.02rem;
}

.ppt-status-line {
  margin: 10px 0 6px;
  font-size: 0.95rem;
  line-height: 1.55;
}

.ppt-status--ready {
  color: #529b2e;
  font-weight: 600;
}

.ppt-status--selected_not_uploaded {
  color: #b88230;
  font-weight: 500;
}

.ppt-status--uploading {
  color: #409eff;
  font-weight: 500;
}

.ppt-status--failed {
  color: #f56c6c;
  font-weight: 600;
}

.ppt-status--stale_cache {
  color: #606266;
}

.ppt-status--no_file {
  color: #909399;
}

.ppt-debug-id {
  font-size: 0.85rem;
  color: #909399;
  margin: 0 0 8px;
}

.qa-section--main {
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  padding: 18px 20px;
  background: #fcfcfd;
  margin-top: 8px;
}

.qa-section--main h3 {
  margin-top: 0;
  font-size: 1.08rem;
}

.debug-flow-checkbox {
  margin-left: 10px;
}

.training-demo-mode-banner {
  margin-bottom: 12px;
}

.training-demo-mode-banner__body {
  margin: 0 0 10px;
  font-size: 0.88rem;
  line-height: 1.5;
}

.training-demo-mode-banner__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.training-demo-preset-note {
  margin: 0 0 12px;
  font-size: 0.88rem;
}

.training-runtime-chain--demo-spotlight {
  font-weight: 600;
  color: #303133 !important;
  font-size: 0.95rem;
}

.training-board-participation {
  margin: 4px 0 12px;
  font-size: 0.9rem;
  line-height: 1.5;
}

.training-when-demo-soft {
  opacity: 0.72;
}

.training-session-state-banner--demo-spotlight {
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.35);
}

.training-page--demo-mode .unfinished-session-resume,
.training-page--demo-mode .training-resume-fail-alert {
  opacity: 0.78;
}

.training-page-head {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
  text-align: left;
  margin-bottom: 4px;
}

.training-page-head__eyebrow {
  margin-bottom: 4px;
}

.training-page-head__sub {
  margin-bottom: 14px;
}

.training-primary-status-card {
  max-width: 100%;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  margin: 0 0 16px;
  padding: 20px 24px 18px;
  border-radius: var(--ui-radius-lg, 14px);
  border: 1px solid var(--ui-card-border, #dfe7f2);
  background: linear-gradient(165deg, #f8fafc 0%, #fff 55%);
  box-shadow: var(--ui-shadow-card);
}

.training-primary-status-card--session_running_lecture,
.training-primary-status-card--session_running_qa {
  border-color: #c7d2fe;
  background: linear-gradient(165deg, #f5f8ff 0%, #fff 50%);
}

.training-primary-status-card--session_paused_recoverable {
  border-color: #fdba74;
  background: linear-gradient(165deg, #fff7ed 0%, #fff 55%);
}

.training-primary-status-card--demo {
  box-shadow: 0 0 0 1px rgba(34, 197, 94, 0.2);
}

.tps-head {
  margin-bottom: 10px;
}

.tps-title {
  margin: 0 0 6px;
  font-size: 26px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.25;
  color: #0f172a;
}

.tps-eyebrow {
  margin: 0;
  font-size: var(--font-sm, 15px);
  line-height: 1.5;
}

.tps-line {
  margin: 0 0 10px;
  font-size: 16px;
  line-height: 1.6;
  color: #334155;
}

.tps-line--config {
  margin-top: 4px;
  padding-top: 10px;
  border-top: 1px dashed #e2e8f0;
  font-size: 0.86rem;
}

.tps-mission-cta {
  margin: 12px 0 0;
  padding: 12px 0 0;
  border-top: 1px solid var(--ui-card-border, #dfe7f2);
  font-size: var(--font-md, 17px);
  line-height: 1.55;
  color: #1e293b;
  font-weight: 500;
}

.tps-mission-extras {
  margin: 10px 0 0;
  padding: 0;
  font-size: 0.86rem;
}

.tps-mission-extras > summary {
  cursor: pointer;
  color: #64748b;
  font-weight: 600;
  list-style: none;
}

.tps-mission-extras > summary::-webkit-details-marker {
  display: none;
}

.tps-mission-extras__line {
  margin: 6px 0 0;
}

.tps-mission-extras__config {
  font-size: 0.86rem;
}

.tps-mission-resume-cta {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #e2e8f0;
}

.tps-mission-resume-lead {
  margin: 0 0 10px;
  font-size: 0.88rem;
  line-height: 1.5;
}

.tps-mission-extras--resume {
  margin-top: 8px;
}

.training-supplemental-hints {
  max-width: 800px;
  margin: 0 0 12px;
}

.tps-rvr--supplemental {
  border-top: none;
  margin-top: 0;
  padding-top: 0;
}

.ui-controls-dock .training-primary-start-btn {
  min-width: 9.5em;
  font-weight: 700;
}

.tps-k {
  display: inline-block;
  min-width: 4.2em;
  margin-right: 6px;
  font-weight: 600;
  color: #64748b;
  font-size: 15px;
}

.tps-sid {
  font-size: 0.86rem;
  padding: 2px 6px;
  border-radius: 4px;
  background: #f1f5f9;
}

.tps-sid--plain {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
    monospace;
  font-size: 0.82rem;
  color: #64748b;
  background: transparent;
  padding: 0;
}

.tps-sid-line--quiet {
  font-size: 0.85rem;
}

.tps-now .tps-k {
  color: #2563eb;
}

.tps-next {
  color: #475569;
  font-size: 0.88rem;
}

.tps-next .tps-k {
  color: #0d9488;
}

.tps-block-title {
  margin: 14px 0 8px;
  font-size: 0.95rem;
  font-weight: 700;
  color: #0f172a;
}

.tps-resume-block .unfinished-session-resume__list {
  margin: 0 0 8px;
}

.tps-resume-actions {
  margin-top: 4px;
}

.tps-rvr-in-card {
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px dashed #e2e8f0;
}

.tps-rvr-note {
  margin: 0 0 8px;
  font-size: 0.86rem;
}

.tps-rvr-brief {
  margin: 0 0 10px;
  font-size: 0.88rem;
  line-height: 1.5;
}

.tps-resume-inline {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  margin: 10px 0 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  font-size: 0.88rem;
}

.tps-resume-inline__text {
  margin: 0;
  flex: 1;
  min-width: 200px;
}

.tps-aux-h3 {
  margin: 14px 0 8px;
  font-size: 0.95rem;
  font-weight: 700;
  color: #334155;
}

.tps-aux-cta {
  margin: 16px 0 0;
  font-size: 0.82rem;
}

.recent-valid-training-detail {
  margin-bottom: 16px;
  padding: 14px 16px;
}

.training-aux-hints-collapse {
  margin: 0 0 16px;
  max-width: 800px;
}

.training-aux-hints-collapse .el-collapse-item__content {
  padding-bottom: 8px;
}

.training-aux-hints-collapse .training-first-hint {
  margin-bottom: 14px;
}

.training-aux-collapse {
  margin: 10px 0 16px;
  max-width: 800px;
}

.training-flow-ribbon {
  max-width: 800px;
  margin: 0 0 18px;
  padding: 18px 18px 16px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: linear-gradient(145deg, #f8fafc 0%, #f1f5f9 100%);
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.05);
}

.training-flow-ribbon--main {
  border-color: #c7d2fe;
  background: linear-gradient(145deg, #f8faff 0%, #eff6ff 52%, #f8fafc 100%);
}

.training-flow-ribbon--debug {
  border-style: dashed;
  border-color: #cbd5e1;
  background: #f8fafc;
}

.training-flow-ribbon__eyebrow {
  margin: 0 0 8px;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: #64748b;
}

.training-flow-ribbon__title {
  margin: 0 0 14px;
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.3;
  color: #0f172a;
}

.training-flow-ribbon__now,
.training-flow-ribbon__after {
  margin: 0 0 10px;
  font-size: 0.95rem;
  line-height: 1.6;
  color: #1e293b;
}

.training-flow-ribbon__after {
  margin-bottom: 0;
  color: #475569;
  font-size: 0.9rem;
}

.training-flow-ribbon__k {
  font-weight: 700;
  color: #334155;
  margin-right: 6px;
}

.training-config-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 14px;
  max-width: 800px;
  margin: 12px 0 16px;
  padding: 12px 16px;
  font-size: 0.86rem;
  line-height: 1.5;
}

.training-config-strip__k {
  font-weight: 700;
  color: #475569;
  flex-shrink: 0;
}

.training-config-strip__v {
  color: #334155;
}

.training-api-debug {
  max-width: 800px;
  margin: 16px 0;
  font-size: 0.88rem;
}

.training-api-debug summary {
  cursor: pointer;
  font-weight: 600;
  color: #475569;
  margin-bottom: 8px;
}

.api-result--in-details {
  margin-top: 0;
}

.ui-controls-dock__buttons .el-button {
  margin: 0 !important;
}

@media (max-width: 1024px) {
  .training-page {
    padding: 24px 14px 40px;
  }

  .form-row > * {
    flex: 1 1 calc(50% - 12px);
    min-width: 0;
  }

  .mode-radios,
  .mode-radios--deck {
    display: flex;
    flex-direction: column;
    align-items: stretch;
  }

  .mode-radios :deep(.el-radio-button) {
    width: 100%;
  }

  .mode-radios :deep(.el-radio-button__inner) {
    width: 100%;
  }

  .ppt-upload {
    flex-direction: column;
    align-items: stretch;
  }

  .ppt-upload__submit {
    margin-left: 0;
    width: 100%;
  }
}

@media (max-width: 768px) {
  .training-page {
    padding: 20px 10px 36px;
  }

  .training-page-head__sub {
    font-size: 0.84rem;
    margin-bottom: 12px;
  }

  .training-config-strip {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
    padding: 12px 14px;
  }

  .training-config-strip__v {
    word-break: break-word;
  }

  .form-row > * {
    flex: 1 1 100%;
    min-width: 0;
  }

  .training-page .el-button {
    margin-left: 4px !important;
    margin-right: 4px !important;
  }

  .camera-preview {
    max-height: min(50vh, 280px);
  }

  .tsg-track-item {
    font-size: 0.74rem;
    padding: 4px 8px;
  }

  .fu-main-row {
    flex-direction: column;
    align-items: stretch;
  }

  .qa-followup-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .qa-followup-actions .el-button {
    width: 100%;
    margin: 0;
  }

  .mock-qa-generate-section,
  .ppt-match-section,
  .metrics-form {
    padding: 16px;
    margin-left: 0;
    margin-right: 0;
  }
}

@media (max-width: 560px) {
  .tss-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .unfinished-session-resume__actions,
  .recent-valid-training-reminder__actions {
    flex-direction: column;
    align-items: stretch;
  }

  .unfinished-session-resume__actions .el-button,
  .recent-valid-training-reminder__actions .el-button {
    width: 100%;
    margin: 0;
  }
}

@media print {
  .no-print {
    display: none !important;
  }
}
</style>