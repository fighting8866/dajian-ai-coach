<template>
  <div
    class="report-page report-page--brand-v1 ui-page-frame ui-page-shell-inset"
    :class="{
      'report-page--demo-mode': reportDemoState.active,
      'report-page--screen-v2': !!reportData,
    }"
  >
    <section
      v-if="!reportData"
      class="report-top-actions report-top-actions--toolbar report-export-panel report-export-panel--gate no-print"
      aria-label="报告入口说明"
    >
      <header class="report-top-actions__formal">
        <p class="report-formal-eyebrow">正式训练报告</p>
        <p v-if="loading" class="report-formal-deck report-formal-deck--toolbar muted">
          {{ PAGE_LOADING.report.hint }}
        </p>
        <p v-else class="report-formal-deck report-formal-deck--toolbar muted">
          请从某次「训练结果」或「历史」进入带本会话编号的报告。加载完成后可在报告首页使用「打印报告」留档为 PDF。
        </p>
      </header>
    </section>

    <div v-if="loading" class="report-load-placeholder no-print" aria-busy="true" aria-live="polite">
      <p class="report-load-placeholder__label muted">{{ PAGE_LOADING.report.label }}</p>
      <p class="report-load-placeholder__hint muted">{{ PAGE_LOADING.report.hint }}</p>
      <el-skeleton :rows="12" animated />
    </div>
    <div v-else-if="errorMessage" class="report-error-panel no-print">
      <el-alert type="error" :closable="false" show-icon :title="PAGE_ERROR_ALERT_TITLE.report">
        <p class="report-error-panel__body">{{ errorMessage }}</p>
        <div class="report-error-panel__actions report-page-error-actions">
          <el-button type="primary" @click="retryLoadReport">重试</el-button>
          <el-dropdown trigger="click" class="report-page-actions-more">
            <el-button type="default" plain
              >其他路线
              <span class="ui-dropdown-caret" aria-hidden="true">▾</span></el-button
            >
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="goHomeFromReport">返回首页</el-dropdown-item>
                <el-dropdown-item @click="goBack">返回结果页</el-dropdown-item>
                <el-dropdown-item @click="goHistoryFromReport">查看历史</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-alert>
    </div>
    <div v-else-if="!sessionId" class="report-error-panel no-print">
      <el-alert type="warning" :closable="false" show-icon title="暂无法从本页打开报告">
        <p class="report-error-panel__body">
          当前没有可打开报告的会话。请从某次「训练结果」进入，或到「历史」点某条「查看详情」进入该次结果，再点「查看训练报告」；链接或地址栏中需带本次会话编号。
        </p>
        <div class="report-error-panel__actions report-page-error-actions">
          <el-button type="primary" @click="goTrainingFromReport">去训练</el-button>
          <el-dropdown trigger="click" class="report-page-actions-more">
            <el-button type="default" plain
              >其他路线
              <span class="ui-dropdown-caret" aria-hidden="true">▾</span></el-button
            >
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="goHomeFromReport">返回首页</el-dropdown-item>
                <el-dropdown-item @click="goHistoryFromReport">查看历史</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-alert>
    </div>

    <div v-else-if="reportData" class="report-print-body report-print-body--screen-v2">
      <div v-if="reportTrainingInvalid" class="report-invalid-callout print-avoid-break">
        <strong class="report-invalid-callout__title">未纳入统计</strong>
        <p class="report-invalid-callout__body">{{ reportInvalidTrainingExplainLine }}</p>
      </div>
      <nav class="ui-inpage-nav report-inpage-nav report-inpage-nav--report-v2 no-print" aria-label="报告快速定位">
        <a class="ui-inpage-nav__link" href="#report-anchor-overview" @click="onInpageNavLinkClick">报告首页</a>
        <a
          class="ui-inpage-nav__link"
          :href="safeSummary ? '#report-anchor-conclusion' : '#report-anchor-overview'"
          @click="onInpageNavLinkClick"
          >综合结论</a
        >
        <a class="ui-inpage-nav__link" href="#report-anchor-metrics" @click="onInpageNavLinkClick">关键得分</a>
        <a class="ui-inpage-nav__link" href="#report-anchor-analysis" @click="onInpageNavLinkClick">详细分析</a>
        <a class="ui-inpage-nav__link" href="#report-anchor-content" @click="onInpageNavLinkClick">内容讲解</a>
        <a class="ui-inpage-nav__link" href="#report-anchor-qa" @click="onInpageNavLinkClick">问答表现</a>
        <a class="ui-inpage-nav__link" href="#report-anchor-suggestions" @click="onInpageNavLinkClick">下一轮建议</a>
      </nav>
      <header
        id="report-anchor-overview"
        tabindex="-1"
        class="report-header report-header-v1 report-hero-screen print-avoid-break inpage-nav-target"
      >
        <div class="report-hero-layout">
          <div class="report-hero-main">
            <p class="report-doc-kicker muted screen-only">单轮训练报告 · 屏幕阅读</p>
            <p class="report-doc-kicker print-only report-doc-kicker--print-cover">训练报告（留档版）</p>
            <div class="report-title-row">
              <h1 class="report-title">{{ SECTION.reportTitle }}</h1>
              <div class="report-hero-score" aria-label="总分">
                <span class="report-hero-score__k">总分</span>
                <span class="report-hero-score__v">{{ formatScore(safeTotalScore) }}</span>
              </div>
            </div>
            <div class="report-hero-subscores" aria-label="分项得分">
              <div class="report-hero-subscores__cell">
                <span class="report-hero-subscores__k">语言</span>
                <span class="report-hero-subscores__v">{{ formatScore(safeScores?.language_score) }}</span>
              </div>
              <div class="report-hero-subscores__cell">
                <span class="report-hero-subscores__k">仪态</span>
                <span class="report-hero-subscores__v">{{ formatScore(safeScores?.posture_score) }}</span>
              </div>
              <div class="report-hero-subscores__cell">
                <span class="report-hero-subscores__k">内容</span>
                <span
                  class="report-hero-subscores__v"
                  :class="{ 'report-subscore--na': displayContentScoreText === '未生成' }"
                >{{ displayContentScoreText }}</span>
              </div>
              <div class="report-hero-subscores__cell">
                <span class="report-hero-subscores__k">问答</span>
                <span class="report-hero-subscores__v">{{ formatScore(safeScores?.qa_score) }}</span>
              </div>
            </div>
            <div class="header-meta report-hero-meta">
              <div class="meta-row">
                <span class="meta-label">训练时间</span>
                <span class="meta-value">{{ formattedReportTime }}</span>
              </div>
              <div class="meta-row">
                <span class="meta-label">学员</span>
                <span class="meta-value">{{ reportPrintDisplayName }}</span>
              </div>
              <div class="meta-row">
                <span class="meta-label">会话编号</span>
                <span class="meta-value meta-mono meta-session-compact" :title="reportData.session_id || ''">{{
                  shortSessionDisplay
                }}</span>
              </div>
              <div class="meta-row">
                <span class="meta-label">评分模式</span>
                <span class="meta-value">{{ safeScoringProfileLabel }}</span>
              </div>
              <div class="meta-row">
                <span class="meta-label">训练重点</span>
                <span class="meta-value">{{ sessionRoundTrainingFocusLabel }}</span>
              </div>
            </div>
            <div v-if="reportHeroSummaryLine" class="report-hero-summary print-avoid-break">
              <span class="inline-label">综合点评摘要</span>
              <p class="report-hero-summary__text">{{ reportHeroSummaryLine }}</p>
            </div>
            <p v-if="showPreflightOkLine" class="preflight-ok-note muted no-print">本轮训练开始前已通过基础准备检查。</p>
          </div>
          <aside class="report-hero-toolbar no-print" aria-label="报告留档与后续操作">
            <p class="report-hero-toolbar__title">留档与后续</p>
            <p class="report-hero-toolbar__micro muted">打印可调起系统对话框，另存为 PDF；文件不上传服务器。</p>
            <div class="report-hero-toolbar__actions">
              <el-button type="primary" :disabled="loading || !reportData" @click="printReport">打印报告</el-button>
              <el-button type="default" @click="goBack">返回结果</el-button>
            </div>
            <div class="report-hero-toolbar__row2">
              <el-button type="primary" plain size="small" @click="reportClosureTrainRecommended">继续训练</el-button>
              <el-dropdown trigger="click" class="report-hero-toolbar__more">
                <el-button type="default" plain size="small">
                  更多
                  <span class="ui-dropdown-caret" aria-hidden="true">▾</span>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="reportClosureGoHome">返回首页</el-dropdown-item>
                    <el-dropdown-item @click="goHistoryFromReport">查看历史</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            <el-alert
              v-if="reportDemoState.active"
              class="report-hero-toolbar__demo no-print"
              type="success"
              :closable="false"
              show-icon
              title="演示精简模式"
            >
              <p class="muted report-hero-toolbar__demo-line">打印与正文一致；技术说明见可选折叠区。</p>
              <el-button size="small" type="primary" plain @click="exitReportDemoMode">退出演示</el-button>
            </el-alert>
          </aside>
        </div>
      </header>

      <section
        v-if="safeSummary"
        id="report-anchor-conclusion"
        tabindex="-1"
        class="report-section report-section-summary report-section--conclusion report-screen-chapter print-avoid-break inpage-nav-target"
      >
        <h2 class="report-part-h2">一、总体结论</h2>
        <p class="report-part-lead muted no-print">对本轮的概括性判断；下方为分项依据、数据与具体建议。</p>
        <h3 class="section-title section-title--sub">{{ SECTION.overallSummary }}</h3>
        <p><span class="inline-label">总评</span>{{ safeSummary.overall_comment || '—' }}</p>
        <p><span class="inline-label">亮点</span>{{ safeSummary.strongest_aspect || '—' }}</p>
        <p><span class="inline-label">可加强</span>{{ safeSummary.weakest_aspect || '—' }}</p>
      </section>

      <section
        v-if="safeNextRoundAdviceDisplay.length"
        class="report-next-preview no-print"
        aria-label="下一轮训练建议摘要"
      >
        <div class="report-next-preview__head">
          <h3 class="report-next-preview__title">下一轮建议（摘要）</h3>
          <a
            class="ui-inpage-nav__link report-next-preview__jump"
            href="#report-anchor-suggestions"
            @click="onInpageNavLinkClick"
            >完整建议 →</a
          >
        </div>
        <ul class="bullet-list tight">
          <li v-for="(line, i) in safeNextRoundAdviceDisplay.slice(0, 3)" :key="`rnp-${i}`">{{ line }}</li>
        </ul>
      </section>

      <div
        id="report-anchor-analysis"
        tabindex="-1"
        class="report-part report-part--analysis report-screen-part inpage-nav-target"
      >
        <h2 class="report-part-h2">二、分项分析</h2>
        <p class="report-part-lead muted no-print">自得分、专项、点评至各维度的依据与说明，可与上节结论对照阅读。</p>

      <section id="report-anchor-metrics" tabindex="-1" class="report-section report-screen-chapter print-avoid-break inpage-nav-target">
        <h3 class="section-title">{{ SECTION.primaryScores }}</h3>
        <div class="score-grid">
          <div class="score-cell">
            <div class="score-name">语言</div>
            <div class="score-num">{{ formatScore(safeScores?.language_score) }}</div>
          </div>
          <div class="score-cell">
            <div class="score-name">仪态</div>
            <div class="score-num">{{ formatScore(safeScores?.posture_score) }}</div>
          </div>
          <div class="score-cell">
            <div class="score-name">内容</div>
            <div
              class="score-num"
              :class="{ 'score-num--na': displayContentScoreText === '未生成' }"
            >
              {{ displayContentScoreText }}
            </div>
          </div>
          <div class="score-cell">
            <div class="score-name">问答</div>
            <div class="score-num">{{ formatScore(safeScores?.qa_score) }}</div>
          </div>
        </div>
      </section>

        <div
          v-if="reportFocusTrendLine || reportFocusOutcomeVisible"
          class="header-meta report-focus-embed print-avoid-break"
          aria-label="本专项与对比"
        >
          <h3 class="section-title section-title--sub">本专项与近期对比</h3>
          <div v-if="reportFocusTrendLine" class="meta-row print-avoid-break report-focus-trend-row">
            <span class="meta-label">本专项趋势</span>
            <span class="meta-value meta-text-wrap">{{ reportFocusTrendLine }}</span>
          </div>
          <div
            v-if="reportFocusOutcomeVisible"
            class="report-focus-outcome print-avoid-break"
          >
            <div v-if="reportPrimaryFocusScore" class="meta-row">
              <span class="meta-label">本专项核心分</span>
              <span class="meta-value">{{ reportPrimaryFocusScore }}</span>
            </div>
            <div class="meta-row report-focus-outcome-row">
              <span class="meta-label">和最近同专项比</span>
              <span class="meta-value meta-text-wrap">{{ reportFocusVsRecentLine }}</span>
            </div>
            <div class="meta-row report-focus-outcome-row">
              <span class="meta-label">下一轮怎么选</span>
              <span class="meta-value meta-text-wrap">{{ reportFocusNextLabelLine }}</span>
            </div>
            <p v-if="reportData?.training_focus_summary" class="report-focus-summary muted">
              {{ reportData.training_focus_summary }}
            </p>
            <div
              v-if="reportFocusMetricBlockVisible"
              class="report-focus-metric-block print-avoid-break"
            >
              <div class="meta-row report-focus-metric-title">
                <span class="meta-label">专项关键指标对比</span>
              </div>
              <p v-if="reportFocusMetricLead" class="report-focus-metric-lead muted">
                {{ reportFocusMetricLead }}
              </p>
              <ul v-if="reportFocusMetricHighlights.length" class="report-focus-metric-list">
                <li v-for="(line, i) in reportFocusMetricHighlights" :key="`rfc-${i}`">{{ line }}</li>
              </ul>
              <p v-else class="report-focus-metric-fallback muted">暂无足够同专项对比数据</p>
            </div>
          </div>
        </div>

        <p
          v-if="String(reportData?.scoring_profile || safeScoringProfile || '').trim() === 'defense'"
          class="defense-flow-overview defense-flow-overview--in-analysis muted no-print"
        >
          {{ DEFENSE_FLOW_OVERVIEW }}
        </p>

      <section
        class="report-section print-avoid-break coach-report-section teacher-report-section report-teacher-panel report-screen-chapter"
      >
        <h3 class="section-title">{{ SECTION.teacherFeedback }}</h3>
        <p
          v-if="String(reportData?.training_focus || 'none').trim().toLowerCase() !== 'none'"
          class="teacher-focus-context-report muted no-print"
        >
          已按本轮训练重点与专项对比整理，便于对照明细。
        </p>
        <el-collapse
          v-model="reportCognitiveCollapse"
          class="ui-aux-collapse ui-aux-collapse--low report-print-hidden report-cognitive-aux"
          :class="{ 'report-demo-muted': reportDemoState.active }"
        >
          <el-collapse-item name="cog" title="各问题与点评的生成方式（可选）">
            <div
              class="cognitive-provider-report cognitive-provider-report--in-collapse print-avoid-break"
              :class="{ 'report-demo-muted': reportDemoState.active }"
            >
              <p><span class="inline-label">提问</span>{{ cognitiveProviderDisplay.question }}</p>
              <p><span class="inline-label">追问</span>{{ cognitiveProviderDisplay.followup }}</p>
              <p><span class="inline-label">点评</span>{{ cognitiveProviderDisplay.commentary }}</p>
            </div>
          </el-collapse-item>
        </el-collapse>
        <p class="coach-commentary-print teacher-report-lead">{{ safeOverallCommentary || '暂无综合点评。' }}</p>
        <div v-if="safeCoachStrengths.length" class="teacher-report-block">
          <p class="inline-label">本轮优点</p>
          <ul class="bullet-list tight">
            <li v-for="(line, i) in safeCoachStrengths" :key="`rst-${i}`">{{ line }}</li>
          </ul>
        </div>
        <div v-if="safeCoachWeaknesses.length" class="teacher-report-block">
          <p class="inline-label">本轮主要问题</p>
          <ul class="bullet-list tight">
            <li v-for="(line, j) in safeCoachWeaknesses" :key="`rwk-${j}`">{{ line }}</li>
          </ul>
        </div>
        <p class="muted teacher-report-footnote no-print">以上内容依据训练与评分规则自动归纳整理。</p>
      </section>

      <section
        class="report-section print-avoid-break coach-report-section report-demo-muted-target"
        :class="{ 'report-demo-muted': reportDemoState.active }"
      >
        <h3 class="section-title">AI 追问建议</h3>
        <p v-if="!safeFollowupQuestions.length" class="muted">暂无追问条目。</p>
        <ul v-else class="bullet-list tight coach-followup-report">
          <li v-for="(fq, i) in safeFollowupQuestions" :key="`rfq-${i}`">
            <span class="inline-label">追问</span>{{ fq.question || '—' }}
            <div class="coach-reason-print"><span class="inline-label">说明</span>{{ fq.reason || '—' }}</div>
            <div v-if="followupDirectionLabel(fq.source)" class="coach-src-print muted no-print">
              {{ followupDirectionLabel(fq.source) }}
            </div>
          </li>
        </ul>
      </section>

      <section
        class="report-section print-avoid-break report-demo-muted-target"
        :class="{ 'report-demo-muted': reportDemoState.active }"
      >
        <h3 class="section-title">统一评分说明</h3>
        <p class="lead">{{ totalExplanation.summary }}</p>
        <ul v-if="totalExplanation.items.length" class="bullet-list report-print-hide-bullets">
          <li v-for="(line, index) in totalExplanation.items" :key="`t-${index}`">{{ line }}</li>
        </ul>
        <div
          v-for="item in scoreExplanationCards"
          :key="item.key"
          class="explain-card"
          :class="{
            'explain-card--optional-skip': item.contentOptionalMissing,
            'explain-card--print-invalid': item.valid === false && !item.contentOptionalMissing,
          }"
        >
          <div class="explain-card-head">
            <strong>{{ item.label }}</strong>
            <span
              class="explain-score"
              :class="{ 'explain-score--na': item.key === 'content' && item.contentOptionalMissing }"
            >{{ item.scoreDisplay }}</span>
          </div>
          <p class="module-status">{{ moduleStatusLine(item.key, item.valid) }}</p>
          <p
            v-if="item.key === 'content' && showPptReportSectionSource"
            class="report-source-line explain-source-line no-print"
          >
            <strong>课件与内容对齐：</strong>{{ pptMatchSourceLine }}
          </p>
          <p
            v-if="item.key === 'qa' && showQaReportSectionSource"
            class="report-source-line explain-source-line no-print"
          >
            <strong>问答环节：</strong>{{ qaSourceLine }}
          </p>
          <p
            v-if="item.key === 'qa' && safeQaResult?.answer_input_mode === 'voice'"
            class="report-source-line explain-source-line muted no-print"
          >
            本轮回答采用语音作答。
          </p>
          <p class="explain-summary">{{ item.explanation.summary }}</p>
          <ul v-if="item.explanation.items.length" class="bullet-list tight report-print-hide-bullets">
            <li v-for="(line, index) in item.explanation.items" :key="`${item.key}-${index}`">{{ line }}</li>
          </ul>
        </div>
      </section>

      <el-collapse
        v-model="reportModalityCollapse"
        class="ui-aux-collapse ui-aux-collapse--low report-print-hidden report-tech-aux report-demo-muted-target"
        :class="{ 'report-demo-muted': reportDemoState.active }"
      >
        <el-collapse-item name="mod" title="各模态如何参与本轮评分（可选）">
          <div class="report-tech-aux-body">
            <ul class="bullet-list plain">
              <li>{{ modalityNarrative.language }}</li>
              <li>{{ modalityNarrative.posture }}</li>
              <li>{{ modalityNarrative.content }}</li>
              <li>{{ modalityNarrative.qa }}</li>
            </ul>
          </div>
        </el-collapse-item>
      </el-collapse>

      <section
        class="report-section report-demo-muted-target"
        :class="{ 'report-demo-muted': reportDemoState.active }"
      >
        <h3 class="section-title">音频与语言指标</h3>
        <p v-if="!reportPrintLanguageHasDetail" class="muted report-print-module-fallback print-only">
          {{ reportPrintLanguageShort }}
        </p>
        <template v-if="reportPrintLanguageHasDetail">
          <p class="module-status">{{ audioSectionIntro }}</p>
          <p class="transcript-block">
            <span class="inline-label">转写</span>
            {{
              resolvedAudioMetrics.audio_valid === false
                ? '（本轮无有效转写）'
                : resolvedAudioMetrics.transcript || '（本轮未记录可用转写）'
            }}
          </p>
          <div class="kv-grid">
            <div class="kv-row">
              <span>语速</span><span>{{ formatSessionMetricCell(resolvedAudioMetrics.speech_rate) }}</span>
            </div>
            <div class="kv-row">
              <span>停顿次数</span><span>{{ formatSessionMetricCell(resolvedAudioMetrics.pause_count) }}</span>
            </div>
            <div class="kv-row">
              <span>平均停顿时长</span><span>{{ formatSessionMetricCell(resolvedAudioMetrics.avg_pause_sec) }}</span>
            </div>
            <div class="kv-row">
              <span>口头禅次数</span><span>{{ formatSessionMetricCell(resolvedAudioMetrics.filler_count) }}</span>
            </div>
          </div>
        </template>
        <div v-else class="no-print">
          <p class="module-status">{{ audioSectionIntro }}</p>
          <p class="transcript-block">
            <span class="inline-label">转写</span>
            {{
              resolvedAudioMetrics.audio_valid === false
                ? '（本轮无有效转写）'
                : resolvedAudioMetrics.transcript || '（本轮未记录可用转写）'
            }}
          </p>
          <div class="kv-grid">
            <div class="kv-row">
              <span>语速</span><span>{{ formatSessionMetricCell(resolvedAudioMetrics.speech_rate) }}</span>
            </div>
            <div class="kv-row">
              <span>停顿次数</span><span>{{ formatSessionMetricCell(resolvedAudioMetrics.pause_count) }}</span>
            </div>
            <div class="kv-row">
              <span>平均停顿时长</span><span>{{ formatSessionMetricCell(resolvedAudioMetrics.avg_pause_sec) }}</span>
            </div>
            <div class="kv-row">
              <span>口头禅次数</span><span>{{ formatSessionMetricCell(resolvedAudioMetrics.filler_count) }}</span>
            </div>
          </div>
        </div>
      </section>

      <section
        class="report-section report-demo-muted-target"
        :class="{ 'report-demo-muted': reportDemoState.active }"
      >
        <h3 class="section-title">视觉与仪态指标</h3>
        <p v-if="!reportPrintPostureHasDetail" class="muted report-print-module-fallback print-only">
          {{ reportPrintPostureShort }}
        </p>
        <template v-if="reportPrintPostureHasDetail">
          <p class="module-status">{{ visionSectionIntro }}</p>
          <div class="kv-grid">
            <div class="kv-row">
              <span>正视前方比例</span
              ><span>{{ formatSessionMetricCell(resolvedVisionMetrics.forward_gaze_ratio) }}</span>
            </div>
            <div class="kv-row">
              <span>低头率</span><span>{{ formatSessionMetricCell(resolvedVisionMetrics.downward_head_ratio) }}</span>
            </div>
            <div class="kv-row">
              <span>姿态稳定度</span
              ><span>{{ formatSessionMetricCell(resolvedVisionMetrics.posture_stability) }}</span>
            </div>
          </div>
        </template>
        <div v-else class="no-print">
          <p class="module-status">{{ visionSectionIntro }}</p>
          <p class="muted">
            {{ resolvedVisionMetrics.vision_message || '本轮未形成可展示的仪态数值，请结合上方说明理解。' }}
          </p>
        </div>
      </section>

      <el-collapse
        v-if="reportData"
        v-model="reportLongSessionCollapse"
        class="ui-aux-collapse ui-aux-collapse--low report-print-hidden long-session-report-section report-demo-muted-target"
        :class="{ 'report-demo-muted': reportDemoState.active }"
      >
        <el-collapse-item name="long" title="整场答辩分段与采样摘要（可选）">
      <section
        class="report-section print-avoid-break long-session-report-section long-session-report-section--inner"
      >
        <h3 class="section-title">整场答辩 · 长时会话摘要</h3>
        <p v-if="resolvedLongSessionSummary.hasSummary" class="muted long-session-report-lead">
          同一会话下的音频分段与视频采样汇总，与上方语言/仪态指标为一场答辩。
        </p>
        <div v-if="resolvedLongSessionSummary.hasSummary" class="long-session-report-columns">
          <div v-if="resolvedLongSessionSummary.audio" class="long-session-report-block">
            <p class="inline-label">音频汇总</p>
            <div class="kv-grid">
              <div class="kv-row">
                <span>总时长</span
                ><span>{{ formatSessionSeconds(resolvedLongSessionSummary.audio.total_audio_duration_sec) }}</span>
              </div>
              <div class="kv-row">
                <span>识别段数</span
                ><span>{{ formatSessionInt(resolvedLongSessionSummary.audio.transcribed_chunks) }}</span>
              </div>
              <div class="kv-row">
                <span>跳过段数</span
                ><span>{{ formatSessionInt(resolvedLongSessionSummary.audio.skipped_chunks) }}</span>
              </div>
              <div class="kv-row">
                <span>丢弃脏段数</span
                ><span>{{ formatSessionInt(resolvedLongSessionSummary.audio.dropped_dirty_chunks) }}</span>
              </div>
            </div>
          </div>
          <div v-if="resolvedLongSessionSummary.video" class="long-session-report-block">
            <p class="inline-label">视频汇总</p>
            <div class="kv-grid">
              <div class="kv-row">
                <span>总时长</span
                ><span>{{
                  formatSessionSeconds(resolvedLongSessionSummary.video.total_video_duration_sec)
                }}</span>
              </div>
              <div v-if="resolvedLongSessionSummary.video.duration_source" class="kv-row">
                <span>时长来源</span><span>{{ String(resolvedLongSessionSummary.video.duration_source) }}</span>
              </div>
              <div class="kv-row">
                <span>处理帧数</span
                ><span>{{ formatSessionInt(resolvedLongSessionSummary.video.processed_frames) }}</span>
              </div>
              <div class="kv-row">
                <span>跳过帧数</span
                ><span>{{ formatSessionInt(resolvedLongSessionSummary.video.skipped_frames) }}</span>
              </div>
              <div class="kv-row">
                <span>采样模式</span
                ><span>{{
                  formatSampledModeLabel(
                    resolvedLongSessionSummary.video.sampled_mode_used,
                    resolvedLongSessionSummary.video.sampled_fps
                  )
                }}</span>
              </div>
            </div>
          </div>
        </div>
        <p v-else class="muted">本轮未回传长时会话摘要</p>
      </section>
        </el-collapse-item>
      </el-collapse>

      <section
        id="report-anchor-content"
        tabindex="-1"
        class="report-section print-avoid-break report-demo-muted-target report-screen-chapter inpage-nav-target"
        :class="{ 'report-demo-muted': reportDemoState.active }"
      >
        <h3 class="section-title">内容与幻灯片</h3>
        <p v-if="!reportPrintContentHasDetail" class="muted report-print-module-fallback print-only">
          {{ reportPrintContentShort }}
        </p>
        <div :class="{ 'no-print': !reportPrintContentHasDetail }">
          <template v-if="safePptMatch">
            <p v-if="showPptReportSectionSource" class="report-source-line no-print">
              <strong>课件与内容对齐：</strong>{{ pptMatchSourceLine }}
            </p>
            <p>当前页：第 {{ safePptMatch.page_index ?? '—' }} 页 — {{ safePptMatch.title || '—' }}</p>
            <div class="kv-grid">
              <div class="kv-row"><span>匹配度</span><span>{{ safePptMatch.match_score ?? '—' }}</span></div>
              <div class="kv-row"><span>关键词覆盖</span><span>{{ safePptMatch.keyword_coverage ?? '—' }}</span></div>
            </div>
            <p>命中关键词：{{ safePptHitKeywords }}</p>
            <p>待加强关键词：{{ safePptMissingKeywords }}</p>
            <p>点评：{{ safePptMatch.comment || '—' }}</p>
          </template>
          <template v-else-if="hasPptMatchAnalysis">
            <p class="muted">本轮以逐页讲解对齐为主（未使用单页匹配卡片）。</p>
            <p v-if="pptAnalysisOverall != null">整体匹配得分：{{ pptAnalysisOverall }}</p>
          </template>
          <p v-else-if="hasContentOnlyPptMatchCard" class="muted">
            本轮为单页或自动猜页匹配，暂无整册逐页分析；内容得分仍以单页对齐卡片为准。
          </p>
          <p v-else-if="isWithoutPptDefense" class="muted">
            本轮为无课件答辩训练，未启用课件匹配；系统聚焦语言、仪态、问答与老师点评。
          </p>
          <p v-else class="report-content-placeholder-note muted">
            本次训练未生成 PPT 内容匹配分析，可在上传 PPT 并完成有效讲解后生成。
          </p>
        </div>
        <div v-if="reportPrintContentHasDetail && contentBreakdownLines.length" class="content-breakdown-report">
          <p class="inline-label">内容得分补充分解</p>
          <ul class="bullet-list tight report-print-hide-bullets">
            <li v-for="(line, idx) in contentBreakdownLines" :key="`rcbd-${idx}`">{{ line }}</li>
          </ul>
        </div>
      </section>

      <section
        id="report-anchor-qa"
        tabindex="-1"
        class="report-section print-avoid-break report-demo-muted-target report-screen-chapter inpage-nav-target"
        :class="{ 'report-demo-muted': reportDemoState.active }"
      >
        <h3 class="section-title">问答评估</h3>
        <p v-if="!reportPrintQaHasDetail" class="muted report-print-module-fallback print-only">{{ reportPrintQaShort }}</p>
        <div :class="{ 'no-print': !reportPrintQaHasDetail }">
          <template v-if="safeQaResult">
            <p v-if="showQaReportSectionSource" class="report-source-line no-print"><strong>问答环节：</strong>{{ qaSourceLine }}</p>
            <p
              v-if="safeQaResult && safeQaResult.answer_input_mode === 'voice'"
              class="muted qa-voice-answer-note-print no-print"
            >
              本轮回答采用语音作答。
            </p>
            <p
              v-if="
                showQaReportSectionSource &&
                (safeQaResult?.qa_source === 'followup_generated' || reportData?.qa_source === 'followup_generated')
              "
              class="muted report-source-line no-print"
            >
              本轮追问在第一轮回答评估后按规则生成。
            </p>
            <p v-if="showDefenseSequentialFlowHint" class="report-source-line defense-flow-hint-print no-print">
              流程说明：先完成讲解阶段，再进入答辩问答。
            </p>
            <p
              v-if="
                showQaReportSectionSource &&
                (safeQaResult.qa_source === 'followup_generated' || reportData?.qa_source === 'followup_generated') &&
                (safeQaResult.followup_reason ||
                  safeQaResult.followup_target_topic ||
                  reportData?.selected_followup_reason)
              "
              class="report-source-line followup-reason-print no-print"
            >
              <strong>追问依据：</strong>
              <template v-if="safeQaResult.followup_target_topic">主题「{{ safeQaResult.followup_target_topic }}」。</template>
              {{ safeQaResult.followup_reason || reportData?.selected_followup_reason || '' }}
            </p>
            <p>题目：{{ safeQaResult.question || '—' }}</p>
            <p>是否切题：{{ safeQaResult.is_relevant ? '是' : '否' }}</p>
            <p>覆盖率：{{ safeQaResult.coverage_score ?? '—' }}</p>
            <p>命中关键词：{{ safeQaHitKeywords }}</p>
            <p>待加强关键词：{{ safeQaMissingKeywords }}</p>
            <p>点评：{{ safeQaResult.comment || '—' }}</p>
          </template>
          <p v-else class="muted">本轮未进行问答评估。</p>
        </div>
        <div v-if="reportPrintQaHasDetail && qaBreakdownLines.length" class="content-breakdown-report">
          <p class="inline-label">问答得分补充分解</p>
          <ul class="bullet-list tight report-print-hide-bullets">
            <li v-for="(line, idx) in qaBreakdownLines" :key="`rqbd-${idx}`">{{ line }}</li>
          </ul>
        </div>
      </section>

      <el-collapse
        v-if="reportInferenceChainLine"
        v-model="reportInferenceCollapse"
        class="ui-aux-collapse ui-aux-collapse--low report-print-hidden report-inference-aux report-inference-aux--wrap"
      >
        <el-collapse-item name="inf" title="推理与运行环境说明（可选）">
          <p
            class="report-inference-chain muted"
            :class="{ 'report-inference-chain--demo-spotlight': reportDemoState.active }"
          >
            {{ reportInferenceChainLine }}
          </p>
        </el-collapse-item>
      </el-collapse>
      </div>

      <section
        id="report-anchor-suggestions"
        tabindex="-1"
        class="report-section report-section--recommendations report-screen-chapter print-avoid-break inpage-nav-target"
      >
        <h2 class="report-part-h2">三、改进建议</h2>
        <p class="report-part-lead muted no-print">可据此安排日常练习、下一轮训练与系统整理项。</p>

        <div v-if="safeSummary" class="print-avoid-break report-suggestion-block">
          <h3 class="section-title section-title--sub">练习与训练要点</h3>
          <p>
            <span class="inline-label">练习建议</span>{{ safeSummary.training_tip || '—' }}
          </p>
        </div>

        <div class="print-avoid-break report-suggestion-block">
          <h3 class="section-title section-title--sub">下一轮训练建议</h3>
          <ul v-if="safeNextRoundAdviceDisplay.length" class="bullet-list tight">
            <li v-for="(line, k) in safeNextRoundAdviceDisplay" :key="`rnr-${k}`">{{ line }}</li>
          </ul>
          <p v-else class="muted">暂无具体条目，可对照上方分维与评分说明。</p>
        </div>

        <div class="print-avoid-break report-suggestion-block">
          <h3 class="section-title section-title--sub">主要建议</h3>
          <ul v-if="mainRecommendationsList.length" class="bullet-list">
            <li v-for="(line, idx) in mainRecommendationsList" :key="idx">{{ line }}</li>
          </ul>
          <p v-else class="muted">本轮暂无系统单独整理的主要建议，可参考上节练习要点与分维分析。</p>
        </div>

        <p
          v-if="
            !safeSummary &&
            !safeNextRoundAdviceDisplay.length &&
            !mainRecommendationsList.length
          "
          class="muted report-suggestion-fallback"
        >
          本轮无单独整理的建议条目，可对照上方一、二部分自行提炼行动项。
        </p>
      </section>

      <el-collapse
        v-if="safeMetrics.length"
        v-model="reportAppendixCollapse"
        class="ui-aux-collapse ui-aux-collapse--low report-print-hidden metrics-appendix print-break-before-appendix report-demo-muted-target"
        :class="{ 'report-demo-muted': reportDemoState.active }"
      >
        <el-collapse-item name="app" title="附录：原始指标项（可选）">
          <section class="report-section metrics-appendix-inner">
            <h2 class="section-title metrics-appendix-inner-title">附录 · 原始指标项</h2>
            <div class="metrics-lines">
              <div v-for="item in safeMetrics" :key="item.name" class="metric-line">
                {{ item.name }}：{{ item.value }}{{ item.unit || '' }}
              </div>
            </div>
          </section>
        </el-collapse-item>
      </el-collapse>

      <section
        class="report-page-flow-foot ui-surface ui-surface--subtle no-print inpage-nav-target"
        aria-label="阅读完成后的后续步骤"
      >
        <p class="report-page-flow-foot__eyebrow">本页导览</p>
        <h2 class="report-page-flow-foot__title">阅读完成后的后续步骤</h2>
        <p class="report-page-flow-foot__lead muted">
          以下为屏幕内跳转，不进入已打印的文稿。若已按上文建议有下一步，可从「按建议方向训练」进入训练准备。
        </p>
        <div class="report-page-flow-foot__actions report-flow-nav report-flow-nav--tiered" role="group">
          <el-button type="default" @click="goBack">返回结果页</el-button>
          <el-dropdown trigger="click" class="report-page-actions-more report-page-flow-foot__more">
            <el-button type="default" plain
              >更多步骤
              <span class="ui-dropdown-caret" aria-hidden="true">▾</span></el-button
            >
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="reportClosureGoHome">返回首页</el-dropdown-item>
                <el-dropdown-item @click="reportClosureTrainRecommended">按建议方向训练</el-dropdown-item>
                <el-dropdown-item divided @click="reportClosureViewHistory">查看历史</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onInpageNavLinkClick } from '../utils/a11yInpageNav'
import { ref, computed, watch, onMounted, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getJson } from '../api/base'
import { toUserFacingMessage } from '../utils/userFacingError'
import { pageFeedback } from '../utils/pageFeedback'
import { compactReportChainLine } from '../utils/inferenceChainLabels'
import {
  readDemoMode,
  exitDemoMode,
  activateDemoModeFromRouteQuery,
  stripDemoQueryKeys,
} from '../utils/demoMode'
import { TRAINING_FOCUS_LABEL, SCORE_DIM_SHORT, DEFENSE_FLOW_OVERVIEW, SECTION } from '../constants/productTerms'
import { PAGE_LOADING, PAGE_ERROR_ALERT_TITLE } from '../constants/pageStatusCopy'
import {
  CURRENT_SESSION_ID_KEY,
  TRAINING_RUNTIME_SNAPSHOT_KEY,
  TRAINING_FOCUS_HANDOFF_KEY,
  persistCurrentSessionId,
} from '../utils/appPreferences'
import {
  getSessionResultRow,
  resolveAudioMetricsFromSession,
  resolveVisionMetricsFromSession,
  resolveLongSessionSummaryFromSession,
  formatSessionMetricCell,
} from '../utils/sessionResultMetrics'
import { readUserScopedItem, writeUserScopedItem, removeUserScopedItem } from '../utils/userScopedStorage'

const route = useRoute()
const router = useRouter()
const appDisplayName = inject('appDisplayName', null)

const reportDemoState = ref(readDemoMode())
/** 屏幕默认折叠的补充说明；打印态由 .report-print-hidden 整段隐藏 */
const reportModalityCollapse = ref([])
const reportCognitiveCollapse = ref([])
const reportLongSessionCollapse = ref([])
const reportInferenceCollapse = ref([])
const reportAppendixCollapse = ref([])

function refreshReportDemoState() {
  reportDemoState.value = readDemoMode()
}

/** 内容补充分解：空对象或字段全为 0/null 视为无有效数据 */
function contentBreakdownHasMeaningful(b) {
  if (!b || typeof b !== 'object') return false
  if (b.title_hit === true || b.outline_hit === true) return true
  const keys = ['match_score', 'keyword_coverage', 'document_quality', 'final_content_score']
  for (const k of keys) {
    const v = b[k]
    if (v == null || v === '') continue
    const n = Number(v)
    if (Number.isFinite(n) && n !== 0) return true
  }
  return false
}

function numOrUndef(v) {
  if (v == null || v === '') return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

function exitReportDemoMode() {
  exitDemoMode()
  refreshReportDemoState()
}
const loading = ref(false)
/** 与 Result.fetchResult 同类次：避免并发 loadReport 互相清空数据与卡死 skeleton */
const reportFetchGen = ref(0)
const errorMessage = ref('')
const reportData = ref(null)
/** 旧记录无 inference_chain_snapshot 时，用当前 provider-status 作比赛说明兜底 */
const reportProviderFallback = ref(null)

const reportInferenceChainLine = computed(() => {
  const snap = reportData.value?.inference_chain_snapshot
  if (snap && typeof snap === 'object') return compactReportChainLine(snap)
  const fb = reportProviderFallback.value
  if (fb && typeof fb === 'object') {
    return `${compactReportChainLine(fb)}（本报告未附带训练当时的链路快照，以上为当前系统配置，仅供现场说明。）`
  }
  return ''
})

const reportTrainingInvalid = computed(() => reportData.value?.training_valid === false)

/** 与 Result 一致：query/params 可能是 string | string[] */
function normalizeId(val) {
  if (val == null) return ''
  if (Array.isArray(val)) return normalizeId(val[0])
  return String(val).trim()
}

/**
 * 与 Result 一致：params.sessionId → query.session_id → query.sessionId → localStorage
 */
const resolvedSessionId = computed(() => {
  const p = normalizeId(route.params.sessionId)
  if (p) return p
  const q1 = normalizeId(route.query.session_id)
  if (q1) return q1
  const q2 = normalizeId(route.query.sessionId)
  if (q2) return q2
  return normalizeId(readUserScopedItem(localStorage, CURRENT_SESSION_ID_KEY))
})

const reportInvalidTrainingExplainLine = computed(() => {
  const parts = []
  const r = String(reportData.value?.invalid_reason_summary || '').trim()
  if (r) parts.push(`主要原因：${r}。`)
  parts.push('建议先检查麦克风、摄像头与训练环境后，再完成一次完整训练；下方分数仅供参考。')
  return parts.join('')
})

const sessionId = computed(() => resolvedSessionId.value || '')

const showPreflightOkLine = computed(() => {
  const sid = String(sessionId.value || '').trim()
  if (!sid) return false
  try {
    return readUserScopedItem(localStorage, `mianshi_preflight_ok_${sid}`) === '1'
  } catch {
    return false
  }
})

function followupDirectionLabel(source) {
  const s = String(source || '').trim()
  if (s === 'qa_weak_point') return '追问方向：回答薄弱点'
  if (s === 'content_gap') return '追问方向：内容缺口'
  if (s === 'outline_gap') return '追问方向：大纲延展'
  return ''
}

/** 与 Result/Training 一致：追问轮 taxonomy（优先 qa_result.followup_*） */
function resolveFollowupTaxonomyShortLabel(qr) {
  if (!qr || typeof qr !== 'object') return '规则追问'
  const kind = String(qr.followup_provider_kind || 'rule').toLowerCase()
  const fb = qr.followup_fallback_to_rule === true
  if (kind === 'hybrid' && fb) return '混合追问（已回退规则）'
  if (kind === 'hybrid') return '混合追问'
  if (kind === 'model') return '模型追问'
  return '规则追问'
}

const shortSessionDisplay = computed(() => {
  const s = reportData.value?.session_id || sessionId.value
  if (!s) return '—'
  return s.length > 14 ? `${s.slice(0, 8)}…${s.slice(-4)}` : s
})

const reportPrintDisplayName = computed(() => {
  const v = appDisplayName?.value
  if (typeof v === 'string' && v.trim()) return v.trim()
  return '—'
})

const formattedReportTime = computed(() => {
  const raw = reportData.value?.basic_info?.timestamp || reportData.value?.timestamp || ''
  if (!raw) return '—'
  try {
    const d = new Date(raw)
    if (!Number.isNaN(d.getTime())) return d.toLocaleString()
  } catch (_) {}
  return String(raw)
})

const safeBasicInfo = computed(() => reportData.value?.basic_info || null)
const safeScores = computed(() => reportData.value?.scores || null)
const isInterviewProfile = computed(() => {
  const p = String(reportData.value?.scoring_profile || 'defense').trim().toLowerCase()
  return p === 'interview'
})
const safeContentScoreRaw = computed(() => {
  const fromScores = safeScores.value?.content_score
  if (fromScores != null && fromScores !== '') return fromScores
  const top = reportData.value?.content_score
  if (top != null && top !== '') return top
  return null
})
const safeScoringProfile = computed(() => reportData.value?.scoring_profile || 'defense')
const safeScoringProfileLabel = computed(() => {
  if (reportData.value?.scoring_profile_label) return reportData.value.scoring_profile_label
  return safeScoringProfile.value === 'interview' ? '面试模式' : '答辩模式'
})

const sessionRoundTrainingFocusLabel = computed(() => {
  const k = String(reportData.value?.training_focus || 'none').trim().toLowerCase()
  const key =
    k === 'language' || k === 'posture' || k === 'qa' || k === 'content' || k === 'none' ? k : 'none'
  return TRAINING_FOCUS_LABEL[key] || TRAINING_FOCUS_LABEL.none
})

const reportFocusTrendLine = computed(() => {
  const tf = String(reportData.value?.training_focus || 'none').trim().toLowerCase()
  if (tf === 'none') return ''
  const t = reportData.value?.training_focus_trend
  return typeof t === 'string' && t.trim() ? t.trim() : ''
})

const reportFocusOutcomeVisible = computed(() => {
  const tf = String(reportData.value?.training_focus || 'none').trim().toLowerCase()
  return tf !== 'none'
})

const reportPrimaryFocusScore = computed(() => {
  const tf = String(reportData.value?.training_focus || 'none').trim().toLowerCase()
  if (tf === 'none') return ''
  const raw = reportData.value?.training_focus_primary_score
  if (raw == null || raw === '') return ''
  const n = Number(raw)
  if (!Number.isFinite(n)) return ''
  const lab = SCORE_DIM_SHORT[tf] || '专项'
  return `${lab}核心分 ${n.toFixed(1)} 分`
})

const reportFocusVsRecentLine = computed(() => {
  const v = reportData.value?.training_focus_vs_recent
  const s = typeof v === 'string' ? v.trim() : ''
  return s || '—'
})

const reportFocusNextLabelLine = computed(() => {
  const v =
    reportData.value?.training_focus_next_action_label || reportData.value?.training_focus_next_hint
  const s = typeof v === 'string' ? v.trim() : ''
  return s || '—'
})

const reportFocusMetricBlockVisible = computed(() => {
  const tf = String(reportData.value?.training_focus || 'none').trim().toLowerCase()
  return tf !== 'none'
})

const reportFocusMetricHighlights = computed(() => {
  const raw = reportData.value?.training_focus_metric_highlights
  if (!Array.isArray(raw)) return []
  return raw.map((x) => String(x || '').trim()).filter(Boolean)
})

const reportFocusMetricLead = computed(() => {
  const c = reportData.value?.training_focus_metric_compare
  if (typeof c !== 'string' || !c.trim()) return ''
  const t = c.trim()
  if (t === '暂无足够同专项对比数据') return ''
  const hi = reportFocusMetricHighlights.value
  if (hi.length && t === hi[0]) return ''
  return t
})

const safeTotalScore = computed(() => {
  const t = reportData.value?.total_score
  if (t != null && t !== '') return t
  return safeBasicInfo.value?.total_score
})

const safeMetrics = computed(() => (Array.isArray(reportData.value?.metrics) ? reportData.value.metrics : []))
const safeSummary = computed(() => reportData.value?.summary || null)
const defenseMaterialMode = computed(() =>
  reportData.value?.defense_material_mode === 'without_ppt' ? 'without_ppt' : 'with_ppt'
)
const isWithoutPptDefense = computed(() => defenseMaterialMode.value === 'without_ppt')
const safePptMatch = computed(() => {
  const m = reportData.value?.ppt_match
  if (m == null || typeof m !== 'object') return null
  const keys = Object.keys(m).filter((k) => {
    const v = m[k]
    if (v == null || v === '') return false
    if (Array.isArray(v)) return v.length > 0
    return true
  })
  if (!keys.length) return null
  return m
})
const resolvedPptMatchSource = computed(() => {
  const nested = safePptMatch.value?.match_source
  const top = reportData.value?.ppt_match_source
  if (typeof nested === 'string' && nested.trim()) return nested.trim()
  return String(top || '').trim()
})
const pptMatchSourceLine = computed(() => {
  const s = resolvedPptMatchSource.value
  if (s === 'auto_guess') return '自动猜页'
  if (s === 'manual') return '手动匹配'
  return ''
})
const isAutoGuessPptSource = computed(() => resolvedPptMatchSource.value === 'auto_guess')
const qaSourceLine = computed(() => {
  const qr = reportData.value?.qa_result
  const top = reportData.value?.qa_source
  const nested = qr?.qa_source
  const s = (top || nested || '').trim()
  if (s === 'auto_generated') {
    const k = String(qr?.question_provider_kind || 'rule').toLowerCase()
    const fb = qr?.question_fallback_to_rule === true
    const qgm = qr?.question_generation_meta
    const fb2 = fb || (qgm && qgm.fallback_to_rule === true)
    if (k === 'hybrid' && fb2) return '自动生成问题（混合首问·已回退规则）'
    if (k === 'hybrid') return '自动生成问题（混合首问）'
    if (k === 'model') return '自动生成问题（模型首问）'
    return '自动生成问题（规则首问）'
  }
  if (s === 'manual') {
    const k = String(qr?.question_provider_kind || 'rule').toLowerCase()
    const fb = qr?.question_fallback_to_rule === true
    const qgm = qr?.question_generation_meta
    const fb2 = fb || (qgm && qgm.fallback_to_rule === true)
    if (k === 'hybrid' && fb2) return '手动单题（混合首问·已回退规则）'
    if (k === 'hybrid') return '手动单题（混合首问）'
    if (k === 'model') return '手动单题（模型首问）'
    return '手动单题（规则首问）'
  }
  if (s === 'followup_generated') {
    return `弱点驱动追问 · ${resolveFollowupTaxonomyShortLabel(qr)}`
  }
  return ''
})
const safePptAnalysis = computed(() => reportData.value?.ppt_match_analysis || null)
const safeQaResult = computed(() => reportData.value?.qa_result || null)
const safeSuggestions = computed(() => (Array.isArray(reportData.value?.suggestions) ? reportData.value.suggestions : []))
const safeScoreExplanations = computed(() => reportData.value?.score_explanations || {})
const safeContentBreakdown = computed(() => reportData.value?.content_breakdown || null)

const contentBreakdownLines = computed(() => {
  if (isWithoutPptDefense.value) {
    return [
      '本轮未进行课件页面对齐与关键词匹配（无课件答辩模式）。',
      '内容分项未参与统一评分权重；语言、仪态、问答等模块仍按既有规则计入总分。',
    ]
  }
  const b = safeContentBreakdown.value
  if (!b || typeof b !== 'object') return []
  if (!contentBreakdownHasMeaningful(b)) return []
  const fmt = (v) => {
    if (v === null || v === undefined || v === '') return '—'
    const n = Number(v)
    return Number.isFinite(n) ? n.toFixed(1) : String(v)
  }
  return [
    `当前页匹配（指标）：${fmt(b.match_score)}`,
    `关键词覆盖：${b.keyword_coverage != null && b.keyword_coverage !== '' ? `${fmt(b.keyword_coverage)}%` : '—'}`,
    `命中当前页标题：${b.title_hit ? '是' : '否'}；命中大纲/他页标题：${b.outline_hit ? '是' : '否'}`,
    ...(b.document_quality != null && b.document_quality !== ''
      ? [`文档结构质量（规则）：${fmt(b.document_quality)}`]
      : []),
    ...(b.final_content_score != null && b.final_content_score !== ''
      ? [`内容模块折算分：${fmt(b.final_content_score)}`]
      : []),
  ]
})

const safeQaBreakdown = computed(() => reportData.value?.qa_breakdown || null)

const safeFollowupQuestions = computed(() => {
  const r = reportData.value?.followup_questions
  return Array.isArray(r) ? r : []
})
const safeCoachCommentary = computed(() => {
  const t = reportData.value?.coach_commentary
  return typeof t === 'string' ? t : ''
})
const safeImprovementAdvice = computed(() => {
  const r = reportData.value?.improvement_advice
  return Array.isArray(r) ? r : []
})
const safeOverallCommentary = computed(() => {
  const o = reportData.value?.overall_commentary
  if (typeof o === 'string' && o.trim()) return o.trim()
  return safeCoachCommentary.value
})

/** 报告首页「综合点评摘要」：与正文总评一致，优先 structured summary */
const reportHeroSummaryLine = computed(() => {
  const oc = safeSummary.value?.overall_comment
  if (typeof oc === 'string' && oc.trim()) return oc.trim()
  const oa = safeOverallCommentary.value
  if (typeof oa === 'string' && oa.trim()) return oa.trim()
  return ''
})

const safeCoachStrengths = computed(() => {
  const r = reportData.value?.strengths
  if (!Array.isArray(r)) return []
  return r.map((x) => String(x).trim()).filter(Boolean)
})
const safeCoachWeaknesses = computed(() => {
  const r = reportData.value?.weaknesses
  if (!Array.isArray(r)) return []
  return r.map((x) => String(x).trim()).filter(Boolean)
})
const safeNextRoundAdviceDisplay = computed(() => {
  const r = reportData.value?.next_round_advice
  if (Array.isArray(r) && r.length) return r.map((x) => String(x).trim()).filter(Boolean)
  return safeImprovementAdvice.value
})

const _cognitiveLabelMaps = {
  question: {
    rule: '规则生成',
    model: '模型生成（预留）',
    hybrid: '混合生成（预留）',
  },
  followup: {
    rule: '规则追问',
    model: '模型追问',
    hybrid: '混合追问',
  },
  commentary: {
    rule: '规则点评',
    model: '模型点评（预留）',
    hybrid: '混合点评（预留）',
  },
}

function _cognitiveLineLabel(cap, kind) {
  const k = String(kind || 'rule').trim().toLowerCase()
  const m = _cognitiveLabelMaps[cap] || {}
  return m[k] || m.rule || '规则生成'
}

const cognitiveProviderDisplay = computed(() => {
  const row = reportData.value
  const md = row?.coach_metadata
  const gp = md?.generation_providers
  const qk = row?.question_provider_kind || md?.question_provider_kind || 'rule'
  const ck = row?.commentary_provider_kind || md?.commentary_provider_kind || 'rule'
  const qr = row?.qa_result
  const qsrc = String(qr?.qa_source || row?.qa_source || '').trim()
  let followupLine = _cognitiveLineLabel('followup', row?.followup_provider_kind || md?.followup_provider_kind || 'rule')
  if (qsrc === 'followup_generated') {
    followupLine = resolveFollowupTaxonomyShortLabel(qr)
  } else {
    followupLine =
      gp?.followup?.provider_label ||
      _cognitiveLineLabel('followup', row?.followup_provider_kind || md?.followup_provider_kind || 'rule')
  }
  const ccom = row?.commentary_generation_meta || md?.commentary_generation_meta
  const qgm = qr?.question_generation_meta
  let questionLine = gp?.question?.provider_label || _cognitiveLineLabel('question', qk)
  if (qsrc === 'auto_generated' || qsrc === 'manual') {
    const k = String(qr?.question_provider_kind || row?.question_provider_kind || qk).toLowerCase()
    const fb = qr?.question_fallback_to_rule === true || (qgm && qgm.fallback_to_rule === true)
    if (k === 'hybrid' && fb) questionLine = '混合首问（已回退规则）'
    else if (k === 'hybrid') questionLine = '混合首问'
    else if (k === 'model') questionLine = '模型首问'
    else questionLine = '规则首问'
  }
  let commentaryLine =
    gp?.commentary?.provider_label || _cognitiveLineLabel('commentary', ck)
  if (ccom && typeof ccom === 'object') {
    const k = String(row?.commentary_provider_kind || ccom.provider_kind || ck).toLowerCase()
    const fb = row?.commentary_fallback_to_rule === true || ccom.fallback_to_rule === true
    if (k === 'hybrid' && fb) commentaryLine = '混合点评（已回退规则）'
    else if (k === 'hybrid') commentaryLine = '混合点评'
    else if (k === 'model') commentaryLine = '模型点评'
    else commentaryLine = '规则点评'
  }
  return {
    question: questionLine,
    followup: followupLine,
    commentary: commentaryLine,
  }
})

const qaBreakdownLines = computed(() => {
  const b = safeQaBreakdown.value
  if (!b || typeof b !== 'object') return []
  const fmt = (v) => {
    if (v === null || v === undefined || v === '') return '—'
    const n = Number(v)
    return Number.isFinite(n) ? n.toFixed(1) : String(v)
  }
  const r = Number(b.coverage_score)
  let covLabel = '—'
  if (Number.isFinite(r)) {
    const pct = r <= 1 ? r * 100 : r
    covLabel = `${pct.toFixed(1)}%`
  }
  return [
    `是否切题：${b.is_relevant === true ? '是' : b.is_relevant === false ? '否' : '—'}`,
    `关键词覆盖（参考）：${covLabel}`,
    `命中关键词数：${b.hit_keyword_count ?? '—'}；缺失数：${b.missing_keyword_count ?? '—'}`,
    `回答信息量（规则）：${fmt(b.answer_information_level)}（约 ${b.answer_length ?? '—'} 字）`,
    `表达清晰度（规则）：${fmt(b.clarity_score)}`,
    ...(b.final_qa_score != null && b.final_qa_score !== ''
      ? [`问答模块折算分：${fmt(b.final_qa_score)}`]
      : []),
  ]
})

const safeModalityValidity = computed(() => reportData.value?.modality_validity || {})
/** 与 Result 同口径：模块有效且能解析出来源时才展示 */
const showPptReportSectionSource = computed(
  () =>
    Boolean(pptMatchSourceLine.value) &&
    (safeModalityValidity.value?.content === true || isAutoGuessPptSource.value)
)
const showQaReportSectionSource = computed(
  () => safeModalityValidity.value?.qa === true && Boolean(qaSourceLine.value)
)

/** 与 Result 同口径：自动生成题 / 追问 + 答辩模式 */
const showDefenseSequentialFlowHint = computed(() => {
  if (!showQaReportSectionSource.value || !safeQaResult.value) return false
  const qs = (
    reportData.value?.qa_source ||
    safeQaResult.value?.qa_source ||
    ''
  ).trim()
  if (qs !== 'auto_generated' && qs !== 'followup_generated') return false
  const sp = String(reportData.value?.scoring_profile || 'defense').trim()
  return sp !== 'interview'
})

const safeAudioAnalysis = computed(() => reportData.value?.audio_analysis || null)
const safeVisionAnalysis = computed(() => reportData.value?.vision_analysis || null)

const currentSessionResultRow = computed(() => getSessionResultRow(reportData.value))
const resolvedAudioMetrics = computed(() => resolveAudioMetricsFromSession(currentSessionResultRow.value))
const resolvedVisionMetrics = computed(() => resolveVisionMetricsFromSession(currentSessionResultRow.value))
const resolvedLongSessionSummary = computed(() => resolveLongSessionSummaryFromSession(currentSessionResultRow.value))

/** 打印留档：无有效数据时不展开大段 0/空表，仅保留一句结论 */
const reportPrintLanguageHasDetail = computed(() => resolvedAudioMetrics.value.audio_valid !== false)
const reportPrintLanguageShort = computed(
  () => '本轮未形成有效语言/语音数据，不提供转写与语速类指标明细。',
)

const reportPrintPostureHasDetail = computed(() => resolvedVisionMetrics.value.vision_valid !== false)
const reportPrintPostureShort = computed(() => {
  const m = resolvedVisionMetrics.value.vision_message
  if (typeof m === 'string' && m.trim()) return m.trim()
  return '本轮未形成有效仪态/视觉数据。'
})

const reportPrintContentHasDetail = computed(() => safeModalityValidity.value.content === true)
const reportPrintContentShort = computed(() => {
  if (isWithoutPptDefense.value) return '本轮为无课件答辩训练，未启用课件内容匹配。'
  return '本轮未形成有效课件内容匹配。'
})

const reportPrintQaHasDetail = computed(
  () => safeModalityValidity.value.qa === true && Boolean(safeQaResult.value),
)
const reportPrintQaShort = computed(() => '本轮未形成有效问答评估数据。')

const audioSectionIntro = computed(() => {
  if (resolvedAudioMetrics.value.audio_valid === false) {
    return '本轮语言模块未获得有效结果：常见于环境过静、时长过短或识别不稳定。下列转写与指标不视为可靠评分依据，可在安静环境下重新录制后重试。'
  }
  return '本轮语言模块有效：以下为转写与语言相关指标。'
})

const visionSectionIntro = computed(() => {
  if (resolvedVisionMetrics.value.vision_valid === false) {
    return '本轮仪态（视觉）模块未获得有效结果：例如画面中人体区域不足、光线或角度导致检测不稳。下列不展示可采信仪态数值为正常；请调整机位与光线后重试。'
  }
  return '本轮仪态（视觉）模块有效：以下为视觉侧指标摘要。'
})

const modalityNarrative = computed(() => {
  const m = safeModalityValidity.value
  const tri = (v, okText, badText, neutralText) => {
    if (v === false) return badText
    if (v === true) return okText
    return neutralText
  }
  return {
    language: tri(
      m.language,
      '语言（语音）：本轮已正常采集并参与评分。',
      '语言（语音）：本轮未能得到可用的语音分析结果，该项未按有效数据计分。',
      '语言（语音）：请结合上方「统一评分说明」理解本轮计分口径。'
    ),
    posture: tri(
      m.posture,
      '仪态（视觉）：本轮已正常采集并参与评分。',
      '仪态（视觉）：本轮未能得到稳定的视觉仪态结果，该项未按有效数据计分。',
      '仪态（视觉）：请结合上方「统一评分说明」理解本轮计分口径。'
    ),
    content: (() => {
      if (m.content === true) {
        return '内容（幻灯片对齐）：本轮已进行内容匹配并参与评分。'
      }
      if (isWithoutPptDefense.value) {
        return '内容（幻灯片对齐）：本轮为无课件答辩训练，未启用课件内容匹配；系统聚焦语言、仪态、问答与老师点评。'
      }
      return tri(
        m.content,
        '内容（幻灯片对齐）：本轮已进行内容匹配并参与评分。',
        '内容（幻灯片对齐）：本轮未进行内容匹配，或未提供可对齐的讲解材料。',
        '内容（幻灯片对齐）：请结合上方「统一评分说明」理解本轮是否纳入内容项。'
      )
    })(),
    qa: tri(
      m.qa,
      '问答：本轮已进行问答评估并参与评分。',
      '问答：本轮未进行问答评估。',
      '问答：请结合上方「统一评分说明」理解本轮是否纳入问答项。'
    ),
  }
})

const hasPptMatchAnalysis = computed(() => {
  const a = safePptAnalysis.value
  return a && typeof a === 'object' && Object.keys(a).length > 0
})

/** 有单页 ppt_match 但无整册分析：不误判为未上传材料 */
const hasContentOnlyPptMatchCard = computed(() => {
  const m = safePptMatch.value
  if (!m || typeof m !== 'object') return false
  if (m.page_index == null || m.page_index === '') return false
  return !hasPptMatchAnalysis.value
})

const hasReportableContentAnalysis = computed(() => {
  if (isWithoutPptDefense.value) return false
  if (hasPptMatchAnalysis.value) return true
  if (hasContentOnlyPptMatchCard.value) return true
  if (contentBreakdownHasMeaningful(safeContentBreakdown.value)) return true
  const m = safePptMatch.value
  if (m && typeof m === 'object' && m.page_index != null && m.page_index !== '') return true
  const cs = numOrUndef(safeContentScoreRaw.value)
  if (cs != null && cs > 0) return true
  return false
})

const pptAnalysisOverall = computed(() => {
  const a = safePptAnalysis.value
  if (!a || typeof a !== 'object') return null
  const v = a.overall_match_score
  return v != null ? v : null
})

const safePptHitKeywords = computed(() =>
  (Array.isArray(safePptMatch.value?.matched_keywords) ? safePptMatch.value.matched_keywords : []).join('、') || '无'
)
const safePptMissingKeywords = computed(() =>
  (Array.isArray(safePptMatch.value?.missing_keywords) ? safePptMatch.value.missing_keywords : []).join('、') || '无'
)
const safeQaHitKeywords = computed(() =>
  (Array.isArray(safeQaResult.value?.hit_keywords) ? safeQaResult.value.hit_keywords : []).join('、') || '无'
)
const safeQaMissingKeywords = computed(() =>
  (Array.isArray(safeQaResult.value?.missing_keywords) ? safeQaResult.value.missing_keywords : []).join('、') || '无'
)

const mainRecommendationsList = computed(() => {
  const raw = reportData.value?.main_recommendations
  if (Array.isArray(raw) && raw.length) {
    return raw.map((x) => String(x ?? '').trim()).filter(Boolean)
  }
  return safeSuggestions.value
    .map((s) => {
      const c = s.content || s.text || ''
      const cat = s.category
      return cat ? `${cat}：${c}` : c
    })
    .filter(Boolean)
})

function formatScore(v) {
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  return Number.isFinite(n) ? n.toFixed(1) : String(v)
}

const displayContentScoreText = computed(() => {
  if (
    isInterviewProfile.value &&
    numOrUndef(safeContentScoreRaw.value) == null &&
    !hasReportableContentAnalysis.value
  ) {
    return '未生成'
  }
  return formatScore(safeContentScoreRaw.value)
})

function formatSessionSeconds(v) {
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  if (!Number.isFinite(n)) return String(v)
  if (n < 60) return `${n.toFixed(1)} 秒`
  const m = Math.floor(n / 60)
  const s = n - m * 60
  return `${m} 分 ${s.toFixed(0)} 秒`
}

function formatSessionInt(v) {
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  return Number.isFinite(n) ? String(Math.round(n)) : String(v)
}

function formatSampledModeLabel(mode, fps) {
  const fpsPart =
    fps != null && fps !== '' && Number.isFinite(Number(fps))
      ? `（约 ${Number(fps).toFixed(2)} fps）`
      : ''
  if (mode === true || mode === 'true' || mode === 1 || mode === '1') {
    return `已启用采样${fpsPart}`
  }
  if (mode === false || mode === 'false' || mode === 0 || mode === '0') {
    return `未标记采样 / 全量解码${fpsPart}`
  }
  if (typeof mode === 'string' && mode.trim()) {
    return fpsPart ? `${mode.trim()} ${fpsPart}` : mode.trim()
  }
  if (mode == null || mode === '') return fpsPart ? `— ${fpsPart}` : '—'
  return String(mode)
}

function moduleStatusLine(key, valid) {
  if (valid) return '本轮本项已纳入统一评分。'
  if (key === 'language') return '本轮语言模块未形成有效数据（未纳入该项评分）。'
  if (key === 'posture') return '本轮仪态模块未形成有效数据（未纳入该项评分）。'
  if (key === 'content') {
    if (reportData.value?.defense_material_mode === 'without_ppt') {
      return '本轮为无课件答辩训练，未启用课件内容匹配（未纳入该项评分）。'
    }
    const sp = String(reportData.value?.scoring_profile || 'defense').trim().toLowerCase()
    const cs = numOrUndef(
      reportData.value?.content_score ?? reportData.value?.scores?.content_score
    )
    if (sp === 'interview' && cs == null) {
      return '本轮未生成课件内容匹配分析；上传 PPT 并完成讲解后可获得该项评估（面试模式下此项为可选）。'
    }
    return '本轮未进行内容匹配（未纳入该项评分）。'
  }
  if (key === 'qa') return '本轮未进行问答评估（未纳入该项评分）。'
  return '本轮本项未纳入统一评分。'
}

const normalizeExplanation = (expl) => {
  if (typeof expl === 'string') {
    const text = expl.trim()
    return {
      summary: text || '暂无进一步说明。',
      items: text ? [text] : [],
    }
  }
  if (Array.isArray(expl)) {
    const items = expl.map((item) => String(item ?? '').trim()).filter(Boolean)
    return {
      summary: items[0] || '暂无进一步说明。',
      items,
    }
  }
  if (expl && typeof expl === 'object') {
    const summary = typeof expl.summary === 'string' ? expl.summary.trim() : ''
    const items = Array.isArray(expl.items)
      ? expl.items.map((item) => String(item ?? '').trim()).filter(Boolean)
      : []
    const mergedSummary = summary || items[0] || '暂无进一步说明。'
    return {
      summary: mergedSummary,
      items,
    }
  }
  return {
    summary: '暂无进一步说明。',
    items: [],
  }
}

const scoreExplanationCards = computed(() => {
  const explanations = safeScoreExplanations.value || {}
  const contentOptionalMissing =
    isInterviewProfile.value &&
    numOrUndef(safeContentScoreRaw.value) == null &&
    !hasReportableContentAnalysis.value
  const contentScoreDisplay = contentOptionalMissing
    ? '未生成'
    : formatScore(safeContentScoreRaw.value)
  return [
    {
      key: 'language',
      label: TRAINING_FOCUS_LABEL.language,
      score: safeScores.value?.language_score ?? '—',
      scoreDisplay: formatScore(safeScores.value?.language_score),
      contentOptionalMissing: false,
      valid: safeModalityValidity.value.language !== false,
      explanation: normalizeExplanation(explanations.language),
    },
    {
      key: 'posture',
      label: TRAINING_FOCUS_LABEL.posture,
      score: safeScores.value?.posture_score ?? '—',
      scoreDisplay: formatScore(safeScores.value?.posture_score),
      contentOptionalMissing: false,
      valid: safeModalityValidity.value.posture !== false,
      explanation: normalizeExplanation(explanations.posture),
    },
    {
      key: 'content',
      label:
        isWithoutPptDefense.value && safeModalityValidity.value.content !== true
          ? '内容专项（未启用）'
          : TRAINING_FOCUS_LABEL.content,
      score: safeContentScoreRaw.value ?? '—',
      scoreDisplay: contentScoreDisplay,
      contentOptionalMissing,
      valid: safeModalityValidity.value.content === true,
      explanation: normalizeExplanation(explanations.content),
    },
    {
      key: 'qa',
      label: TRAINING_FOCUS_LABEL.qa,
      score: safeScores.value?.qa_score ?? '—',
      scoreDisplay: formatScore(safeScores.value?.qa_score),
      contentOptionalMissing: false,
      valid: safeModalityValidity.value.qa === true,
      explanation: normalizeExplanation(explanations.qa),
    },
  ]
})

const totalExplanation = computed(() => normalizeExplanation(safeScoreExplanations.value?.total))

const loadReport = async (id) => {
  if (!id) {
    reportData.value = null
    errorMessage.value = ''
    loading.value = false
    return
  }

  const myGen = ++reportFetchGen.value
  refreshReportDemoState()

  loading.value = true
  errorMessage.value = ''
  reportData.value = null
  reportProviderFallback.value = null
  try {
    const response = await getJson(`/report/${id}`)
    if (myGen === reportFetchGen.value) {
      reportData.value = response
    }
    if (myGen !== reportFetchGen.value) return
    if (!response?.inference_chain_snapshot) {
      try {
        reportProviderFallback.value = await getJson('/system/provider-status')
      } catch (_) {
        reportProviderFallback.value = null
      }
    }
    try {
      const rawSnap = readUserScopedItem(localStorage, TRAINING_RUNTIME_SNAPSHOT_KEY)
      if (rawSnap) {
        const o = JSON.parse(rawSnap)
        if (o && o.session_id === id) {
          removeUserScopedItem(localStorage, TRAINING_RUNTIME_SNAPSHOT_KEY, undefined, true)
          console.log('[Report] cleared training runtime snapshot for session', id)
        }
      }
    } catch (_) {}
    const tfR = String(response?.training_focus || 'none').trim().toLowerCase()
    if (tfR !== 'none') {
      console.log('[Report.focus.summary] vs_recent=', response?.training_focus_vs_recent)
      console.log('[Report.focus.summary] next_action=', response?.training_focus_next_action)
    }
    console.log('[Report] defense_material_mode=', response?.defense_material_mode)
    console.debug(
      '[Report] debug ppt_match=',
      response?.ppt_match,
      'ppt_match_source=',
      response?.ppt_match_source,
      'content_breakdown=',
      response?.content_breakdown
    )
    console.log('[Report] audio_session_summary', response?.audio_session_summary)
    console.log('resultData.vision_session_summary', reportData.value?.vision_session_summary)
    console.log('[Report] resultData.vision_analysis', response?.vision_analysis)
  } catch (e) {
    if (myGen === reportFetchGen.value) {
      errorMessage.value = toUserFacingMessage(
        e,
        '暂时无法获取本页报告，或该条不属于当前账号。请稍后重试，或从结果、历史页打开本账号记录。'
      )
    }
  } finally {
    if (myGen === reportFetchGen.value) {
      loading.value = false
    }
  }
}

function retryLoadReport() {
  console.log('[Report.load] retry=', true)
  const id = sessionId.value
  if (id) loadReport(id)
}

function goHomeFromReport() {
  router.push('/home')
}

function goTrainingFromReport() {
  router.push('/training')
}

function goHistoryFromReport() {
  router.push('/history')
}

watch(loading, (v) => {
  console.log('[Report.load] loading=', v)
})

watch(errorMessage, (m) => {
  if (m) console.log('[Report.load] error=', m)
})

watch(
  () => resolvedSessionId.value,
  (id) => {
    if (id) persistCurrentSessionId(id)
    loadReport(id)
  },
  { immediate: true }
)

onMounted(() => {
  if (activateDemoModeFromRouteQuery(route.query)) {
    refreshReportDemoState()
    const q = stripDemoQueryKeys({ ...route.query })
    if (JSON.stringify(q) !== JSON.stringify(route.query)) {
      router.replace({ path: route.path, query: q })
    }
  } else {
    refreshReportDemoState()
  }
  console.log('[Report.demo_mode] active=', reportDemoState.value.active)
})

watch(
  reportData,
  (row) => {
    const qr = row?.qa_result
    if (!row || !qr || String(qr.qa_source || '').trim() !== 'followup_generated') return
    console.log('[Report.followup.source] qa_result=', qr)
    console.log('[Report.followup.source] provider_kind=', qr?.followup_provider_kind)
    console.log('[Report.followup.source] fallback_to_rule=', qr?.followup_fallback_to_rule)
    console.log('[Report.followup.source] final label=', resolveFollowupTaxonomyShortLabel(qr))
  },
  { deep: true }
)

function logReportAction(action) {
  console.log('[Report.action] action=', action)
}

function normalizeReportTrainingFocusKey(raw) {
  const k = String(raw || '').trim().toLowerCase()
  if (k === 'language' || k === 'posture' || k === 'qa' || k === 'content') return k
  return null
}

function inferWeakestReportFocus() {
  const r = reportData.value
  if (!r) return 'language'
  const pairs = [
    ['language', numOrUndef(r.language_score)],
    ['posture', numOrUndef(r.posture_score)],
    ['content', numOrUndef(r.content_score)],
    ['qa', numOrUndef(r.qa_score)],
  ].filter(([, v]) => v != null)
  if (!pairs.length) return 'language'
  pairs.sort((a, b) => a[1] - b[1])
  return pairs[0][0]
}

function reportRoundScoringProfile() {
  const p = String(reportData.value?.scoring_profile || 'defense').trim() || 'defense'
  return p.toLowerCase() === 'interview' ? 'interview' : 'defense'
}

function reportRoundDefenseMaterialMode() {
  return String(reportData.value?.defense_material_mode || 'with_ppt').trim().toLowerCase() === 'without_ppt'
    ? 'without_ppt'
    : 'with_ppt'
}

function reportClosureGoHome() {
  const sid = String(sessionId.value || '').trim()
  if (!sid || !reportData.value) {
    pageFeedback(
      'Report',
      'go_home',
      '报告尚未就绪或缺少会话信息，请稍后重试，或从历史页重新打开。',
      'warning'
    )
    return
  }
  logReportAction('go_home')
  pageFeedback('Report', 'go_home', '正在返回首页，可在首页继续训练并查看学习概况。', 'success')
  router.push({
    path: '/home',
    query: {
      last_completed_session_id: sid,
      entry_source: 'report',
    },
  })
}

function reportClosureTrainRecommended() {
  if (!reportData.value) {
    pageFeedback('Report', 'train_recommended', '报告还在加载，请稍候再试。', 'warning')
    return
  }
  logReportAction('train_recommended')
  if (reportTrainingInvalid.value) {
    pageFeedback(
      'Report',
      'train_recommended',
      '本轮未纳入统计：仍会按建议专项打开训练页；建议下一轮先检查设备与环境。',
      'warning'
    )
  } else {
    pageFeedback(
      'Report',
      'train_recommended',
      '已按建议方向带好专项，正在打开训练页（不会自动开始训练）。',
      'success'
    )
  }
  const focus =
    normalizeReportTrainingFocusKey(reportData.value.recommended_training_focus) || inferWeakestReportFocus()
  const profile = reportRoundScoringProfile()
  const dm = reportRoundDefenseMaterialMode()
  try {
    writeUserScopedItem(
      sessionStorage,
      TRAINING_FOCUS_HANDOFF_KEY,
      JSON.stringify({
        recommended_focus: focus,
        scoring_profile: profile,
        defense_material_mode: dm,
        source: 'apply_recommended_focus',
        from_session_id: sessionId.value || null,
        ts: Date.now(),
      })
    )
  } catch (_) {}
  try {
    removeUserScopedItem(localStorage, TRAINING_RUNTIME_SNAPSHOT_KEY, undefined, true)
  } catch (_) {}
  router.push({
    path: '/training',
    query: {
      entry: 'report_recommended',
      recommended_focus: focus,
      scoring_profile: profile,
      defense_material_mode: dm,
    },
  })
}

function reportClosureViewHistory() {
  logReportAction('view_history')
  pageFeedback('Report', 'view_history', '正在打开历史页。', 'info')
  router.push('/history')
}

const goBack = () => {
  const sid = String(sessionId.value || '').trim()
  if (sid) {
    persistCurrentSessionId(sid)
    router.push({ name: 'Result', params: { sessionId: sid }, query: { session_id: sid } })
  } else {
    router.push({ name: 'Result' })
  }
}

const reportPrintReady = computed(() => {
  if (loading.value) return false
  if (errorMessage.value) return false
  if (!String(sessionId.value || '').trim()) return false
  if (!reportData.value) return false
  return true
})

function reportPrintBlockedReason() {
  if (loading.value) return 'loading'
  if (errorMessage.value) return 'error'
  if (!String(sessionId.value || '').trim()) return 'no_session'
  if (!reportData.value) return 'no_data'
  return ''
}

const printReport = () => {
  const ready = reportPrintReady.value
  const blocked = reportPrintBlockedReason()
  console.log('[Report.print] ready=', ready)
  if (!ready) {
    console.log('[Report.print] action=', 'blocked')
    console.log('[Report.print] blocked_reason=', blocked)
    if (blocked === 'loading') {
      pageFeedback('Report', 'print', '报告仍在加载，请稍候再试打印或导出。', 'warning')
    } else if (blocked === 'error') {
      pageFeedback('Report', 'print', '当前报告未准备好，暂无法打印。请先重试加载或返回结果页。', 'warning')
    } else {
      pageFeedback('Report', 'print', '当前没有可打印的完整报告。', 'warning')
    }
    return
  }
  console.log('[Report.print] action=', 'open_print_dialog')
  console.log('[Report.print] blocked_reason=', '')
  if (reportTrainingInvalid.value) {
    pageFeedback(
      'Report',
      'print',
      '已打开打印预览。提示：本轮未纳入统计，纸质稿中的分数与指标仅供参考，请结合现场使用。',
      'warning'
    )
  } else {
    pageFeedback('Report', 'print', '已打开打印预览，可在预览中另存为 PDF 或连接打印机。', 'info')
  }
  window.print()
}
</script>

<style scoped>
.report-page {
  padding: 0;
  color: var(--ui-text-primary);
  background: transparent;
  box-sizing: border-box;
}


.report-load-placeholder {
  margin-bottom: 20px;
}

.report-load-placeholder__label {
  margin: 0 0 6px;
  font-size: 0.95rem;
}

.report-load-placeholder__hint {
  margin: 0 0 12px;
  font-size: 0.86rem;
  line-height: 1.5;
}

.report-error-panel {
  margin-bottom: 20px;
}

.report-error-panel__body {
  margin: 0 0 12px;
  font-size: 0.9rem;
  line-height: 1.55;
}

.report-error-panel__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.report-error-panel__more {
  margin: 10px 0 0;
  font-size: 0.86rem;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.report-error-panel__more-sep {
  opacity: 0.5;
  user-select: none;
}

.report-top-actions,
.report-export-panel {
  margin-bottom: 24px;
  padding: 18px 20px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-lg);
  background: linear-gradient(180deg, var(--ui-surface-subtle) 0%, var(--ui-surface) 52%);
  box-shadow: var(--ui-shadow-card);
}

.report-export-panel--gate {
  margin-bottom: 16px;
  padding: 14px 16px;
}

.report-export-panel--gate .report-top-actions__formal {
  margin: 0;
  padding: 0;
  border-bottom: none;
}

.report-top-actions__formal {
  margin: 0 0 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--ui-border);
  text-align: left;
}

.report-formal-eyebrow {
  margin: 0 0 6px;
  font-size: 0.8rem;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ui-text-primary);
}

.report-formal-deck {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.55;
  max-width: 64rem;
}

.report-top-doc {
  width: 100%;
  max-width: 40rem;
}

@media screen {
  .report-top-actions--toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px 20px;
    padding: 12px 16px;
    margin-bottom: 16px;
  }

  .report-top-actions--toolbar .report-top-actions__formal {
    margin: 0;
    padding: 0;
    border-bottom: none;
    flex: 1 1 300px;
    min-width: 0;
  }

  .report-top-actions--toolbar .report-formal-deck--toolbar {
    max-width: none;
    font-size: 0.82rem;
    line-height: 1.45;
  }

  .report-top-actions--toolbar .report-top-doc {
    max-width: 240px;
    flex: 0 0 auto;
  }
}

.report-page-flow-foot {
  margin-top: 24px;
  padding: 18px 20px 20px;
  border-radius: var(--ui-radius-md);
  border: 1px solid var(--ui-border);
  text-align: left;
}

.report-page-flow-foot__eyebrow {
  margin: 0 0 6px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ui-text-muted, #64748b);
}

.report-page-flow-foot__title {
  margin: 0 0 8px;
  font-size: 1.02rem;
  font-weight: 700;
  color: var(--ui-text-primary);
  letter-spacing: -0.02em;
}

.report-page-flow-foot__lead {
  margin: 0 0 14px;
  font-size: 0.86rem;
  line-height: 1.55;
  max-width: 56ch;
}

.report-page-flow-foot__actions {
  margin-top: 0;
  margin-bottom: 0;
}

.report-top-card {
  padding: 16px 18px;
  border-radius: var(--ui-radius-md);
  border: 1px solid var(--ui-border);
  text-align: left;
}

.report-top-card--doc {
  background: var(--ui-surface);
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04);
}

.report-top-card--flow {
  background: var(--ui-surface-subtle);
  border-style: solid;
  border-color: var(--ui-border);
}

.report-top-card__title {
  margin: 0 0 8px;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--ui-text-primary);
  letter-spacing: -0.02em;
}

.report-top-card__title--doc {
  font-size: 1.05rem;
}

.report-top-card__title--flow {
  color: var(--ui-text-secondary);
  font-size: 0.92rem;
  font-weight: 650;
}

.report-top-card__lead {
  margin: 0 0 10px;
}

.report-top-card__hint {
  margin: 0 0 10px;
  font-size: 0.8rem;
  line-height: 1.5;
}

.report-top-card__primary {
  margin-top: 4px;
}

.report-flow-nav {
  margin-bottom: 4px;
}

.report-flow-nav--tiered {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-bottom: 0;
}

.ui-dropdown-caret {
  display: inline-block;
  margin-left: 4px;
  font-size: 0.75em;
  opacity: 0.85;
  line-height: 1;
}

.report-page-error-actions {
  align-items: center;
}

.report-flow-train {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--ui-border);
}

.report-flow-train__label {
  margin: 0 0 6px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ui-text-muted);
}

.report-flow-train__actions {
  margin-bottom: 0;
}

.report-export-panel__title {
  margin: 0 0 8px;
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--ui-text-primary);
}

.report-export-panel__lead {
  margin: 0 0 14px;
  font-size: 0.88rem;
  line-height: 1.55;
}

.report-top-card--doc .report-export-panel__lead {
  margin-bottom: 10px;
}

.report-export-panel__primary {
  margin-bottom: 0;
}

.report-top-card--flow .report-export-panel__secondary {
  margin-bottom: 0;
}

.report-export-panel__secondary {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 6px;
}

.report-top-card--flow .report-demo-continue {
  margin: 8px 0 0;
}

.report-demo-continue {
  margin: 4px 0 10px;
  padding: 12px 14px;
  background: var(--ui-accent-soft);
  border: 1px solid var(--ui-accent-muted);
  border-radius: var(--ui-radius-md);
}

.report-demo-continue__label {
  margin: 0 0 8px;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--ui-text-secondary);
}

.report-demo-continue__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.report-export-panel__closure {
  margin: 12px 0 6px;
  font-size: 0.82rem;
}

.report-top-card--flow .report-export-panel__closure-actions,
.report-export-panel__closure-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.report-print-body {
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  padding: 24px 28px;
  background: var(--ui-surface);
}

.report-hero-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: stretch;
}

.report-hero-main {
  min-width: 0;
}

.report-hero-subscores {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin: 12px 0 14px;
}

.report-hero-subscores__cell {
  text-align: center;
  padding: 8px 6px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  background: var(--ui-surface-subtle);
}

.report-hero-subscores__k {
  display: block;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ui-text-muted);
  margin-bottom: 4px;
}

.report-hero-subscores__v {
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--ui-text-primary);
  line-height: 1.2;
}

.report-hero-meta {
  margin-top: 4px;
}

.report-hero-summary {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: var(--ui-radius-md);
  border: 1px dashed var(--ui-border-strong);
  background: var(--ui-surface-subtle);
}

.report-hero-summary__text {
  margin: 6px 0 0;
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--ui-text-primary);
}

.report-hero-toolbar {
  flex-shrink: 0;
  padding: 12px 14px;
  border-radius: var(--ui-radius-md);
  border: 1px solid var(--ui-border);
  background: var(--ui-surface-subtle);
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.05);
}

.report-hero-toolbar__title {
  margin: 0 0 6px;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ui-text-muted);
}

.report-hero-toolbar__micro {
  margin: 0 0 10px;
  font-size: 0.76rem;
  line-height: 1.45;
}

.report-hero-toolbar__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.report-hero-toolbar__actions :deep(.el-button) {
  margin: 0;
}

.report-hero-toolbar__row2 {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.report-hero-toolbar__row2 :deep(.el-button) {
  margin: 0;
}

.report-hero-toolbar__more :deep(.el-button) {
  margin: 0;
}

.report-hero-toolbar__demo {
  margin-top: 10px;
}

.report-hero-toolbar__demo-line {
  margin: 0 0 8px;
  font-size: 0.8rem;
  line-height: 1.45;
}

.report-inpage-nav--report-v2 {
  flex-wrap: wrap;
  row-gap: 6px;
  margin-bottom: 4px;
  padding: 8px 10px;
  border-radius: var(--ui-radius-md);
  background: var(--ui-surface-subtle);
  border: 1px dashed var(--ui-border);
}

.report-next-preview {
  margin: 0 0 18px;
  padding: 12px 14px 14px;
  border-radius: var(--ui-radius-lg);
  border: 1px solid #a7f3d0;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, var(--ui-surface) 48%);
  box-shadow: var(--ui-shadow-card);
}

.report-next-preview__head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px 12px;
  margin-bottom: 8px;
}

.report-next-preview__title {
  margin: 0;
  font-size: 1rem;
  font-weight: 800;
  color: var(--ui-text-primary);
  letter-spacing: -0.02em;
}

.report-next-preview__jump {
  font-size: 0.86rem;
  font-weight: 600;
}

.report-screen-part .report-part-h2 {
  margin-top: 4px;
}

@media screen and (min-width: 900px) {
  .report-screen-chapter {
    position: relative;
    padding-left: 12px;
    margin-left: 2px;
    border-left: 3px solid var(--ui-accent-muted);
  }

  .report-screen-chapter.report-section--conclusion,
  .report-screen-chapter.report-section-summary {
    padding-left: 18px;
  }

  .report-screen-part {
    padding-left: 4px;
    border-left: 2px solid #e2e8f0;
    margin-left: 0;
  }
}

.report-invalid-callout {
  margin-bottom: 16px;
  padding: 12px 14px;
  border: 1px solid #fde68a;
  border-radius: var(--ui-radius-md);
  background: var(--brand-warning-soft);
}

.report-invalid-callout__title {
  display: block;
  font-size: 0.95rem;
  color: #b88230;
  margin-bottom: 6px;
}

.report-invalid-callout__body {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.55;
  color: var(--ui-text-secondary);
}

.report-export-panel__title--v1 {
  margin: 0 0 12px;
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.02em;
}

.report-doc-kicker {
  margin: 0 0 10px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ui-text-muted);
}

.report-part-h2 {
  margin: 0 0 8px;
  font-size: 1.15rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--ui-text-primary);
  border-bottom: 1px solid var(--ui-border);
  padding-bottom: 8px;
}

.report-part-lead {
  margin: 0 0 16px;
  font-size: 0.88rem;
  line-height: 1.55;
  max-width: 56ch;
}

.report-part--analysis {
  padding-top: 4px;
}

.report-part--analysis .report-part-h2 {
  margin-top: 0;
}

.report-focus-embed {
  margin-bottom: 16px;
}

.defense-flow-overview--in-analysis {
  margin: 0 0 18px;
  font-size: 0.88rem;
  line-height: 1.55;
}

.report-suggestion-block {
  margin-top: 12px;
}

.report-section--recommendations .report-suggestion-block:first-of-type {
  margin-top: 0;
}

.report-suggestion-fallback {
  margin: 12px 0 0;
  font-size: 0.9rem;
}

.report-section--conclusion {
  position: relative;
}

.report-inference-aux {
  border-top: 1px dashed var(--ui-border);
  padding-top: 10px;
  margin-top: 6px;
}

.report-header {
  border-bottom: 1px solid var(--ui-border);
  padding-bottom: 16px;
  margin-bottom: 20px;
}

.report-title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px 20px;
  margin-bottom: 10px;
}

.report-title-row .report-title {
  margin: 0;
}

.report-hero-score {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.report-hero-score__k {
  font-size: 0.9rem;
  font-weight: 600;
  color: #64748b;
}

.report-hero-score__v {
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: #0f172a;
  line-height: 1;
}

.report-header-one-liner {
  margin: 0 0 14px;
  font-size: 1rem;
  line-height: 1.55;
  color: #334155;
}

@media screen {
  .report-section--recommendations {
    padding: 16px 18px 18px;
    background: linear-gradient(180deg, rgba(16, 185, 129, 0.06) 0%, var(--ui-surface) 32%);
    border: 1px solid var(--ui-border);
    border-radius: var(--ui-radius-lg);
    box-shadow: var(--ui-shadow-card);
  }

  .report-section--conclusion,
  .report-section-summary {
    padding: 16px 18px;
    background: var(--ui-surface-subtle);
    border: 1px solid var(--ui-border);
    border-radius: var(--ui-radius-lg);
    box-shadow: var(--ui-shadow-card);
  }

  .report-teacher-panel {
    padding: 16px 18px 18px;
    background: var(--ui-surface);
    border: 1px solid var(--ui-border);
    border-radius: var(--ui-radius-lg);
    border-left: 4px solid var(--ui-accent-muted);
    box-shadow: var(--ui-shadow-card);
  }
}

.report-inference-chain {
  margin: 6px 0 0;
  font-size: 0.88rem;
  line-height: 1.5;
}

.report-title {
  margin: 0 0 16px;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--ui-text-primary);
}

.header-meta {
  display: grid;
  gap: 8px;
}

.meta-row {
  display: flex;
  gap: 12px;
  align-items: baseline;
  font-size: 0.95rem;
}

.meta-label {
  color: var(--ui-text-muted);
  min-width: 5em;
}

.meta-value {
  color: var(--ui-text-primary);
}

.meta-text-wrap {
  white-space: normal;
  line-height: 1.5;
  flex: 1;
  min-width: 0;
}

.report-focus-trend-row {
  align-items: flex-start;
}

.report-focus-outcome {
  margin-top: 4px;
  padding: 10px 12px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}

.report-focus-outcome-row {
  align-items: flex-start;
}

.report-focus-summary {
  margin: 10px 0 0;
  font-size: 0.88rem;
  line-height: 1.55;
}

.report-focus-metric-block {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #e4e7ed;
}

.report-focus-metric-title .meta-label {
  font-weight: 600;
  color: #303133;
}

.report-focus-metric-lead {
  margin: 6px 0 6px;
  font-size: 0.86rem;
  line-height: 1.55;
}

.report-focus-metric-list {
  margin: 0;
  padding-left: 1.15rem;
  font-size: 0.86rem;
  line-height: 1.55;
  color: #606266;
}

.report-focus-metric-list li {
  margin-bottom: 3px;
}

.report-focus-metric-fallback {
  margin: 4px 0 0;
  font-size: 0.86rem;
}

.meta-mono {
  font-family: ui-monospace, monospace;
  font-size: 0.88rem;
}

.meta-highlight .meta-value.score-total {
  font-size: 1.35rem;
  font-weight: 700;
}

.report-section {
  margin-bottom: 22px;
}

.report-source-line {
  font-size: 0.95rem;
  margin: 0 0 10px;
  color: #606266;
}

.explain-source-line {
  margin: 6px 0 10px;
  padding: 6px 8px;
  background: #fafafa;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.section-title {
  margin: 0 0 12px;
  font-size: 1.06rem;
  font-weight: 700;
  border-left: 3px solid var(--ui-accent);
  padding-left: 10px;
  color: var(--ui-text-primary);
  letter-spacing: -0.015em;
}

.section-title--sub {
  font-size: 0.98rem;
  font-weight: 600;
  border-left-width: 2px;
  padding-left: 8px;
  margin-top: 4px;
  color: var(--ui-text-secondary);
}

.score-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.score-cell {
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  padding: 12px;
  text-align: center;
  background: var(--ui-surface-subtle);
}

.score-name {
  font-size: 0.85rem;
  color: var(--ui-text-muted);
  margin-bottom: 6px;
}

.score-num {
  font-size: 1.2rem;
  font-weight: 600;
}

.lead {
  margin: 0 0 10px;
  line-height: 1.6;
}

.bullet-list {
  margin: 0;
  padding-left: 1.2rem;
  line-height: 1.65;
}

.bullet-list.tight {
  margin-top: 6px;
}

.bullet-list.plain {
  list-style: disc;
}

.explain-card {
  margin-top: 14px;
  padding: 12px 14px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #fafafa;
}

.explain-card--optional-skip {
  border-color: #e8eaec;
  background: #fcfcfd;
}

.explain-score--na {
  font-weight: 500;
  color: #909399;
  font-size: 0.95em;
}

.report-subscore--na {
  color: #909399;
  font-size: 0.92em;
}

.score-num--na {
  color: #909399;
  font-size: 0.98em;
}

.report-content-placeholder-note {
  margin: 10px 0 0;
  padding: 10px 12px;
  background: #f8f9fb;
  border-radius: 6px;
  border: 1px solid #eef0f3;
  line-height: 1.55;
}

.explain-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.explain-score {
  font-weight: 600;
}

.module-status {
  font-size: 0.9rem;
  color: #606266;
  margin: 0 0 8px;
}

.explain-summary {
  margin: 0 0 6px;
  line-height: 1.6;
}

.inline-label {
  display: inline-block;
  min-width: 4.5em;
  color: #909399;
  margin-right: 6px;
}

.transcript-block {
  white-space: pre-wrap;
  line-height: 1.6;
  margin: 10px 0;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 0.92rem;
}

.kv-grid {
  display: grid;
  gap: 6px;
  margin-top: 8px;
  max-width: 420px;
}

.long-session-report-lead {
  margin: 0 0 10px;
  line-height: 1.55;
}

.long-session-report-columns {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
  align-items: start;
}

.long-session-report-block .kv-grid {
  max-width: none;
}

.kv-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 0.92rem;
  border-bottom: 1px dotted #e4e7ed;
  padding-bottom: 4px;
}

.muted {
  color: #909399;
  line-height: 1.6;
  margin: 8px 0 0;
}

.content-breakdown-report {
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px dashed #e4e7ed;
}

.coach-report-section {
  border-left: 3px solid #67c23a;
  padding-left: 12px;
}

.coach-followup-report li {
  margin-bottom: 10px;
}

.coach-reason-print {
  margin-top: 4px;
  font-size: 0.92rem;
}

.coach-src-print {
  margin-top: 2px;
  font-size: 0.85rem;
}

.coach-commentary-print {
  line-height: 1.65;
  margin: 0;
}

.teacher-report-section .teacher-report-lead {
  margin-bottom: 10px;
}

.teacher-focus-context-report {
  margin: 0 0 10px;
  font-size: 0.88rem;
  line-height: 1.55;
}

.teacher-report-block {
  margin-top: 10px;
}

.teacher-report-footnote {
  margin-top: 12px;
  font-size: 0.85rem;
}

.cognitive-provider-report {
  margin: 0 0 10px;
  padding: 8px 10px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fafafa;
  font-size: 0.92rem;
}

.cognitive-provider-report p {
  margin: 4px 0;
  line-height: 1.5;
}

.metrics-appendix .metrics-lines {
  font-size: 0.88rem;
  line-height: 1.55;
}

.metrics-appendix-inner-title {
  display: none;
}

.report-tech-aux {
  margin-bottom: 14px;
}

.report-inference-aux--wrap {
  margin: 8px 0 16px;
}

.metric-line {
  padding: 2px 0;
  border-bottom: 1px solid #f0f2f5;
}

.print-avoid-break {
  break-inside: avoid;
  page-break-inside: avoid;
}

.print-break-before-appendix {
  break-before: page;
  page-break-before: always;
}

.debug-message {
  margin: 10px 0;
  padding: 12px;
  border-radius: 8px;
  text-align: center;
  font-size: 0.9em;
}

.debug-message.info {
  background: #f0f9ff;
  color: #409eff;
  border: 1px solid #d9ecff;
}

.debug-message.warning {
  background: #fdf6ec;
  color: #e6a23c;
  border: 1px solid #fcebb6;
}

.debug-message.error {
  background: #fef0f0;
  color: #f56c6c;
  border: 1px solid #fbc4c4;
}

.report-demo-mode-inline {
  margin-bottom: 12px;
}

.report-demo-mode-inline__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-top: 4px;
}

@media screen and (max-width: 1024px) {
  .report-page {
    padding: 20px 14px 36px;
  }

  .report-print-body {
    padding: 20px 18px;
  }

  .report-export-panel,
  .report-top-actions {
    padding: 16px 16px;
  }

  .report-top-doc {
    max-width: 100%;
  }
}

@media screen and (max-width: 640px) {
  .report-hero-subscores {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media screen and (min-width: 1100px) {
  .report-print-body--screen-v2 {
    padding: 26px 32px 32px;
  }
}

@media screen and (max-width: 768px) {
  .report-page {
    padding: 16px 10px 28px;
  }

  .report-print-body {
    padding: 16px 14px;
  }

  .report-title-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .report-hero-score__v {
    font-size: 1.75rem;
  }

  .score-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .score-cell {
    padding: 10px 8px;
  }

  .report-top-card__primary .el-button,
  .report-export-panel__primary .el-button {
    width: 100%;
  }

  .report-flow-nav.report-export-panel__secondary,
  .report-export-panel__secondary,
  .report-flow-nav--tiered {
    flex-direction: column;
    align-items: stretch;
  }

  .report-flow-nav.report-export-panel__secondary .el-button,
  .report-export-panel__secondary .el-button,
  .report-flow-nav--tiered .el-button,
  .report-page-flow-foot__actions :deep(.el-button) {
    width: 100%;
    margin: 0;
  }

  .report-page-flow-foot__more {
    width: 100%;
  }

  .report-page-flow-foot__more :deep(.el-button) {
    width: 100%;
  }

  .report-flow-train__actions.report-export-panel__closure-actions,
  .report-export-panel__closure-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .report-flow-train__actions .el-button,
  .report-export-panel__closure-actions .el-button {
    width: 100%;
    margin: 0;
  }

  .report-demo-continue__actions {
    flex-direction: column;
    align-items: stretch;
  }

  .report-demo-continue__actions .el-button {
    width: 100%;
  }

  .meta-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .meta-label {
    min-width: 0;
  }

  .kv-grid {
    max-width: none;
  }
}

@media screen and (max-width: 480px) {
  .score-grid {
    grid-template-columns: 1fr;
  }
}

@media screen {
  .report-page--demo-mode .report-header {
    border-bottom: 2px solid rgba(64, 158, 255, 0.3);
    padding-bottom: 18px;
  }
}

.report-inference-chain--demo-spotlight {
  font-weight: 600;
  color: #303133 !important;
}

.report-demo-muted {
  opacity: 0.66;
}

@media print {
  .no-print {
    display: none !important;
  }

  .report-print-hidden {
    display: none !important;
  }

  .report-print-hide-bullets {
    display: none !important;
  }

  .report-demo-muted,
  .cognitive-provider-report.report-demo-muted {
    opacity: 1 !important;
  }

  .report-page {
    padding: 0;
    max-width: none;
    margin: 0;
    color: #111;
    background: #fff;
  }

  .report-print-body {
    border: none;
    padding: 0;
    border-radius: 0;
    box-shadow: none;
    max-width: 100%;
  }

  .report-doc-kicker--print-cover {
    margin: 0 0 6px;
    font-size: 0.65rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #555;
  }

  .report-header {
    border-bottom: 1px solid #ccc;
    padding-bottom: 12px;
    margin-bottom: 16px;
    break-inside: avoid;
    page-break-inside: avoid;
  }

  .report-title-row {
    align-items: flex-end;
  }

  .report-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #000;
  }

  .report-hero-score__k {
    color: #444;
    font-size: 0.82rem;
  }

  .report-hero-score__v {
    font-size: 1.45rem;
    font-weight: 700;
    color: #000;
  }

  .report-hero-layout {
    display: block;
  }

  .report-hero-subscores {
    gap: 6px;
    margin: 10px 0 12px;
    break-inside: avoid;
    page-break-inside: avoid;
  }

  .report-hero-subscores__cell {
    background: #fff !important;
    border: 1px solid #d8d8d8;
    border-radius: 2px;
    padding: 6px 4px;
    box-shadow: none !important;
  }

  .report-hero-subscores__k {
    color: #555;
    font-size: 0.65rem;
  }

  .report-hero-subscores__v {
    font-size: 0.95rem;
    font-weight: 700;
    color: #000;
  }

  .report-hero-meta .meta-label {
    color: #555;
  }

  .meta-session-compact {
    font-size: 0.75rem !important;
  }

  .report-hero-summary {
    margin-top: 12px;
    padding: 10px 12px;
    border: 1px solid #ddd;
    border-radius: 2px;
    background: #fafafa !important;
    break-inside: avoid;
    page-break-inside: avoid;
  }

  .report-hero-summary__text {
    color: #222;
    font-size: 0.9rem;
  }

  .report-screen-chapter,
  .report-screen-part {
    padding-left: 0 !important;
    margin-left: 0 !important;
    border-left: none !important;
  }

  .report-part-h2 {
    font-size: 1.05rem;
    font-weight: 700;
    color: #000;
    border-bottom: 1px solid #ccc;
    break-after: avoid;
    page-break-after: avoid;
  }

  .report-section-summary,
  .report-section--conclusion,
  .report-section--recommendations,
  .report-teacher-panel {
    padding: 0 !important;
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
  }

  .report-teacher-panel {
    border-left: 1px solid #bbb !important;
    padding-left: 10px !important;
  }

  .report-section {
    margin-bottom: 12px;
  }

  .section-title {
    border-left: 2px solid #999;
    color: #000;
    font-size: 1rem;
    break-after: avoid;
    page-break-after: avoid;
  }

  .section-title--sub {
    border-left-color: #aaa;
    color: #333;
  }

  .score-grid {
    gap: 8px;
    break-inside: avoid;
    page-break-inside: avoid;
  }

  .score-cell {
    background: #fff !important;
    border: 1px solid #d8d8d8;
    border-radius: 2px;
    box-shadow: none !important;
    padding: 8px 6px;
  }

  .score-num {
    font-size: 1.05rem;
    color: #000;
  }

  .explain-card {
    background: #fff !important;
    border: 1px solid #ddd;
    border-radius: 2px;
    box-shadow: none !important;
    padding: 8px 10px;
    margin-top: 10px;
    break-inside: avoid;
    page-break-inside: avoid;
  }

  .explain-card--print-invalid {
    padding: 4px 0 !important;
    border: none !important;
    border-bottom: 1px dotted #ccc !important;
    border-radius: 0 !important;
    background: transparent !important;
    margin-top: 6px;
  }

  .explain-card--print-invalid .explain-card-head,
  .explain-card--print-invalid .explain-summary,
  .explain-card--print-invalid .report-print-hide-bullets {
    display: none !important;
  }

  .explain-card--print-invalid .module-status {
    margin: 0;
    font-size: 0.88rem;
    color: #333;
  }

  .report-focus-outcome {
    background: #fff !important;
    border: 1px solid #ddd;
    box-shadow: none !important;
  }

  .transcript-block {
    background: #f5f5f5 !important;
    border: 1px solid #e5e5e5;
    break-inside: auto;
    page-break-inside: auto;
  }

  .explain-source-line {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
  }

  .coach-report-section,
  .teacher-report-section {
    border-left-color: #999;
  }

  .report-invalid-callout {
    border: 1px solid #e0e0e0;
    background: #fafafa !important;
    break-inside: avoid;
    page-break-inside: avoid;
  }

  .report-print-module-fallback {
    margin: 6px 0 0;
    font-size: 0.9rem;
    color: #444;
  }

  .print-avoid-break {
    break-inside: avoid;
    page-break-inside: avoid;
  }

  .print-break-before-appendix {
    break-before: auto;
    page-break-before: auto;
  }

  .kv-row {
    border-bottom-color: #ddd;
  }
}
</style>

<style>
/* 打印时整页留白与对比度（非 scoped，避免打印稿像随意截图） */
@media print {
  html,
  body {
    background: #fff !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }

  .app-container {
    height: auto !important;
    min-height: 0 !important;
    width: 100% !important;
    background: #fff !important;
  }
}
</style>
