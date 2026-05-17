<template>
  <div
    class="result-page result-page--brand-v1 ui-page-frame ui-page-shell-inset"
    :class="{ 'result-page--demo-mode': demoModeUi.active }"
  >
    <header class="result-page-head">
      <h1 class="ui-page-title">训练结果</h1>
      <p class="ui-page-sub">
        首屏左栏看分数与小结，右栏选下一步；老师点评与维度复盘在下方，按需展开即可。
      </p>
    </header>

    <el-alert
      v-if="demoModeUi.active"
      class="result-demo-mode-banner no-print"
      type="success"
      :closable="false"
      show-icon
      title="演示模式"
    >
      <p class="result-demo-mode-banner__body muted">本页在演示下突出总分、点评与主操作，细则已合并到可折叠区。</p>
      <div class="result-demo-mode-banner__actions result-page-actions-row">
        <el-button size="default" type="primary" @click="exitResultDemoMode">退出演示模式</el-button>
        <el-dropdown trigger="click" class="result-page-actions-more">
          <el-button size="default" type="default" plain
            >其他
            <span class="ui-dropdown-caret" aria-hidden="true">▾</span></el-button
          >
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="goToHomeFromResult">返回首页</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-alert>

    <div v-if="loading" class="result-load-placeholder" aria-busy="true" aria-live="polite">
      <p class="result-load-placeholder__label muted">{{ PAGE_LOADING.result.label }}</p>
      <p class="result-load-placeholder__hint muted">{{ PAGE_LOADING.result.hint }}</p>
      <el-skeleton :rows="10" animated />
    </div>

    <div v-else-if="errorMessage" class="result-error-panel">
      <el-alert type="error" :closable="false" show-icon :title="PAGE_ERROR_ALERT_TITLE.result">
        <p class="result-error-panel__body">{{ errorMessage }}</p>
        <div class="result-error-panel__actions result-page-error-actions">
          <el-button type="primary" @click="retryFetchResult">重试</el-button>
          <el-dropdown trigger="click" class="result-page-actions-more">
            <el-button type="default" plain
              >其他路线
              <span class="ui-dropdown-caret" aria-hidden="true">▾</span></el-button
            >
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="goToHomeFromResult">返回首页</el-dropdown-item>
                <el-dropdown-item @click="goToHistory">查看历史</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-alert>
    </div>

    <div v-else-if="!sessionId" class="result-error-panel">
      <el-alert type="warning" :closable="false" show-icon title="暂无法从本页打开结果">
        <p class="result-error-panel__body">
          当前没有会话信息。请从训练页完成一轮后由系统进入本页，或在链接中携带本轮会话编号。
        </p>
        <div class="result-error-panel__actions result-page-error-actions">
          <el-button type="primary" @click="goToTraining">去训练</el-button>
          <el-dropdown trigger="click" class="result-page-actions-more">
            <el-button type="default" plain
              >其他路线
              <span class="ui-dropdown-caret" aria-hidden="true">▾</span></el-button
            >
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="goToHomeFromResult">返回首页</el-dropdown-item>
                <el-dropdown-item @click="goToHistory">查看历史</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-alert>
    </div>

    <div
      v-else-if="!loading && !errorMessage && sessionId && !resultData"
      class="result-error-panel"
    >
      <el-alert type="error" :closable="false" show-icon title="结果尚未加载完成">
        <p class="result-error-panel__body">
          主结果可能仍在生成中，或已被新请求覆盖。建议先重试；若仍失败，可返回首页后从历史重新打开该条记录。
        </p>
        <div class="result-error-panel__actions result-page-error-actions">
          <el-button type="primary" @click="retryFetchResult">重试</el-button>
          <el-dropdown trigger="click" class="result-page-actions-more">
            <el-button type="default" plain
              >其他路线
              <span class="ui-dropdown-caret" aria-hidden="true">▾</span></el-button
            >
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="goToHomeFromResult">返回首页</el-dropdown-item>
                <el-dropdown-item @click="goToHistory">查看历史</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-alert>
    </div>

    <div v-else-if="resultData" class="result-content">
      <el-alert
        v-if="sessionTrainingInvalid"
        type="info"
        show-icon
        :closable="false"
        class="training-invalid-banner training-invalid-banner--soft print-avoid-break"
        :title="PAGE_SOFT.trainingNotInStatsShort"
      >
        <template #default>
          <p class="training-invalid-banner__body">
            {{ invalidTrainingExplainLine }}
          </p>
        </template>
      </el-alert>

      <nav class="ui-inpage-nav result-inpage-nav no-print" aria-label="本页内容导航">
        <a class="ui-inpage-nav__link" href="#result-anchor-overview" @click="onInpageNavLinkClick">总览</a>
        <a class="ui-inpage-nav__link" href="#result-anchor-next" @click="onInpageNavLinkClick">下一步</a>
        <a class="ui-inpage-nav__link" href="#result-anchor-teacher" @click="onInpageNavLinkClick">老师点评</a>
        <a class="ui-inpage-nav__link" href="#result-anchor-details" @click="onInpageNavLinkClick">详细分析</a>
      </nav>

      <div class="ui-l-desk-2 result-hero-2col">
        <section
          id="result-anchor-overview"
          tabindex="-1"
          class="result-overview-card result-at-a-glance inpage-nav-target print-avoid-break"
          aria-label="本轮表现总览"
        >
          <header class="result-overview-card__head">
            <h2 class="result-overview-card__title">本轮结果</h2>
            <p class="result-overview-card__lead muted no-print">
              总分与四项维度得分；小结与练习提示在下方。各维度计分说明见「详细分析」折叠区。
            </p>
          </header>
          <div
            v-if="resultHistoryFetchSettled && resultCompareSummaryBlock.show"
            class="result-compare-summary no-print"
            :class="`result-compare-summary--${resultCompareSummaryBlock.tone}`"
            role="status"
            aria-label="与上一次有效训练的对比摘要"
          >
            <p class="result-compare-summary__title">{{ resultCompareSummaryBlock.titleLine }}</p>
            <p v-if="resultCompareSummaryBlock.detailLine" class="result-compare-summary__detail muted">
              {{ resultCompareSummaryBlock.detailLine }}
            </p>
          </div>
          <div class="result-overview-scoreblock">
            <div class="result-overview-total">
              <div class="result-overview-total__label">总分</div>
              <div class="result-overview-total__value">{{ formatScore(safeTotalScore) }}</div>
            </div>
            <div class="result-overview-dims" role="list">
              <div class="result-overview-dim" role="listitem">
                <div class="result-overview-dim__label">语言</div>
                <div class="result-overview-dim__value">{{ formatScore(safeLanguageScore) }}</div>
              </div>
              <div class="result-overview-dim" role="listitem">
                <div class="result-overview-dim__label">仪态</div>
                <div class="result-overview-dim__value">{{ formatScore(safePostureScore) }}</div>
              </div>
              <div class="result-overview-dim" role="listitem">
                <div class="result-overview-dim__label">内容</div>
                <div class="result-overview-dim__value">{{ formatScore(safeContentScore) }}</div>
              </div>
              <div class="result-overview-dim" role="listitem">
                <div class="result-overview-dim__label">问答</div>
                <div class="result-overview-dim__value">{{ formatScore(safeQaScore) }}</div>
              </div>
            </div>
          </div>
          <div v-if="summaryView.strongest_aspect || summaryView.weakest_aspect" class="result-overview-chiprow no-print">
            <span v-if="summaryView.strongest_aspect" class="ui-tag ui-tag--pos result-overview-chip">
              <strong>最强项</strong> {{ summaryView.strongest_aspect }}
            </span>
            <span v-if="summaryView.weakest_aspect" class="ui-tag ui-tag--warn result-overview-chip">
              <strong>待加强</strong> {{ summaryView.weakest_aspect }}
            </span>
          </div>
          <div class="result-overview-narrative">
            <p class="result-overview-overall">
              <span class="result-overview-narrative__k">总评</span>
              {{ summaryView.overall_comment || '暂无总评摘要，可结合分数与老师点评安排下一练。' }}
            </p>
            <p v-if="summaryView.training_tip" class="result-overview-tip">
              <span class="result-overview-narrative__k">练习提示</span>
              {{ summaryView.training_tip }}
            </p>
          </div>
        </section>

        <section
          id="result-anchor-next"
          tabindex="-1"
          class="result-next-panel result-primary-actions result-primary-actions--hero-dock ui-surface ui-surface--subtle ui-interactive-soft no-print inpage-nav-target"
          aria-label="下一步"
        >
          <h2 class="result-next-panel__title">下一步</h2>
          <p class="result-next-panel__advice no-print">
            建议先巩固
            <strong class="result-next-panel__emph">{{
              summaryView.weakest_aspect || '本轮最薄弱的环节'
            }}</strong>
            ，再用主按钮进入下一轮；查看正式报告、回首页或历史请用下方次要操作（均为手动跳转）。
          </p>
          <div v-if="recommendedFocusLabel" class="result-next-focus-callout no-print">
            <span class="result-next-focus-callout__k">推荐训练方向</span>
            <p class="result-next-focus-callout__v">{{ recommendedFocusLabel }}</p>
          </div>
          <div class="result-next-actions result-next-actions--stacked">
            <el-button class="result-btn-primary result-next-actions__btn" type="primary" size="large" @click="startNextRoundTraining">{{
              nextRoundPrimaryButtonLabel
            }}</el-button>
            <el-button
              class="result-btn-secondary result-next-actions__btn"
              type="primary"
              plain
              size="default"
              @click="goToReport"
              >查看训练报告</el-button
            >
            <el-dropdown trigger="click" class="result-page-actions-more result-next-actions__btn result-next-actions__more">
              <el-button class="result-btn-tertiary" type="default" plain size="default"
                >其他
                <span class="ui-dropdown-caret" aria-hidden="true">▾</span></el-button
              >
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="goToHomeFromResult">返回首页</el-dropdown-item>
                  <el-dropdown-item @click="goToHistory">查看历史</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </section>
      </div>

      <div
        id="result-anchor-teacher"
        tabindex="-1"
        class="score-card teacher-feedback-card teacher-feedback-card--prominent ui-surface result-panel--teacher result-tier-review inpage-nav-target"
      >
        <h3 class="teacher-card-main-title">老师点评与练习建议</h3>
        <p class="teacher-card-lead muted">建议通读这一段，结合分数安排下一练。内容依据本轮训练与评分规则整理，便于复盘。</p>
        <p v-if="sessionRoundTrainingFocusKey !== 'none'" class="teacher-focus-context muted">
          已结合本轮「{{ sessionRoundTrainingFocusLabel }}」及同专项历史对照做了整理，便于你专项复盘。
        </p>
        <el-collapse v-model="teacherCognitiveCollapse" class="ui-aux-collapse ui-aux-collapse--low result-teacher-cognitive-collapse no-print">
          <el-collapse-item title="各环节说明与依据（可选）" name="cog">
            <div class="cognitive-provider-strip cognitive-provider-strip--in-collapse">
              <p class="cognitive-provider-line">
                <strong>提问：</strong>{{ cognitiveProviderDisplay.question }}
              </p>
              <p class="cognitive-provider-line">
                <strong>追问：</strong>{{ cognitiveProviderDisplay.followup }}
              </p>
              <p class="cognitive-provider-line">
                <strong>点评：</strong>{{ cognitiveProviderDisplay.commentary }}
              </p>
            </div>
          </el-collapse-item>
        </el-collapse>
        <p class="teacher-overall">{{ safeOverallCommentary || '暂无单独综合点评，可先看下方分条；需要计分细节可展开「四维度与计分说明」。' }}</p>
        <div v-if="safeCoachStrengths.length" class="teacher-subsection">
          <h4 class="teacher-subtitle">本轮优点</h4>
          <ul class="explain-list teacher-bullet-list">
            <li v-for="(line, i) in safeCoachStrengths" :key="`st-${i}`">{{ line }}</li>
          </ul>
        </div>
        <div v-if="safeCoachWeaknesses.length" class="teacher-subsection">
          <h4 class="teacher-subtitle">本轮主要问题</h4>
          <ul class="explain-list teacher-bullet-list teacher-weak-list">
            <li v-for="(line, j) in safeCoachWeaknesses" :key="`wk-${j}`">{{ line }}</li>
          </ul>
        </div>
        <div class="teacher-subsection">
          <h4 class="teacher-subtitle">后续练习方向</h4>
          <ul v-if="safeNextRoundAdviceDisplay.length" class="explain-list teacher-bullet-list teacher-advice-list">
            <li v-for="(line, k) in safeNextRoundAdviceDisplay" :key="`nr-${k}`">{{ line }}</li>
          </ul>
          <p v-else class="score-item muted teacher-muted">暂无成体系的后续建议，可在下方「四维度与计分说明」中自订下一练重点。</p>
        </div>
      </div>

      <el-collapse
        id="result-anchor-details"
        tabindex="-1"
        v-model="resultSecondaryBlocksCollapse"
        class="ui-aux-collapse ui-aux-collapse--low result-secondary-blocks no-print inpage-nav-target"
      >
        <el-collapse-item title="四维度与计分说明" name="dim">
      <div
        class="score-card result-score-explain-card print-avoid-break"
        :class="{ 'result-demo-soft': demoModeUi.active }"
      >
        <h3>四维度 · 怎么理解本轮分数</h3>
        <p class="score-explain-lead muted">
          各维度分如何汇总；某一项未计分或数据较少时，多属本轮未走到对应环节，便于对照，并非异常。
        </p>
        <div class="score-item"><strong>评分模式：</strong>{{ safeScoringProfileLabel }}</div>
        <div class="score-item"><strong>总分计算：</strong>{{ totalExplanation.summary }}</div>
        <ul v-if="totalExplanation.items.length > 0" class="explain-list total-explain-list">
          <li v-for="(line, index) in totalExplanation.items" :key="`total-${index}`">{{ line }}</li>
        </ul>
        <div class="explain-grid">
          <div v-for="item in scoreExplanationCards" :key="item.key" class="explain-item">
            <div class="explain-head">
              <strong>{{ item.label }}</strong>
              <span>{{ formatScore(item.score) }}</span>
            </div>
            <div class="explain-validity" :class="{ 'explain-validity--soft': !item.valid }">
              {{ moduleValidityUserLine(item) }}
            </div>
            <p
              v-if="item.key === 'content' && showPptMatchSourceLine"
              class="module-source-line"
            >
              <strong>课件与内容对齐：</strong>{{ pptMatchSourceLine }}
            </p>
            <p
              v-if="item.key === 'qa' && showQaSourceLine"
              class="module-source-line"
            >
              <strong>问答环节：</strong>{{ qaSourceLine }}
            </p>
            <p
              v-if="item.key === 'qa' && safeQaResult?.answer_input_mode === 'voice'"
              class="module-source-line muted"
            >
              本轮回答采用语音作答。
            </p>
            <div class="explain-summary">{{ item.explanation.summary }}</div>
            <ul class="explain-list">
              <li v-for="(line, index) in item.explanation.items" :key="`${item.key}-${index}`">{{ line }}</li>
            </ul>
            <div v-if="item.key === 'content' && contentBreakdownLines.length" class="content-breakdown-hint">
              <div class="content-breakdown-title">内容得分补充分解</div>
              <ul class="explain-list content-breakdown-list">
                <li v-for="(line, idx) in contentBreakdownLines" :key="`cbd-${idx}`">{{ line }}</li>
              </ul>
            </div>
            <div v-if="item.key === 'qa' && qaBreakdownLines.length" class="content-breakdown-hint">
              <div class="content-breakdown-title">问答得分补充分解</div>
              <ul class="explain-list content-breakdown-list">
                <li v-for="(line, idx) in qaBreakdownLines" :key="`qbd-${idx}`">{{ line }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
        </el-collapse-item>

        <el-collapse-item
          v-if="
            resultGoalNarrativeLines.length ||
            resultGoalStatusReminder.lines.length ||
            resultRhythmLines.length
          "
          title="目标对照、达成与练习节奏"
          name="goals"
        >
          <el-alert
            v-if="resultGoalNarrativeLines.length"
            type="info"
            :closable="false"
            show-icon
            class="result-goal-narrative print-avoid-break"
            title="与训练目标对照"
          >
            <template #default>
              <ul class="result-goal-narrative__list">
                <li v-for="(ln, i) in resultGoalNarrativeLines" :key="`rgn-${i}`">{{ ln }}</li>
              </ul>
            </template>
          </el-alert>

          <el-alert
            v-if="resultGoalStatusReminder.lines.length"
            :type="resultGoalStatusAlertType"
            :closable="false"
            show-icon
            class="result-goal-status-reminder print-avoid-break"
            title="目标达成提醒"
          >
            <template #default>
              <ul class="result-goal-status-reminder__list">
                <li v-for="(ln, i) in resultGoalStatusReminder.lines" :key="`rgs-${i}`">{{ ln }}</li>
              </ul>
              <p
                v-if="resultGoalStatusReminder.nextAction?.label"
                class="result-goal-status-reminder__next muted"
              >
                <strong>下一步建议：</strong>{{ resultGoalStatusReminder.nextAction.label }}
              </p>
            </template>
          </el-alert>

          <el-alert
            v-if="resultRhythmLines.length"
            type="info"
            :closable="false"
            show-icon
            class="result-rhythm-reminder print-avoid-break"
            title="训练节奏提醒"
          >
            <template #default>
              <ul class="result-rhythm-reminder__list">
                <li v-for="(ln, i) in resultRhythmLines" :key="`rrm-${i}`">{{ ln }}</li>
              </ul>
            </template>
          </el-alert>
        </el-collapse-item>

        <el-collapse-item title="下一轮专项与训练预填" name="nextround">
      <div class="score-card next-round-training-card result-panel--accent ui-interactive-soft">
        <h3>下一轮训练建议</h3>
        <p class="next-round-lead muted">
          根据本轮评分，选择下一轮专项训练重点；开始训练后仍可按原流程完成讲解与问答。
        </p>
        <p
          class="next-round-overview-hint muted"
          :class="{ 'result-demo-soft': demoModeUi.active }"
        >
          进入训练页后，还会在顶部看到基于历史有效训练的近期提醒（最近一次重点与总览建议），与这里的选择相互补充；也可在训练页一键「继续上次训练方式」或「按建议方向训练」预填配置（不会自动开始训练）。
        </p>
        <p v-if="recommendedFocusLabel" class="next-round-recommend">
          <strong>推荐你下一轮重点训练：</strong>{{ recommendedFocusLabel }}
        </p>
        <p v-else class="next-round-recommend muted">本轮暂无法从评分中自动推荐薄弱项，你可任选一项专项开始。</p>
        <div class="next-round-chips">
          <el-button
            v-for="opt in nextFocusOptions"
            :key="opt.key"
            size="default"
            :type="effectiveNextFocus === opt.key ? 'primary' : 'default'"
            plain
            @click="selectedNextFocus = opt.key"
          >
            {{ opt.label }}
          </el-button>
        </div>
        <div class="next-round-actions">
          <el-button type="primary" plain @click="startNextRoundTraining">
            {{ nextRoundPrimaryButtonLabel }}
          </el-button>
        </div>
        <div class="result-closure-actions no-print" role="region" aria-label="训练闭环">
          <p class="result-closure-lead muted">需要沿用上次有效配置、按总览建议开练、回到首页或打开复盘台时，可从下栏选择。</p>
          <el-dropdown trigger="click" class="result-closure-dropdown">
            <el-button type="default" plain
              >更多导航与预填
              <span class="ui-dropdown-caret" aria-hidden="true">▾</span></el-button
            >
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="closureGoHome">返回首页</el-dropdown-item>
                <el-dropdown-item @click="closureResumeLastFromResult">继续上次训练方式</el-dropdown-item>
                <el-dropdown-item @click="closureTrainRecommendedFromResult">按建议方向训练</el-dropdown-item>
                <el-dropdown-item divided @click="closureViewHistoryFromResult">查看历史</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <p class="result-closure-footnote muted">
            以上入口仅做跳转与预填配置，不会自动开始训练；首页概况会在你回到首页后刷新展示。
          </p>
        </div>
      </div>
        </el-collapse-item>

        <el-collapse-item title="本轮专项成效与对比" name="focus">
      <div class="score-card focus-outcome-card result-panel--accent">
        <h3>本轮专项成效</h3>
        <template v-if="sessionRoundTrainingFocusKey !== 'none'">
          <p class="focus-outcome-line">
            <strong>训练重点：</strong>{{ sessionRoundTrainingFocusLabel }}
          </p>
          <p v-if="primaryFocusScoreDisplay" class="focus-outcome-line">
            <strong>本专项核心分：</strong>{{ primaryFocusScoreDisplay }}
          </p>
          <p class="focus-outcome-line">
            <strong>和最近同专项比：</strong>{{ focusOutcomeVsRecentDisplay }}
          </p>
          <p v-if="resultData?.training_focus_trend" class="focus-outcome-line focus-outcome-trend muted">
            <strong>同专项趋势回顾：</strong>{{ resultData.training_focus_trend }}
          </p>
          <p class="focus-outcome-line focus-outcome-next">
            <strong>下一轮怎么选：</strong>{{ focusOutcomeNextLabelDisplay }}
          </p>
          <div class="focus-metric-compare-sub">
            <h4 class="focus-metric-subtitle">本轮专项关键指标对比</h4>
            <p v-if="focusMetricSummaryLine" class="focus-metric-lead muted">{{ focusMetricSummaryLine }}</p>
            <ul v-if="focusMetricHighlightsList.length" class="focus-metric-list">
              <li v-for="(line, idx) in focusMetricHighlightsList" :key="`fmc-${idx}`">{{ line }}</li>
            </ul>
            <p v-else class="focus-metric-fallback muted">暂无足够同专项对比数据</p>
          </div>
        </template>
        <p v-else class="focus-outcome-body muted">
          本轮为常规训练，不做专项成效解读。若想看到练得如何、是否换重点，可在上一结果中选定专项再开始训练。
        </p>
      </div>
        </el-collapse-item>

        <el-collapse-item title="AI 追问建议" name="ai">
      <div class="score-card coach-ai-card" :class="{ 'result-demo-soft': demoModeUi.active }">
        <h3>AI 追问建议</h3>
        <p v-if="!safeFollowupQuestions.length" class="score-item muted">本轮没有可用追问。完成问答、内容相关流程并上传课件后，今后训练可生成更丰富的追问供参考。</p>
        <ul v-else class="coach-followup-list">
          <li v-for="(fq, i) in safeFollowupQuestions" :key="`fq-${i}`" class="coach-followup-item">
            <div class="fq-question"><strong>追问：</strong>{{ fq.question || '—' }}</div>
            <div class="fq-reason"><strong>说明：</strong>{{ fq.reason || '—' }}</div>
            <div v-if="followupDirectionLabel(fq.source)" class="fq-source">
              {{ followupDirectionLabel(fq.source) }}
            </div>
          </li>
        </ul>
      </div>
        </el-collapse-item>

        <el-collapse-item title="过程数据与模块明细" name="raw">
      <div class="score-card" :class="{ 'result-demo-soft': demoModeUi.active }">
        <h3>音频转写与语言指标</h3>
        <p v-if="resolvedAudioMetrics.audio_valid === false" class="score-item muted module-invalid-hint">
          {{
            resolvedAudioMetrics.audio_message ||
              '本轮未采到可分析的语音。多为环境过静、过短或识别不稳定，稍后在安静环境重试即可。'
          }}
        </p>
        <div class="score-item">
          <strong>转写文本：</strong>
          {{
            resolvedAudioMetrics.audio_valid === false
              ? '（本轮无可用转写，未展示可能不准的内容）'
              : resolvedAudioMetrics.transcript || '暂无转写文本'
          }}
        </div>
        <div class="score-item"><strong>语速：</strong>{{ formatSessionMetricCell(resolvedAudioMetrics.speech_rate) }}</div>
        <div class="score-item"><strong>停顿次数：</strong>{{ formatSessionMetricCell(resolvedAudioMetrics.pause_count) }}</div>
        <div class="score-item"><strong>平均停顿时长：</strong>{{ formatSessionMetricCell(resolvedAudioMetrics.avg_pause_sec) }}</div>
        <div class="score-item"><strong>口头禅次数：</strong>{{ formatSessionMetricCell(resolvedAudioMetrics.filler_count) }}</div>
      </div>

      <div class="score-card" :class="{ 'result-demo-soft': demoModeUi.active }">
        <h3>视觉分析指标</h3>
        <template v-if="resolvedVisionMetrics.vision_valid === false">
          <div class="score-item">
            <strong>视觉状态：</strong>
            {{
              resolvedVisionMetrics.vision_message ||
                '本轮画面信号偏弱（例如曝光、抖动或入镜不足），下次可调整机位与光线后重试。'
            }}
          </div>
        </template>
        <template v-else>
          <div class="score-item"><strong>正视前方比例：</strong>{{ formatSessionMetricCell(resolvedVisionMetrics.forward_gaze_ratio) }}</div>
          <div class="score-item"><strong>低头率：</strong>{{ formatSessionMetricCell(resolvedVisionMetrics.downward_head_ratio) }}</div>
          <div class="score-item"><strong>姿态稳定度：</strong>{{ formatSessionMetricCell(resolvedVisionMetrics.posture_stability) }}</div>
        </template>
      </div>

      <div
        v-if="resultData"
        class="score-card long-session-summary-card"
        :class="{ 'result-demo-soft': demoModeUi.active }"
      >
        <h3>整场答辩 · 长时会话摘要</h3>
        <p v-if="resolvedLongSessionSummary.hasSummary" class="score-item muted session-summary-hint">
          以下为本场<strong>整段音频分段合并</strong>与<strong>整段视频采样分析</strong>的汇总口径，而非单次短切片。
        </p>
        <div v-if="resolvedLongSessionSummary.hasSummary" class="session-summary-grid">
          <div v-if="resolvedLongSessionSummary.audio" class="session-summary-col">
            <div class="session-summary-subtitle">音频</div>
            <div class="score-item">
              <strong>总时长：</strong>{{ formatSessionSeconds(resolvedLongSessionSummary.audio.total_audio_duration_sec) }}
            </div>
            <div class="score-item">
              <strong>识别段数：</strong>{{ formatSessionInt(resolvedLongSessionSummary.audio.transcribed_chunks) }}
            </div>
            <div class="score-item">
              <strong>跳过段数：</strong>{{ formatSessionInt(resolvedLongSessionSummary.audio.skipped_chunks) }}
            </div>
            <div class="score-item">
              <strong>丢弃脏段数：</strong>{{ formatSessionInt(resolvedLongSessionSummary.audio.dropped_dirty_chunks) }}
            </div>
          </div>
          <div v-if="resolvedLongSessionSummary.video" class="session-summary-col">
            <div class="session-summary-subtitle">视频</div>
            <div class="score-item">
              <strong>总时长：</strong>{{ formatSessionSeconds(resolvedLongSessionSummary.video.total_video_duration_sec) }}
            </div>
            <div v-if="resolvedLongSessionSummary.video.duration_source" class="score-item">
              <strong>时长来源：</strong>{{ String(resolvedLongSessionSummary.video.duration_source) }}
            </div>
            <div class="score-item">
              <strong>处理帧数：</strong>{{ formatSessionInt(resolvedLongSessionSummary.video.processed_frames) }}
            </div>
            <div class="score-item">
              <strong>跳过帧数：</strong>{{ formatSessionInt(resolvedLongSessionSummary.video.skipped_frames) }}
            </div>
            <div class="score-item">
              <strong>采样模式：</strong>{{
                formatSampledModeLabel(
                  resolvedLongSessionSummary.video.sampled_mode_used,
                  resolvedLongSessionSummary.video.sampled_fps
                )
              }}
            </div>
          </div>
        </div>
        <p v-else class="score-item muted">本轮未带长时汇总信息，不影响已展示的总分与主结论</p>
      </div>

      <div class="score-card" :class="{ 'result-demo-soft': demoModeUi.active }">
        <h3>内容匹配卡</h3>
        <p v-if="showPptMatchSourceLine" class="score-item source-tag"><strong>课件与内容对齐：</strong>{{ pptMatchSourceLine }}</p>
        <template v-if="safePptMatch">
          <div class="score-item"><strong>当前页：</strong>第 {{ safePptMatch.page_index ?? '-' }} 页 - {{ safePptMatch.title || '-' }}</div>
          <div class="score-item"><strong>匹配度：</strong>{{ safePptMatch.match_score ?? '-' }}</div>
          <div class="score-item"><strong>关键词覆盖率：</strong>{{ safePptMatch.keyword_coverage ?? '-' }}</div>
          <div class="score-item"><strong>命中关键词：</strong>{{ matchedKeywordsText }}</div>
          <div class="score-item"><strong>缺失关键词：</strong>{{ missingKeywordsText }}</div>
          <div class="score-item"><strong>内容建议：</strong>{{ safePptMatch.comment || '无' }}</div>
        </template>
        <template v-else-if="isWithoutPptDefense">
          <div class="score-item muted">
            本轮为无课件答辩训练，未启用课件匹配；系统聚焦语言、仪态、问答与老师点评。
          </div>
        </template>
        <template v-else>
          <div class="score-item muted">本轮未做课件匹配；若未上传课件或流程未走内容对齐，属常见情况</div>
        </template>
      </div>

      <div class="score-card ppt-analysis-card" :class="{ 'result-demo-soft': demoModeUi.active }">
        <h3>PPT 匹配分析</h3>
        <template v-if="hasPptAnalysis">
          <div class="analysis-overall">
            <div class="analysis-overall-label">总体匹配度</div>
            <div class="analysis-overall-value">{{ formatScore(safePptOverallMatchScore) }}</div>
          </div>

          <div class="analysis-subtitle">逐页匹配分数</div>
          <div v-if="safePptSlideMatches.length > 0" class="analysis-slides">
            <div v-for="item in safePptSlideMatches" :key="`ppt-slide-${item.page}`" class="analysis-slide-row">
              <div class="analysis-slide-head">
                <span class="analysis-slide-page">第 {{ item.page }} 页</span>
                <span class="analysis-slide-score">{{ formatScore(item.score) }}</span>
              </div>
              <div class="analysis-progress-track">
                <div class="analysis-progress-bar" :style="{ width: `${Math.max(0, Math.min(100, Number(item.score) || 0))}%` }"></div>
              </div>
              <div class="analysis-preview">{{ item.text_preview || '该页暂无文本预览' }}</div>
            </div>
          </div>
          <div v-else class="score-item">暂无逐页匹配明细</div>

          <div class="analysis-hints">
            <div class="analysis-hint-item">
              <strong>漏讲页提示：</strong>{{ missedPagesText }}
            </div>
            <div class="analysis-hint-item">
              <strong>偏题提示：</strong>{{ offTopicText }}
            </div>
          </div>
        </template>
        <template v-else-if="hasSinglePagePptMatchOnly">
          <div class="score-item muted">
            本轮为单页匹配或自动猜页结果，暂无整册逐页匹配分析图；内容得分仍以上方「内容匹配卡」为准。
          </div>
        </template>
        <template v-else-if="isWithoutPptDefense">
          <div class="score-item muted">
            本轮为无课件答辩训练，未启用课件匹配与整册逐页分析。
          </div>
        </template>
        <template v-else>
          <div class="score-item muted">本轮未带整册 PPT 分析；若未上传或仅有单页，属常见情况</div>
        </template>
      </div>

      <div class="score-card" :class="{ 'result-demo-soft': demoModeUi.active }">
        <h3>问答评估卡</h3>
        <p v-if="showQaSourceLine" class="score-item source-tag"><strong>问答环节：</strong>{{ qaSourceLine }}</p>
        <p
          v-if="safeQaResult && safeQaResult.answer_input_mode === 'voice'"
          class="score-item muted qa-voice-answer-note"
        >
          本轮回答采用语音作答。
        </p>
        <p
          v-if="
            showQaSourceLine &&
            (safeQaResult?.qa_source === 'followup_generated' || resultData?.qa_source === 'followup_generated')
          "
          class="score-item muted"
        >
          本轮追问在第一轮回答评估后按规则生成。
        </p>
        <p v-if="showDefenseSequentialFlowHint" class="score-item defense-flow-hint">
          流程说明：先完成讲解阶段，再进入答辩问答。
        </p>
        <p class="qa-card-tip">该结果用于辅助判断答辩回答是否切题</p>
        <template v-if="safeQaResult">
          <p
            v-if="
              showQaSourceLine &&
              (safeQaResult.qa_source === 'followup_generated' || resultData?.qa_source === 'followup_generated') &&
              (safeQaResult.followup_reason ||
                safeQaResult.followup_target_topic ||
                resultData?.selected_followup_reason)
            "
            class="score-item source-tag followup-reason-line"
          >
            <strong>追问依据：</strong>
            <template v-if="safeQaResult.followup_target_topic">
              主题「{{ safeQaResult.followup_target_topic }}」。
            </template>
            {{ safeQaResult.followup_reason || resultData?.selected_followup_reason || '' }}
          </p>
          <div class="score-item"><strong>问题：</strong>{{ safeQaResult.question || '-' }}</div>
          <div class="score-item"><strong>是否切题：</strong>{{ safeQaResult.is_relevant ? '是' : '否' }}</div>
          <div class="score-item"><strong>覆盖率：</strong>{{ safeQaResult.coverage_score ?? '-' }}</div>
          <div class="score-item"><strong>命中关键词：</strong>{{ qaHitKeywordsText }}</div>
          <div class="score-item"><strong>缺失关键词：</strong>{{ qaMissingKeywordsText }}</div>
          <div class="score-item"><strong>评价：</strong>{{ safeQaResult.comment || '无' }}</div>
        </template>
        <template v-else>
          <div class="score-item module-soft-hint">本轮没有问答评估。若未进入问答环节，可忽略本区。</div>
        </template>
      </div>
        </el-collapse-item>

        <el-collapse-item title="其他改进建议" name="sugg">
      <div class="suggestions-section" :class="{ 'result-demo-soft': demoModeUi.active }">
        <h3>改进建议</h3>
        <ul class="suggestions-list">
          <li v-for="(suggestion, index) in safeSuggestions" :key="index" class="suggestion-item">
            <div v-if="suggestion.category" class="suggestion-category">{{ suggestion.category }}：</div>
            <div class="suggestion-content">{{ suggestion.content || suggestion.text || suggestion }}</div>
          </li>
          <li v-if="safeSuggestions.length === 0" class="suggestion-item">暂无其他补充建议，可以上方老师点评与分项说明为主</li>
        </ul>
      </div>
        </el-collapse-item>
      </el-collapse>

      <p class="result-page-section-k no-print" role="presentation">本场说明与留痕</p>

      <el-collapse v-model="resultMetaCollapse" class="ui-aux-collapse ui-aux-collapse--low result-meta-collapse no-print">
        <el-collapse-item title="本场会话、模式与过程说明" name="meta">
          <div class="session-info-left session-info-left--flat">
            <h3 class="result-meta-h2">当前查看会话</h3>
            <p class="training-mode-line result-meta-sid">
              会话编号 <code class="result-meta-sid-code">{{ sessionId }}</code>
            </p>
            <p class="training-mode-line">
              训练模式 <span class="ui-tag ui-tag--neutral">{{ safeScoringProfileLabel }}</span>
            </p>
            <p class="training-focus-session-line muted">
              本轮训练重点：<span class="ui-tag" :class="sessionRoundTrainingFocusTagClass">{{
                sessionRoundTrainingFocusLabel
              }}</span>
            </p>
            <p
              v-if="String(resultData?.scoring_profile || '').trim() === 'defense'"
              class="defense-flow-overview muted"
            >
              {{ DEFENSE_FLOW_OVERVIEW }}
            </p>
            <p v-if="resultPhaseClosureHint" class="result-phase-closure-hint muted">
              {{ resultPhaseClosureHint }}
            </p>
            <p v-if="resultWeeklyAccumulationHint" class="result-weekly-accum-hint muted">
              {{ resultWeeklyAccumulationHint }}
            </p>
            <p v-if="resultNextPlanHintLine" class="result-next-plan-hint muted">
              {{ resultNextPlanHintLine }}
            </p>
            <p v-if="showPreflightOkLine" class="preflight-ok-note muted">
              本轮训练开始前已通过基础准备检查。
            </p>
            <p
              v-if="resultInferenceChainLine"
              class="result-inference-chain muted"
              :class="{ 'result-inference-chain--demo-spotlight': demoModeUi.active }"
            >
              {{ resultInferenceChainLine }}
            </p>
          </div>
          <p class="report-button-tip report-button-tip--aux muted">
            向评委展示时可按：分数与链路 → 报告留档 → 历史专项对照（均为手动跳转，不会自动开始训练）。
          </p>
          <p class="history-filter-hint muted">
            历史页支持专项筛选、有效训练总览与无效记录清理（删除后不可恢复）。
          </p>
          <div class="ppt-match-status ppt-match-status--in-meta" :class="{ 'result-demo-soft': demoModeUi.active }">
            <div v-if="safePptMatch" class="ppt-match-yes result-ppt-match-line">课件/幻灯片：已参与对齐与计分</div>
            <div v-else class="ppt-match-no result-ppt-match-line">课件/幻灯片：未使用或未生成单页/逐页匹配结果</div>
          </div>
        </el-collapse-item>
      </el-collapse>

      <el-collapse
        v-model="resultMetricsMoreCollapse"
        class="ui-aux-collapse ui-aux-collapse--low result-metrics-collapse result-aux-for-print"
      >
        <el-collapse-item name="m" title="更多指标与明细（可选）">
          <div class="metrics-section">
            <p class="metrics-section-lead muted no-print">下列为补充参考指标，不影响上方总分与四维度主结论。</p>
            <div class="metrics-grid">
              <div v-for="metric in safeMetrics" :key="metric.name" class="metric-item">
                <div class="metric-name">{{ metric.name }}</div>
                <div class="metric-value">{{ metric.value }}{{ metric.unit || '' }}</div>
                <div class="metric-score" v-if="metric.score != null">指标分：{{ metric.score }}</div>
                <div v-if="metric.description" class="metric-description">{{ metric.description }}</div>
              </div>
              <div v-if="safeMetrics.length === 0" class="metric-item muted">本页未返回可展示的指标明细，可仅参考上方主结论。</div>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { onInpageNavLinkClick } from '../utils/a11yInpageNav'
import { getJson } from '../api/base'
import { toUserFacingMessage } from '../utils/userFacingError'
import { pageFeedback } from '../utils/pageFeedback'
import { sessionInferenceLine, boardParticipationLine } from '../utils/inferenceChainLabels'
import {
  readDemoMode,
  exitDemoMode,
  activateDemoModeFromRouteQuery,
  stripDemoQueryKeys,
} from '../utils/demoMode'
import {
  buildResultGoalNarrative,
  readTrainingGoals,
  hasActiveTrainingGoals,
  TRAINING_GOALS_CHANGED_EVENT,
  computeTrainingGoalProgress,
} from '../utils/trainingGoals'
import { computeGoalStatusPack, buildResultGoalStatusReminder } from '../utils/trainingGoalStatus'
import { computeTrainingRhythm, buildResultRhythmLines } from '../utils/trainingStreaks'
import { buildResultWeeklyAccumulationHint, computeWeeklyTrainingReview } from '../utils/trainingWeeklyReview'
import { computeNextTrainingPlan, buildResultNextPlanHint } from '../utils/nextTrainingPlan'
import { TRAINING_FOCUS_LABEL, SCORE_DIM_SHORT, DEFENSE_FLOW_OVERVIEW, SECTION } from '../constants/productTerms'
import {
  CURRENT_SESSION_ID_KEY,
  TRAINING_RUNTIME_SNAPSHOT_KEY,
  TRAINING_FOCUS_HANDOFF_KEY,
  persistCurrentSessionId,
} from '../utils/appPreferences'
import { readUserScopedItem, writeUserScopedItem, removeUserScopedItem } from '../utils/userScopedStorage'
import {
  getSessionResultRow,
  resolveAudioMetricsFromSession,
  resolveVisionMetricsFromSession,
  resolveLongSessionSummaryFromSession,
  formatSessionMetricCell,
} from '../utils/sessionResultMetrics'
import { PAGE_LOADING, PAGE_ERROR_ALERT_TITLE, PAGE_SOFT } from '../constants/pageStatusCopy'
import { buildResultCompareSummary } from '../utils/resultCompareSummary'

const router = useRouter()

const resultMetaCollapse = ref([])
const teacherCognitiveCollapse = ref([])
const resultMetricsMoreCollapse = ref([])
/** 计分、目标、专项、数据明细等次屏区块，默认全收起 */
const resultSecondaryBlocksCollapse = ref([])
const route = useRoute()

const demoModeUi = ref(readDemoMode())

function refreshResultDemoMode() {
  demoModeUi.value = readDemoMode()
}

function exitResultDemoMode() {
  exitDemoMode()
  refreshResultDemoMode()
}

const resultData = ref(null)
const loading = ref(false)
/** 串行化 fetchResult：并发/重复 watch 时仅最新一次请求可写 resultData 与关闭 loading */
const resultFetchGen = ref(0)
const errorMessage = ref('')
const resultHistoryForGoals = ref([])
/** 与首屏历史对照摘要：避免在 /history 返回前用空列表误判为「无上次记录」 */
const resultHistoryFetchSettled = ref(true)
const resultGoalsRevision = ref(0)
function bumpResultGoalsRevision() {
  resultGoalsRevision.value++
}
/** 旧记录无 inference_chain_snapshot 时，用当前 provider-status 作比赛说明兜底 */
const resultProviderFallback = ref(null)

const resultInferenceChainLine = computed(() => {
  const snap = resultData.value?.inference_chain_snapshot
  if (snap && typeof snap === 'object') {
    return `${sessionInferenceLine(snap)} ${boardParticipationLine(snap)}`
  }
  const fb = resultProviderFallback.value
  if (fb && typeof fb === 'object') {
    return `${sessionInferenceLine(fb)} ${boardParticipationLine(fb)}（本条记录未保存训练当时的链路快照，以上为当前系统配置，仅供现场说明。）`
  }
  return ''
})

const apiBase = import.meta.env.VITE_API_BASE || '/api'

/** 统一处理 query/params 可能是 string | string[] */
function normalizeId(val) {
  if (val == null) return ''
  if (Array.isArray(val)) return normalizeId(val[0])
  const s = String(val).trim()
  return s
}

/** 与训练/Report 一致：追问轮 taxonomy（优先 qa_result.followup_*，与后端 /qa/followup 对齐） */
function resolveFollowupTaxonomyShortLabel(qr) {
  if (!qr || typeof qr !== 'object') return '规则追问'
  const kind = String(qr.followup_provider_kind || 'rule').toLowerCase()
  const fb = qr.followup_fallback_to_rule === true
  if (kind === 'hybrid' && fb) return '混合追问（已回退规则）'
  if (kind === 'hybrid') return '混合追问'
  if (kind === 'model') return '模型追问'
  return '规则追问'
}

/** 与训练页一致：弱化技术 source，仅展示用户可读方向 */
function followupDirectionLabel(source) {
  const s = String(source || '').trim()
  if (s === 'qa_weak_point') return '追问方向：回答薄弱点'
  if (s === 'content_gap') return '追问方向：内容缺口'
  if (s === 'outline_gap') return '追问方向：大纲延展'
  return ''
}

/**
 * session_id 兜底：params.sessionId → query.session_id → query.sessionId → localStorage
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

const sessionId = computed(() => resolvedSessionId.value || '')

const showPreflightOkLine = computed(() => {
  const sid = sessionId.value
  if (!sid) return false
  try {
    return readUserScopedItem(localStorage, `mianshi_preflight_ok_${sid}`) === '1'
  } catch {
    return false
  }
})

const safeSummary = computed(() => resultData.value?.summary || null)
const defenseMaterialMode = computed(() =>
  resultData.value?.defense_material_mode === 'without_ppt' ? 'without_ppt' : 'with_ppt'
)
const isWithoutPptDefense = computed(() => defenseMaterialMode.value === 'without_ppt')

function moduleValidityUserLine(item) {
  if (!item) return ''
  if (item.key === 'content' && isWithoutPptDefense.value && !item.valid) {
    return '本轮为无课件答辩，未做内容匹配；本项不单独计分，属常见情况。'
  }
  if (item.valid) return '本项已按规则参与计分。'
  return '本项可依据有限或未走到对应环节，保留分数便于你对照。'
}

function normalizeTrainingFocusKey(raw) {
  const k = String(raw || '').trim().toLowerCase()
  if (k === 'language' || k === 'posture' || k === 'qa' || k === 'content') return k
  return null
}

function normalizeSessionTrainingFocusKey(raw) {
  const k = String(raw || '').trim().toLowerCase()
  if (k === 'language' || k === 'posture' || k === 'qa' || k === 'content' || k === 'none') return k
  return 'none'
}

const sessionRoundTrainingFocusKey = computed(() =>
  normalizeSessionTrainingFocusKey(resultData.value?.training_focus)
)

const sessionRoundTrainingFocusLabel = computed(() => {
  const k = sessionRoundTrainingFocusKey.value
  return TRAINING_FOCUS_LABEL[k] || TRAINING_FOCUS_LABEL.none
})

const sessionRoundTrainingFocusTagClass = computed(() => {
  const k = sessionRoundTrainingFocusKey.value
  const map = {
    language: 'ui-tag--focus-lang',
    posture: 'ui-tag--focus-posture',
    qa: 'ui-tag--focus-qa',
    content: 'ui-tag--focus-content',
    none: 'ui-tag--focus-none',
  }
  return map[k] || 'ui-tag--focus-none'
})

const resultGoalNarrativeLines = computed(() => {
  void resultGoalsRevision.value
  const r = resultData.value
  if (!r) return []
  const goals = readTrainingGoals()
  if (!hasActiveTrainingGoals(goals)) return []
  const pack = buildResultGoalNarrative({
    goals,
    sessionId: sessionId.value,
    trainingValid: r.training_valid !== false,
    totalScore: r.total_score,
    sessionFocusKey: sessionRoundTrainingFocusKey.value,
    focusTrendKind: r.focus_trend_kind,
    trainingFocusVsRecent: r.training_focus_vs_recent,
    historyList: resultHistoryForGoals.value,
  })
  console.log('[Result.goal] narrative=', pack.lines, 'kind=', pack.kind)
  return pack.lines
})

const resultGoalStatusReminder = computed(() => {
  void resultGoalsRevision.value
  const r = resultData.value
  if (!r) return { lines: [], status: null, nextAction: { key: '', label: '' } }
  if (r.training_valid === false) {
    return { lines: [], status: null, nextAction: { key: '', label: '' } }
  }
  const prog = computeTrainingGoalProgress({
    goals: readTrainingGoals(),
    historyList: resultHistoryForGoals.value,
    overview: null,
  })
  const pack = computeGoalStatusPack(prog)
  return buildResultGoalStatusReminder(prog, pack)
})

const resultGoalStatusAlertType = computed(() => {
  const st = resultGoalStatusReminder.value.status
  if (st === 'achieved') return 'success'
  if (st === 'near_complete') return 'warning'
  return 'info'
})

const resultGoalProgressForPlan = computed(() => {
  void resultGoalsRevision.value
  return computeTrainingGoalProgress({
    goals: readTrainingGoals(),
    historyList: resultHistoryForGoals.value,
    overview: null,
  })
})

const resultGoalStatusPackForPlan = computed(() => computeGoalStatusPack(resultGoalProgressForPlan.value))

const resultWeeklyForPlan = computed(() => {
  void resultGoalsRevision.value
  return computeWeeklyTrainingReview(resultHistoryForGoals.value, {
    overview: null,
    goals: readTrainingGoals(),
  })
})

const resultRhythmStatsForPlan = computed(() => {
  void resultGoalsRevision.value
  const p = resultGoalProgressForPlan.value
  const pack = resultGoalStatusPackForPlan.value
  let countRemaining = null
  if (p.validCountProgress) {
    const r = p.validCountProgress.target - p.validCountProgress.current
    countRemaining = r > 0 ? r : null
  }
  return computeTrainingRhythm(resultHistoryForGoals.value, {
    goalStatus: pack.status,
    targetFocus: p.goals?.target_focus || null,
    countRemaining,
  })
})

/** 训练节奏提醒：与 resultRhythmStatsForPlan / 目标状态一致，供折叠区展示 */
const resultRhythmLines = computed(() => {
  void resultGoalsRevision.value
  const p = resultGoalProgressForPlan.value
  const pack = resultGoalStatusPackForPlan.value
  return buildResultRhythmLines(resultRhythmStatsForPlan.value, {
    goalStatus: pack?.status ?? null,
    targetFocus: p?.goals?.target_focus || null,
  })
})

const resultNextPlan = computed(() => {
  void resultGoalsRevision.value
  const r = resultData.value
  if (!r || r.training_valid === false) return null
  return computeNextTrainingPlan({
    historyList: resultHistoryForGoals.value,
    overview: null,
    goals: readTrainingGoals(),
    goalProgress: resultGoalProgressForPlan.value,
    goalStatusPack: resultGoalStatusPackForPlan.value,
    rhythmStats: resultRhythmStatsForPlan.value,
    weeklyReview: resultWeeklyForPlan.value,
    resultSessionMeta: {
      sessionFocus: sessionRoundTrainingFocusKey.value,
      focusTrendKind: r.focus_trend_kind,
    },
  })
})

const resultNextPlanHintLine = computed(() =>
  buildResultNextPlanHint(resultNextPlan.value, {
    trainingValid: resultData.value?.training_valid !== false,
    goalStatus: resultGoalStatusPackForPlan.value?.status,
    sessionFocus: sessionRoundTrainingFocusKey.value,
    focusTrendKind: resultData.value?.focus_trend_kind,
  })
)

watch(
  resultNextPlan,
  (p) => {
    if (!p?.next_plan_action) return
    console.log('[Result.next_plan] action=', p.next_plan_action)
    console.log('[Result.next_plan] reason=', p.next_plan_reason)
  },
  { flush: 'post' }
)

const primaryFocusScoreDisplay = computed(() => {
  const k = sessionRoundTrainingFocusKey.value
  if (k === 'none') return ''
  const raw = resultData.value?.training_focus_primary_score
  if (raw == null || raw === '') return ''
  const n = Number(raw)
  if (!Number.isFinite(n)) return ''
  const lab = SCORE_DIM_SHORT[k] || '专项'
  return `${lab}核心分 ${n.toFixed(1)} 分`
})

/** 专项成效：与后端 training_focus_vs_recent 对齐（规则版 V1） */
const focusOutcomeVsRecentDisplay = computed(() => {
  const v = resultData.value?.training_focus_vs_recent
  const s = typeof v === 'string' ? v.trim() : ''
  return s || '—'
})

/** 用户化下一轮建议：优先 training_focus_next_action_label */
const focusOutcomeNextLabelDisplay = computed(() => {
  const v =
    resultData.value?.training_focus_next_action_label || resultData.value?.training_focus_next_hint
  const s = typeof v === 'string' ? v.trim() : ''
  return s || '—'
})

const focusMetricHighlightsList = computed(() => {
  const raw = resultData.value?.training_focus_metric_highlights
  if (!Array.isArray(raw)) return []
  return raw.map((x) => String(x || '').trim()).filter(Boolean)
})

const focusMetricSummaryLine = computed(() => {
  const c = resultData.value?.training_focus_metric_compare
  if (typeof c !== 'string' || !c.trim()) return ''
  const t = c.trim()
  if (t === '暂无足够同专项对比数据') return ''
  const hi = focusMetricHighlightsList.value
  if (hi.length && t === hi[0]) return ''
  return t
})

const apiRecommendedFocus = computed(() =>
  normalizeTrainingFocusKey(resultData.value?.recommended_training_focus)
)

const selectedNextFocus = ref(null)

watch(resultData, () => {
  selectedNextFocus.value = null
})

const nextFocusOptions = computed(() => {
  const o = [
    { key: 'language', label: TRAINING_FOCUS_LABEL.language },
    { key: 'posture', label: TRAINING_FOCUS_LABEL.posture },
  ]
  if (!isWithoutPptDefense.value) {
    o.push({ key: 'content', label: TRAINING_FOCUS_LABEL.content })
  }
  o.push({ key: 'qa', label: TRAINING_FOCUS_LABEL.qa })
  return o
})

const effectiveNextFocus = computed(() => {
  const opts = nextFocusOptions.value
  const sel = normalizeTrainingFocusKey(selectedNextFocus.value)
  if (sel && opts.some((x) => x.key === sel)) return sel
  const api = apiRecommendedFocus.value
  if (api && opts.some((x) => x.key === api)) return api
  return opts[0]?.key || 'language'
})

const recommendedFocusLabel = computed(() => {
  const k = apiRecommendedFocus.value
  if (!k) return ''
  return TRAINING_FOCUS_LABEL[k] || k
})

const NEXT_ROUND_BUTTON_LABELS = {
  language: '开始语言专项训练',
  posture: '开始仪态专项训练',
  qa: '开始问答专项训练',
  content: '开始内容专项训练',
}

const sessionTrainingInvalid = computed(() => resultData.value?.training_valid === false)

const resultCompareSummaryBlock = computed(() => {
  const r = resultData.value
  if (!r) {
    return { show: false, titleLine: '', detailLine: '', tone: 'empty' }
  }
  return buildResultCompareSummary({
    trainingValid: r.training_valid !== false,
    sessionId: sessionId.value,
    result: r,
    historyList: resultHistoryForGoals.value,
  })
})

const invalidTrainingExplainLine = computed(() => {
  const parts = []
  const r = String(resultData.value?.invalid_reason_summary || '').trim()
  if (r) parts.push(`说明：${r}。`)
  parts.push('建议先确认麦克风和摄像头、环境可稳定录制后，再完成一轮完整训练。')
  parts.push('下方分数和明细仍可供你复盘；与已纳入统计的趋势对比时，建议以完整训练为准。')
  return parts.join('')
})

const nextRoundPrimaryButtonLabel = computed(() => {
  if (resultData.value?.training_valid === false) {
    return '环境与设备就绪后再开始训练'
  }
  const k = effectiveNextFocus.value
  return NEXT_ROUND_BUTTON_LABELS[k] || '开始下一轮专项训练'
})

function logResultAction(action) {
  console.log('[Result.action] action=', action)
}

function resultRoundScoringProfile() {
  const p = String(resultData.value?.scoring_profile || 'defense').trim() || 'defense'
  const low = p.toLowerCase()
  return low === 'interview' ? 'interview' : 'defense'
}

function resultRoundDefenseMaterialMode() {
  return String(resultData.value?.defense_material_mode || 'with_ppt').trim().toLowerCase() === 'without_ppt'
    ? 'without_ppt'
    : 'with_ppt'
}

function closureGoHome() {
  const sid = String(sessionId.value || '').trim()
  if (!sid) {
    pageFeedback('Result', 'go_home', '暂时缺少会话信息，请从历史或训练页重新进入。', 'warning')
    return
  }
  logResultAction('go_home')
  pageFeedback('Result', 'go_home', '正在返回首页，可在首页继续训练并查看学习概况。', 'success')
  router.push({
    path: '/home',
    query: {
      last_completed_session_id: sid,
      entry_source: 'result',
    },
  })
}

function closureResumeLastFromResult() {
  if (!resultData.value) {
    pageFeedback('Result', 'resume_last', '结果还在加载，请稍候再试。', 'warning')
    return
  }
  logResultAction('resume_last')
  if (sessionTrainingInvalid.value) {
    pageFeedback(
      'Result',
      'resume_last',
      '本轮未纳入统计：仍会按本轮的模式与专项打开训练页，分数仅作现场对照；建议下一轮先保证设备与环境稳定。',
      'warning'
    )
  } else {
    pageFeedback(
      'Result',
      'resume_last',
      '已按本轮设置对齐「上次训练方式」，正在打开训练页（不会自动开始训练）。',
      'success'
    )
  }
  const profile = resultRoundScoringProfile()
  const dm = resultRoundDefenseMaterialMode()
  const tf = String(resultData.value.training_focus ?? 'none').trim().toLowerCase()
  let focus = tf === 'none' || tf === '' ? null : normalizeTrainingFocusKey(tf)
  let source = 'resume_last_config'
  if (focus === 'content' && dm === 'without_ppt') {
    focus = null
    source = 'none'
  }
  try {
    writeUserScopedItem(
      sessionStorage,
      TRAINING_FOCUS_HANDOFF_KEY,
      JSON.stringify({
        recommended_focus: focus,
        scoring_profile: profile,
        defense_material_mode: dm,
        source,
        from_session_id: sessionId.value || null,
        ts: Date.now(),
      })
    )
  } catch (_) {}
  try {
    removeUserScopedItem(localStorage, TRAINING_RUNTIME_SNAPSHOT_KEY, undefined, true)
  } catch (_) {}
  router.push({ path: '/training', query: { entry: 'result_resume' } })
}

function closureTrainRecommendedFromResult() {
  if (!resultData.value) {
    pageFeedback('Result', 'train_recommended', '结果还在加载，请稍候再试。', 'warning')
    return
  }
  logResultAction('train_recommended')
  if (sessionTrainingInvalid.value) {
    pageFeedback(
      'Result',
      'train_recommended',
      '本轮未纳入统计：仍会按建议专项打开训练页；建议下一轮先完成环境与设备检查。',
      'warning'
    )
  } else {
    pageFeedback(
      'Result',
      'train_recommended',
      '已按建议方向带好专项，正在打开训练页（不会自动开始训练）。',
      'success'
    )
  }
  const focus = apiRecommendedFocus.value || effectiveNextFocus.value
  const profile = resultRoundScoringProfile()
  const dm = resultRoundDefenseMaterialMode()
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
      entry: 'result_recommended',
      recommended_focus: focus,
      scoring_profile: profile,
      defense_material_mode: dm,
    },
  })
}

function closureViewHistoryFromResult() {
  logResultAction('view_history')
  pageFeedback('Result', 'view_history', '正在打开历史页。', 'info')
  router.push('/history')
}

function startNextRoundTraining() {
  if (!resultData.value) {
    pageFeedback('Result', 'next_round_training', '结果还在加载，请稍候再试。', 'warning')
    return
  }
  if (sessionTrainingInvalid.value) {
    pageFeedback(
      'Result',
      'next_round_training',
      '本轮未形成可用于复盘的完整结果。请先确认麦克风、摄像头与环境正常，再完成一轮完整训练后，再开始下一轮专项。',
      'warning'
    )
    return
  }
  const focus = effectiveNextFocus.value
  const profile = resultRoundScoringProfile()
  const dm = resultRoundDefenseMaterialMode()
  const payload = {
    recommended_focus: focus,
    scoring_profile: profile,
    defense_material_mode: dm,
    source: 'result_page',
    from_session_id: sessionId.value || null,
    ts: Date.now(),
  }
  try {
    writeUserScopedItem(sessionStorage, TRAINING_FOCUS_HANDOFF_KEY, JSON.stringify(payload))
  } catch (_) {}
  try {
    removeUserScopedItem(localStorage, TRAINING_RUNTIME_SNAPSHOT_KEY, undefined, true)
  } catch (_) {}
  const opt = nextFocusOptions.value.find((x) => x.key === focus)
  const focusLabel = opt?.label || '所选专项'
  const partialModules =
    Array.isArray(scoreExplanationCards.value) &&
    scoreExplanationCards.value.some((it) => it && it.valid === false)
  const partialNote = partialModules ? '（本轮有个别环节未产生得分，下一轮以现场表现与准备检查为准即可。）' : ''
  pageFeedback(
    'Result',
    'next_round_training',
    `已选定「${focusLabel}」，正在打开训练页；到达后请先完成准备检查，再开始训练。${partialNote}`,
    'success'
  )
  router.push({
    path: '/training',
    query: {
      entry: 'result_recommended',
      recommended_focus: focus,
      scoring_profile: profile,
      defense_material_mode: dm,
    },
  })
}

const safePptMatch = computed(() => resultData.value?.ppt_match || null)
const resolvedPptMatchSource = computed(() => {
  const nested = safePptMatch.value?.match_source
  const top = resultData.value?.ppt_match_source
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
  const qr = resultData.value?.qa_result
  const top = resultData.value?.qa_source
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
const safeMetrics = computed(() => (Array.isArray(resultData.value?.metrics) ? resultData.value.metrics : []))
const safeSuggestions = computed(() => (Array.isArray(resultData.value?.suggestions) ? resultData.value.suggestions : []))
const safeTotalScore = computed(() => resultData.value?.total_score ?? '-')
const safeLanguageScore = computed(() => resultData.value?.language_score ?? '-')
const safePostureScore = computed(() => resultData.value?.posture_score ?? '-')
const safeContentScore = computed(() => resultData.value?.content_score ?? '-')
const safeQaScore = computed(() => resultData.value?.qa_score ?? '-')
const safeScoringProfileLabel = computed(() => {
  const lbl = resultData.value?.scoring_profile_label
  return typeof lbl === 'string' && lbl.trim() !== '' ? lbl : '—'
})
const safeScoreBreakdown = computed(() => resultData.value?.score_breakdown || null)
/** 仅当对应模块计分有效时展示来源，避免无效模块误标 */
const contentModuleValid = computed(() => safeScoreBreakdown.value?.valid_modules?.content === true)
const qaModuleValid = computed(() => safeScoreBreakdown.value?.valid_modules?.qa === true)
const showPptMatchSourceLine = computed(
  () => Boolean(pptMatchSourceLine.value) && (contentModuleValid.value || isAutoGuessPptSource.value)
)
const showQaSourceLine = computed(() => qaModuleValid.value && Boolean(qaSourceLine.value))
const safeScoreExplanations = computed(() => resultData.value?.score_explanations || {})
const safeContentBreakdown = computed(() => resultData.value?.content_breakdown || null)

const contentBreakdownLines = computed(() => {
  if (isWithoutPptDefense.value) {
    return [
      '本轮未进行课件页面对齐与关键词匹配（无课件答辩模式）。',
      '内容分项未参与统一评分权重；语言、仪态、问答等模块仍按既有规则计入总分。',
    ]
  }
  const b = safeContentBreakdown.value
  if (!b || typeof b !== 'object') return []
  const fmt = (v) => {
    if (v === null || v === undefined || v === '') return '—'
    const n = Number(v)
    return Number.isFinite(n) ? n.toFixed(1) : String(v)
  }
  const lines = [
    `当前页匹配（指标）：${fmt(b.match_score)}`,
    `关键词覆盖：${b.keyword_coverage != null && b.keyword_coverage !== '' ? `${fmt(b.keyword_coverage)}%` : '—'}`,
    `命中当前页标题：${b.title_hit ? '是' : '否'}；命中大纲/他页标题：${b.outline_hit ? '是' : '否'}`,
  ]
  if (b.document_quality != null && b.document_quality !== '') {
    lines.push(`文档结构质量（规则）：${fmt(b.document_quality)}`)
  }
  if (b.final_content_score != null && b.final_content_score !== '') {
    lines.push(`内容模块折算分：${fmt(b.final_content_score)}`)
  }
  return lines
})

const safeQaBreakdown = computed(() => resultData.value?.qa_breakdown || null)

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
  const lines = [
    `是否切题：${b.is_relevant === true ? '是' : b.is_relevant === false ? '否' : '—'}`,
    `关键词覆盖（参考）：${covLabel}`,
    `命中关键词数：${b.hit_keyword_count ?? '—'}；缺失数：${b.missing_keyword_count ?? '—'}`,
    `回答信息量（规则）：${fmt(b.answer_information_level)}（约 ${b.answer_length ?? '—'} 字）`,
    `表达清晰度（规则）：${fmt(b.clarity_score)}`,
  ]
  if (b.final_qa_score != null && b.final_qa_score !== '') {
    lines.push(`问答模块折算分：${fmt(b.final_qa_score)}`)
  }
  return lines
})

const safeFollowupQuestions = computed(() => {
  const r = resultData.value?.followup_questions
  return Array.isArray(r) ? r : []
})
const safeCoachCommentary = computed(() => {
  const t = resultData.value?.coach_commentary
  return typeof t === 'string' ? t : ''
})
const safeImprovementAdvice = computed(() => {
  const r = resultData.value?.improvement_advice
  return Array.isArray(r) ? r : []
})
const safeOverallCommentary = computed(() => {
  const o = resultData.value?.overall_commentary
  if (typeof o === 'string' && o.trim()) return o.trim()
  return safeCoachCommentary.value
})
const safeCoachStrengths = computed(() => {
  const r = resultData.value?.strengths
  if (!Array.isArray(r)) return []
  return r.map((x) => String(x).trim()).filter(Boolean)
})
const safeCoachWeaknesses = computed(() => {
  const r = resultData.value?.weaknesses
  if (!Array.isArray(r)) return []
  return r.map((x) => String(x).trim()).filter(Boolean)
})
const safeNextRoundAdviceDisplay = computed(() => {
  const r = resultData.value?.next_round_advice
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
  const row = resultData.value
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

const safeMatchedKeywords = computed(() => (Array.isArray(safePptMatch.value?.matched_keywords) ? safePptMatch.value.matched_keywords : []))
const safeMissingKeywords = computed(() => (Array.isArray(safePptMatch.value?.missing_keywords) ? safePptMatch.value.missing_keywords : []))
const matchedKeywordsText = computed(() => safeMatchedKeywords.value.join('、') || '无')
const missingKeywordsText = computed(() => safeMissingKeywords.value.join('、') || '无')
const safeQaResult = computed(() => resultData.value?.qa_result || null)

/** 与训练页阶段引导呼应：一句话说明本轮结束于哪类流程（不做复杂推断） */
const resultPhaseClosureHint = computed(() => {
  if (!resultData.value || resultData.value.training_valid === false) return ''
  const isDefense = String(resultData.value.scoring_profile || '').trim() === 'defense'
  const qr = safeQaResult.value
  const qsrc = String(qr?.qa_source || resultData.value.qa_source || '').toLowerCase()
  const hasQa = !!(qr || typeof resultData.value.qa_score === 'number')

  if (isDefense && hasQa && qsrc === 'followup_generated') {
    return '本轮训练已完成完整阶段流程（含老师追问与作答评估）并生成结果。'
  }
  if (isDefense && hasQa) {
    return '本轮在答辩问答阶段完成作答评估并生成结果。'
  }
  if (isDefense && !hasQa) {
    return '本轮在讲解阶段结束并生成结果；未进入答辩问答时，结果以讲解与综合评估为主。'
  }
  if (!isDefense && hasQa) {
    return '本轮训练已完成并生成结果（含问答评估）。'
  }
  return '本轮训练已完成并生成结果。'
})

const resultWeeklyAccumulationHint = computed(() => {
  if (!resultData.value) return ''
  const trainingValid = resultData.value.training_valid !== false
  return buildResultWeeklyAccumulationHint({
    trainingValid,
    hasGoals: hasActiveTrainingGoals(readTrainingGoals()),
  })
})

/** 自动生成题 / 弱点追问 + 答辩模式：提示真实答辩时序 */
const showDefenseSequentialFlowHint = computed(() => {
  if (!showQaSourceLine.value || !safeQaResult.value) return false
  const qs = (
    resultData.value?.qa_source ||
    safeQaResult.value?.qa_source ||
    ''
  ).trim()
  if (qs !== 'auto_generated' && qs !== 'followup_generated') return false
  const sp = String(resultData.value?.scoring_profile || 'defense').trim()
  return sp !== 'interview'
})

const qaHitKeywordsText = computed(() => (Array.isArray(safeQaResult.value?.hit_keywords) ? safeQaResult.value.hit_keywords : []).join('、') || '无')
const qaMissingKeywordsText = computed(() => (Array.isArray(safeQaResult.value?.missing_keywords) ? safeQaResult.value.missing_keywords : []).join('、') || '无')
/** 与 report 无关：本页顶部卡片与长时区共用 raw_result/result 的解析结果 */
const currentSessionResultRow = computed(() => getSessionResultRow(resultData.value))
const resolvedAudioMetrics = computed(() => resolveAudioMetricsFromSession(currentSessionResultRow.value))
const resolvedVisionMetrics = computed(() => resolveVisionMetricsFromSession(currentSessionResultRow.value))
const resolvedLongSessionSummary = computed(() => resolveLongSessionSummaryFromSession(currentSessionResultRow.value))

const safePptAnalysis = computed(() => {
  // 优先读取新字段；兼容后端暂时写在 ppt_match 下的情况
  const topLevel = resultData.value?.ppt_match_analysis
  if (topLevel && typeof topLevel === 'object') return topLevel
  const legacy = resultData.value?.ppt_match
  if (legacy && typeof legacy === 'object' && Array.isArray(legacy.slide_matches)) return legacy
  return null
})
const hasPptAnalysis = computed(() => !!safePptAnalysis.value)
/** 仅有单页 ppt_match（如手动/自动猜页）而无整册 slide_matches 分析时，避免误标「未上传 PPT」 */
const hasSinglePagePptMatchOnly = computed(() => {
  const m = safePptMatch.value
  if (!m || typeof m !== 'object') return false
  if (m.page_index == null || m.page_index === '') return false
  return !hasPptAnalysis.value
})
const safePptOverallMatchScore = computed(() => safePptAnalysis.value?.overall_match_score ?? '—')
const safePptSlideMatches = computed(() =>
  Array.isArray(safePptAnalysis.value?.slide_matches) ? safePptAnalysis.value.slide_matches : []
)
const safeMissedPages = computed(() =>
  Array.isArray(safePptAnalysis.value?.missed_pages) ? safePptAnalysis.value.missed_pages : []
)
const safeOffTopicSegments = computed(() =>
  Array.isArray(safePptAnalysis.value?.off_topic_segments) ? safePptAnalysis.value.off_topic_segments : []
)
const missedPagesText = computed(() => {
  if (safeMissedPages.value.length === 0) return '无明显漏讲页'
  return `建议补充第 ${safeMissedPages.value.join('、')} 页的核心内容`
})
const offTopicText = computed(() => {
  if (safeOffTopicSegments.value.length === 0) return '未发现明显偏题片段'
  const firstTwo = safeOffTopicSegments.value.slice(0, 2).join('；')
  return `检测到偏题片段：${firstTwo}${safeOffTopicSegments.value.length > 2 ? '……' : ''}`
})

const summaryView = computed(() => {
  const s = resultData.value?.summary || {}
  const pick = (key, fallback) => {
    const v = s && typeof s === 'object' ? s[key] : undefined
    const str = v == null ? '' : String(v).trim()
    return str ? str : fallback
  }
  return {
    overall_comment: pick('overall_comment', '暂无总评'),
    strongest_aspect: pick('strongest_aspect', '暂无最强项结论'),
    weakest_aspect: pick('weakest_aspect', '暂无待改进项结论'),
    training_tip: pick('training_tip', '暂无训练建议'),
  }
})

const normalizeExplanation = (expl) => {
  if (typeof expl === 'string') {
    const text = expl.trim()
    return {
      summary: text || '评分解释缺失',
      items: text ? [text] : [],
    }
  }
  if (Array.isArray(expl)) {
    const items = expl.map((item) => String(item ?? '').trim()).filter(Boolean)
    return {
      summary: items[0] || '评分解释缺失',
      items,
    }
  }
  if (expl && typeof expl === 'object') {
    const summary = typeof expl.summary === 'string' ? expl.summary.trim() : ''
    const items = Array.isArray(expl.items)
      ? expl.items.map((item) => String(item ?? '').trim()).filter(Boolean)
      : []
    const mergedSummary = summary || items[0] || '评分解释缺失'
    return {
      summary: mergedSummary,
      items,
    }
  }
  return {
    summary: '评分解释缺失',
    items: [],
  }
}

const scoreExplanationCards = computed(() => {
  const validModules = safeScoreBreakdown.value?.valid_modules || {}
  const explanations = safeScoreExplanations.value || {}
  console.log('[Result] score_explanations raw', resultData.value?.score_explanations)
  console.log('[Result] explanation types', {
    total: typeof explanations.total,
    language: typeof explanations.language,
    posture: typeof explanations.posture,
    content: typeof explanations.content,
    qa: typeof explanations.qa,
  })
  return [
    {
      key: 'language',
      label: TRAINING_FOCUS_LABEL.language,
      score: safeLanguageScore.value,
      valid: validModules.language !== false,
      explanation: normalizeExplanation(explanations.language),
    },
    {
      key: 'posture',
      label: TRAINING_FOCUS_LABEL.posture,
      score: safePostureScore.value,
      valid: validModules.posture !== false,
      explanation: normalizeExplanation(explanations.posture),
    },
    {
      key: 'content',
      label:
        isWithoutPptDefense.value && validModules.content !== true
          ? '内容专项（未启用）'
          : TRAINING_FOCUS_LABEL.content,
      score: safeContentScore.value,
      valid: validModules.content === true,
      explanation: normalizeExplanation(explanations.content),
    },
    {
      key: 'qa',
      label: TRAINING_FOCUS_LABEL.qa,
      score: safeQaScore.value,
      valid: validModules.qa === true,
      explanation: normalizeExplanation(explanations.qa),
    },
  ]
})

const totalExplanation = computed(() => {
  return normalizeExplanation(safeScoreExplanations.value?.total)
})

const formatScore = (val) => {
  if (val == null) return '—'
  if (typeof val === 'number') return String(val)
  const s = String(val).trim()
  return s ? s : '—'
}

const formatSessionSeconds = (v) => {
  if (v == null || v === '') return '—'
  const n = Number(v)
  if (!Number.isFinite(n)) return String(v)
  if (n < 60) return `${n.toFixed(1)} 秒`
  const m = Math.floor(n / 60)
  const s = n - m * 60
  return `${m} 分 ${s.toFixed(0)} 秒`
}

const formatSessionInt = (v) => {
  if (v == null || v === '') return '—'
  const n = Number(v)
  return Number.isFinite(n) ? String(Math.round(n)) : String(v)
}

const formatSampledModeLabel = (mode, fps) => {
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

const fetchResult = async (targetSessionId, allowRetry = true) => {
  if (!targetSessionId) {
    loading.value = false
    errorMessage.value = ''
    resultData.value = null
    resultHistoryForGoals.value = []
    resultHistoryFetchSettled.value = true
    return
  }

  const myGen = ++resultFetchGen.value
  loading.value = true
  errorMessage.value = ''
  resultData.value = null
  resultHistoryForGoals.value = []
  resultProviderFallback.value = null
  resultHistoryFetchSettled.value = false

  const requestPath = `/result/${encodeURIComponent(targetSessionId)}`
  const fullUrl = `${apiBase}${requestPath}`
  console.log('[Result] fetchResult 请求 URL:', fullUrl)

  try {
    const response = await getJson(requestPath)
    if (myGen === resultFetchGen.value) {
      resultData.value = response
    }
  } catch (e) {
    const msg = e && e.message ? String(e.message) : String(e)
    console.error('[Result] fetchResult 失败（完整错误）:', e)
    console.error('[Result] fetchResult 失败 message/stack:', {
      message: e && e.message,
      stack: e && e.stack,
      name: e && e.name,
    })
    // 结束训练后立即跳转时，偶发 404：再等一次读库/内存
    if (allowRetry && /404/.test(msg)) {
      console.warn('[Result] fetchResult 404，400ms 后重试一次')
      await new Promise((r) => setTimeout(r, 400))
      await fetchResult(targetSessionId, false)
      return
    }
    if (myGen === resultFetchGen.value) {
      errorMessage.value = toUserFacingMessage(
        e,
        '暂时无法获取本轮结果，或该条不属于当前账号。可在训练页结束一轮后再试，或从历史页打开本账号记录。'
      )
    }
  } finally {
    if (myGen === resultFetchGen.value) {
      loading.value = false
    }
  }

  if (myGen !== resultFetchGen.value) return
  if (!resultData.value) {
    resultHistoryFetchSettled.value = true
    return
  }

  try {
    if (myGen !== resultFetchGen.value) {
      resultHistoryFetchSettled.value = true
      return
    }
    const response = resultData.value
    try {
      const hist = await getJson('/history')
      resultHistoryForGoals.value = Array.isArray(hist.history) ? hist.history : []
    } catch (_) {
      resultHistoryForGoals.value = []
    } finally {
      if (myGen === resultFetchGen.value) {
        resultHistoryFetchSettled.value = true
      }
    }
    if (!response?.inference_chain_snapshot) {
      try {
        resultProviderFallback.value = await getJson('/system/provider-status')
      } catch (_) {
        resultProviderFallback.value = null
      }
    }
    try {
      const rawSnap = readUserScopedItem(localStorage, TRAINING_RUNTIME_SNAPSHOT_KEY)
      if (rawSnap) {
        const o = JSON.parse(rawSnap)
        if (o && o.session_id === targetSessionId) {
          removeUserScopedItem(localStorage, TRAINING_RUNTIME_SNAPSHOT_KEY, undefined, true)
          console.log('[Result] cleared training runtime snapshot for session', targetSessionId)
        }
      }
    } catch (_) {}
    const tfRaw = response?.training_focus
    const tfNorm = String(tfRaw || 'none').trim().toLowerCase()
    const disp =
      tfNorm === 'language'
        ? '语言专项'
        : tfNorm === 'posture'
          ? '仪态专项'
          : tfNorm === 'qa'
            ? '问答专项'
            : tfNorm === 'content'
              ? '内容专项'
              : '常规训练'
    console.log('[Result.focus] training_focus=', tfRaw, 'normalized=', tfNorm)
    console.log('[Result.focus] display_label=', disp)
    if (tfNorm !== 'none') {
      console.log('[Result.focus.summary] vs_recent=', response?.training_focus_vs_recent)
      console.log('[Result.focus.summary] next_action=', response?.training_focus_next_action)
    }
    console.log('[Result] fetchResult 成功，响应:', response)
    console.log('[Result] audio_session_summary', response?.audio_session_summary)
    console.log('resultData.vision_session_summary', resultData.value?.vision_session_summary)
    console.log('[Result] resultData.vision_analysis', response?.vision_analysis)
    console.log(
      '[Result] scoring_profile =',
      response?.scoring_profile,
      'scoring_profile_label =',
      response?.scoring_profile_label
    )
    const se = response?.score_explanations
    console.log('[Result] score_explanations from API', se)
    if (se && typeof se === 'object') {
      for (const k of ['total', 'language', 'posture', 'content', 'qa']) {
        console.log(`[Result] score_explanations.${k} type`, typeof se[k])
      }
    }
    console.log('[Result] transcript (pure field)', response?.transcript)
    console.log('[Result] audio_metrics (separate from transcript)', response?.audio_metrics)
    console.log('[Result] resolvedAudioMetrics', resolvedAudioMetrics.value)
    console.log('[Result] resolvedVisionMetrics', resolvedVisionMetrics.value)
    console.log('result vision debug:', resultData.value)
    console.log('result vision fields:', {
      vision_valid: response?.vision_valid ?? response?.vision_analysis?.vision_valid,
      vision_message: response?.vision_message ?? response?.vision_analysis?.vision_message,
      vision_metrics: response?.vision_analysis,
      metrics: response?.metrics,
      resultData: response,
    })
  } catch (postErr) {
    console.error('[Result] fetchResult 主结果之后补充处理失败（主结果仍展示）:', postErr)
    if (myGen === resultFetchGen.value) {
      resultHistoryFetchSettled.value = true
    }
  }
}

function retryFetchResult() {
  console.log('[Result.load] retry=', true)
  const sid = resolvedSessionId.value
  if (sid) fetchResult(sid)
}

function goToHomeFromResult() {
  router.push('/home')
}

watch(loading, (v) => {
  console.log('[Result.load] loading=', v)
})

watch(errorMessage, (m) => {
  if (m) console.log('[Result.load] error=', m)
})

watch(
  resultGoalStatusReminder,
  (b) => {
    if (!resultData.value) return
    if (!hasActiveTrainingGoals(readTrainingGoals())) return
    if (!b.lines?.length) return
    console.log('[Result.goal_status] status=', b.status)
    console.log('[Result.goal_status] next_action=', b.nextAction)
  },
  { deep: true, flush: 'post' }
)

watch(
  () => resolvedSessionId.value,
  (newSessionId) => {
    if (newSessionId) {
      persistCurrentSessionId(newSessionId)
      fetchResult(newSessionId)
    } else {
      loading.value = false
      errorMessage.value = ''
      resultData.value = null
      resultHistoryForGoals.value = []
      resultHistoryFetchSettled.value = true
    }
  },
  { immediate: true }
)

watch(
  resultData,
  (r) => {
    if (!r) return
    const c = r.score_breakdown?.valid_modules?.content
    const expl = r.score_explanations?.content
    const explStr = typeof expl === 'string' ? expl : ''
    const looksMissingPpt =
      explStr.includes('ppt_match') || explStr.includes('PPT 匹配') || explStr.includes('当前页')
    if (c === false || looksMissingPpt) {
      console.warn('[Result] content module invalid — full debug', {
        ppt_match: r.ppt_match,
        ppt_match_source: r.ppt_match_source,
        content_breakdown: r.content_breakdown,
        raw_result: r.raw_result ?? r,
        score_breakdown: r.score_breakdown,
        score_explanations: r.score_explanations,
      })
    }
  },
  { deep: true }
)

watch(
  resultData,
  (row) => {
    const qr = row?.qa_result
    if (!row || !qr || String(qr.qa_source || '').trim() !== 'followup_generated') return
    console.log('[Result.followup.source] qa_result=', qr)
    console.log('[Result.followup.source] provider_kind=', qr?.followup_provider_kind)
    console.log('[Result.followup.source] fallback_to_rule=', qr?.followup_fallback_to_rule)
    console.log('[Result.followup.source] final label=', resolveFollowupTaxonomyShortLabel(qr))
  },
  { deep: true }
)

onMounted(() => {
  try {
    window.addEventListener(TRAINING_GOALS_CHANGED_EVENT, bumpResultGoalsRevision)
  } catch (_) {}
  if (activateDemoModeFromRouteQuery(route.query)) {
    refreshResultDemoMode()
    const q = stripDemoQueryKeys({ ...route.query })
    if (JSON.stringify(q) !== JSON.stringify(route.query)) {
      router.replace({ path: route.path, query: q })
    }
  } else {
    refreshResultDemoMode()
  }
  console.log('[Result.demo_mode] active=', demoModeUi.value.active)
  console.log(
    '[Result.demo_mode] emphasized_blocks=',
    demoModeUi.value.active
      ? ['total_hero', 'subscores', 'teacher_commentary', 'inference_chain', 'focus_outcome']
      : []
  )
  console.log('[Result] onMounted route.query:', { ...route.query })
  console.log('[Result] onMounted route.params:', { ...route.params })
  console.log('[Result] onMounted 最终 sessionId:', resolvedSessionId.value || '(empty)')
})

onBeforeUnmount(() => {
  try {
    window.removeEventListener(TRAINING_GOALS_CHANGED_EVENT, bumpResultGoalsRevision)
  } catch (_) {}
})

const goToHistory = () => {
  router.push('/history')
}

const goToReport = () => {
  if (!sessionId.value) return
  const sid = sessionId.value
  persistCurrentSessionId(sid)
  router.push({ name: 'Report', params: { sessionId: sid }, query: { session_id: sid } })
}

const goToTraining = () => {
  try {
    removeUserScopedItem(localStorage, TRAINING_RUNTIME_SNAPSHOT_KEY, undefined, true)
  } catch (_) {}
  router.push('/training')
}
</script>

<style scoped>
.result-page {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  padding: 0;
  min-height: 100vh;
  box-sizing: border-box;
}

.result-load-placeholder {
  width: 100%;
  max-width: min(var(--app-content-max-width, 1360px), 100%);
  text-align: left;
}

.result-load-placeholder__label {
  margin: 0 0 6px;
  font-size: 0.95rem;
}

.result-load-placeholder__hint {
  margin: 0 0 14px;
  font-size: 0.86rem;
  line-height: 1.5;
}
.result-error-panel {
  width: 100%;
  max-width: min(var(--app-content-max-width, 1360px), 100%);
  text-align: left;
}

.result-error-panel__body {
  margin: 0 0 12px;
  font-size: 0.92rem;
  line-height: 1.55;
}

.result-error-panel__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.ui-dropdown-caret {
  display: inline-block;
  margin-left: 4px;
  font-size: 0.75em;
  opacity: 0.85;
  line-height: 1;
}

.result-next-actions--tiered .result-next-actions__primary {
  align-items: center;
}

.debug-message {
  width: 100%;
  max-width: 800px;
  margin: 20px 0;
  padding: 15px;
  border-radius: 8px;
  text-align: center;
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

.result-content {
  width: 100%;
  max-width: min(var(--app-content-max-width, 1360px), 100%);
  min-width: 0;
  box-sizing: border-box;
}

.result-page-head {
  width: 100%;
  max-width: min(var(--app-content-max-width, 1360px), 100%);
  text-align: left;
  margin-bottom: 8px;
}

.result-page-head .ui-page-title {
  font-size: clamp(2rem, 2.6vw, 2.625rem);
  margin-bottom: 8px;
}

.result-page-head .ui-page-sub {
  font-size: var(--font-md, 17px);
  line-height: 1.65;
  max-width: 48rem;
}

.result-inpage-nav {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  margin: 0 0 20px;
  padding: 14px 22px;
  font-size: var(--font-sm, 15px);
  gap: 10px 20px;
  border-radius: var(--ui-radius-lg);
  background: var(--ui-surface);
  border: 1px solid var(--ui-card-border, var(--ui-border));
  box-shadow: var(--ui-shadow-card);
}

.result-inpage-nav .ui-inpage-nav__link {
  font-size: var(--font-sm, 15px);
  font-weight: 600;
}

.result-hero-v1 {
  margin-bottom: 16px;
  padding: 20px 22px;
  text-align: left;
}

.result-hero-v1__top {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.result-hero-v1__score-block {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.result-hero-v1__score-label {
  font-size: 0.95rem;
  font-weight: 600;
  color: #64748b;
}

.result-hero-v1__score-value {
  font-size: 2.35rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: #0f172a;
  line-height: 1;
}

.result-hero-v1__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.result-hero-v1__tagline {
  margin: 14px 0 0;
  font-size: 1.02rem;
  line-height: 1.6;
  color: #334155;
}

.result-hero-2col {
  align-items: start;
  margin-bottom: 20px;
  width: 100%;
  box-sizing: border-box;
}

@media (min-width: 900px) {
  .result-hero-2col.ui-l-desk-2 {
    grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
    gap: 24px 28px;
  }
}

@media (min-width: 1280px) {
  .result-hero-2col.ui-l-desk-2 {
    grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
    gap: 28px 32px;
  }
}

.result-hero-2col .result-primary-actions--hero-dock {
  margin-bottom: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}

.result-primary-actions {
  margin-bottom: 14px;
  padding: 14px 18px;
  text-align: left;
}

.result-next-panel {
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-items: stretch;
  min-height: 0;
  width: 100%;
  box-sizing: border-box;
}

.result-next-panel__title {
  margin: 0 0 2px;
  font-size: 1.35rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--ui-text-primary);
  line-height: 1.25;
}

.result-next-panel__advice {
  margin: 0;
  font-size: var(--font-base, 17px);
  line-height: 1.65;
  color: var(--ui-text-primary);
}

.result-next-panel__emph {
  color: var(--ui-accent);
  font-weight: 700;
}

.result-next-focus-callout {
  margin: 0;
  padding: 12px 14px;
  border-radius: var(--ui-radius-md);
  background: var(--ui-accent-soft);
  border: 1px solid var(--ui-accent-muted);
  box-sizing: border-box;
}

.result-next-focus-callout__k {
  display: block;
  margin-bottom: 6px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ui-accent);
}

.result-next-focus-callout__v {
  margin: 0;
  font-size: var(--font-sm, 15px);
  line-height: 1.6;
  color: var(--ui-text-primary);
}

.result-next-panel .el-button.result-btn-primary {
  font-size: var(--font-md, 17px);
  font-weight: 700;
  padding: 12px 22px;
}

.result-next-panel .el-button.result-btn-secondary {
  font-size: var(--font-base, 16px);
  font-weight: 600;
}

.result-next-panel .el-button.result-btn-tertiary {
  font-size: var(--font-sm, 15px);
  font-weight: 500;
  color: var(--ui-text-secondary);
}

.result-next-actions--stacked {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  width: 100%;
  margin-top: 2px;
}

.result-next-actions--stacked .result-next-actions__btn {
  width: 100%;
  margin: 0 !important;
}

.result-next-actions--stacked .result-next-actions__more {
  width: 100%;
}

.result-next-actions--stacked .result-next-actions__more :deep(.el-button) {
  width: 100%;
}

@media (min-width: 901px) {
  .result-next-actions--stacked {
    flex-direction: row;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px 12px;
  }

  .result-next-actions--stacked .result-btn-primary {
    flex: 1 1 100%;
    min-width: 0;
  }

  .result-next-actions--stacked .result-btn-secondary,
  .result-next-actions--stacked .result-next-actions__more {
    flex: 1 1 auto;
    width: auto;
    min-width: 140px;
  }

  .result-next-actions--stacked .result-next-actions__more :deep(.el-button) {
    width: 100%;
  }
}

@media (max-width: 900px) {
  .result-primary-actions__row {
    flex-direction: column;
    align-items: stretch;
  }

  .result-primary-actions__row .el-button {
    width: 100%;
    margin-left: 0 !important;
    margin-right: 0 !important;
  }
}

.result-primary-actions__k {
  margin: 0 0 10px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #64748b;
}

.result-primary-actions__lead {
  margin: -4px 0 12px;
  font-size: 0.86rem;
  line-height: 1.5;
}

.result-primary-actions__row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 12px;
  align-items: center;
}

.result-secondary-blocks {
  margin: 4px 0 18px;
}

.result-secondary-blocks .el-collapse-item__content {
  padding-top: 6px;
}

.result-secondary-blocks .score-card:first-of-type {
  margin-top: 0;
}

.training-invalid-banner--soft {
  border-left: 3px solid #93c5fd;
}

.result-meta-collapse {
  margin-bottom: 14px;
}

.session-info-left--flat {
  padding: 0;
}

.result-meta-h2 {
  margin: 0 0 10px;
  font-size: 1rem;
}

.report-button-tip--aux {
  margin: 12px 0 8px;
  font-size: 0.84rem;
}

.result-aux-collapse {
  margin: 16px 0;
}

.result-aux-collapse .el-alert {
  margin-bottom: 10px;
}

.result-aux-collapse .el-alert:last-child {
  margin-bottom: 0;
}

.result-panel--teacher {
  border-left: 3px solid var(--ui-accent-muted);
}

.result-panel--accent {
  border-left: 3px solid var(--brand-border-accent-soft);
}

.teacher-feedback-card--prominent {
  margin: 0 0 24px;
  padding: 22px 24px;
  border: 1px solid var(--ui-border);
}

.teacher-feedback-card--prominent h3 {
  margin-top: 0;
}

.result-tier-review {
  margin-top: 6px;
}

.teacher-card-main-title {
  margin: 0 0 8px;
  font-size: 1.45rem;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.02em;
  line-height: 1.25;
}

.teacher-card-lead {
  margin: 0 0 14px;
  font-size: var(--font-base, 16px);
  line-height: 1.65;
  color: #475569;
}

.result-teacher-cognitive-collapse {
  margin: 0 0 14px;
  max-width: 100%;
}

.cognitive-provider-strip--in-collapse {
  margin: 0;
}

.result-aag-eyebrow {
  margin: 0 0 4px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #64748b;
}

.result-aag-lead {
  margin: 0 0 12px;
  font-size: 0.86rem;
  line-height: 1.5;
}

.result-compare-summary {
  margin: 0 0 16px;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: linear-gradient(165deg, #f8fafc 0%, #fff 100%);
  max-width: 100%;
}

.result-compare-summary__title {
  margin: 0;
  font-size: var(--font-base, 16px);
  font-weight: 700;
  line-height: 1.5;
  color: #0f172a;
}

.result-compare-summary__detail {
  margin: 6px 0 0;
  font-size: var(--font-sm, 15px);
  line-height: 1.6;
  color: #475569;
}

.result-compare-summary--up {
  border-color: #bbf7d0;
  background: linear-gradient(165deg, #f0fdf4 0%, #fff 100%);
}

.result-compare-summary--down {
  border-color: #fecdd3;
  background: linear-gradient(165deg, #fff1f2 0%, #fff 100%);
}

.result-compare-summary--flat,
.result-compare-summary--first {
  border-color: #e2e8f0;
}

.result-aag-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 12px;
}

.result-section-landmark {
  margin: 0 0 16px;
  max-width: 46rem;
  font-size: 0.86rem;
  line-height: 1.55;
  color: #334155;
}

.result-score-explain-card h3 {
  font-size: 1.28rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.score-explain-lead {
  margin: 0 0 12px;
  font-size: var(--font-sm, 15px);
  line-height: 1.6;
}

.explain-validity--soft {
  font-size: 0.9rem;
  color: #64748b;
}

.result-page-section-k {
  margin: 28px 0 10px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #94a3b8;
}

.result-meta-sid {
  font-size: 0.9rem;
}

.result-meta-sid-code {
  font-size: 0.82rem;
  word-break: break-all;
}

.metrics-section-lead {
  margin: 0 0 12px;
  font-size: 0.86rem;
  line-height: 1.45;
}

.module-soft-hint {
  line-height: 1.5;
  color: #64748b;
}

.hero-right--v1 .summary-title {
  font-size: 0.95rem;
}

.training-invalid-banner {
  margin-bottom: 16px;
}

.training-invalid-banner__body {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.55;
  color: #606266;
}

.session-info {
  margin-bottom: 30px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.session-info-left h2 {
  margin: 0 0 10px;
}

.training-mode-line {
  margin: 0;
  font-size: 0.95rem;
  color: #606266;
}

.button-group {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

.result-demo-path-label {
  margin: 0;
  width: 100%;
  text-align: right;
  font-size: 0.78rem;
  font-weight: 600;
  color: #909399;
}

.result-next-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  align-items: flex-start;
}

.result-next-actions__aux {
  margin-top: 2px;
  gap: 8px 14px;
}

.report-button-tip {
  margin: 0;
  padding: 5px 10px;
  background: #f0f9ff;
  color: #409eff;
  border: 1px solid #d9ecff;
  border-radius: 4px;
  font-size: 0.8em;
  text-align: center;
  max-width: 200px;
}

.history-filter-hint {
  margin: 0;
  font-size: 0.78em;
  line-height: 1.45;
  max-width: 220px;
  text-align: right;
}

.ppt-match-status {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  text-align: center;
}

.result-ppt-match-line {
  font-size: 0.9rem;
  line-height: 1.45;
  margin: 0;
}

.ppt-match-yes {
  background: #f0f9ff;
  color: #409eff;
  border: 1px solid #d9ecff;
}

.ppt-match-no {
  background: #f9f0ff;
  color: #909399;
  border: 1px solid #f0d9ff;
}

.ppt-match-status--in-meta {
  margin-top: 12px;
  margin-bottom: 0;
  text-align: left;
}

/* 结果总览卡（轻量品牌色，非整幅海报） */
.result-overview-card {
  margin-bottom: 0;
  padding: var(--ui-card-pad-y, 22px) var(--ui-card-pad-x, 24px);
  border-radius: var(--ui-radius-lg);
  background: var(--ui-surface);
  border: 1px solid var(--ui-card-border, var(--ui-border));
  box-shadow: var(--ui-shadow-card);
  position: relative;
  overflow: hidden;
  transition: box-shadow var(--ui-transition);
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.result-overview-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #1e3a8a 0%, #2563eb 55%, #38bdf8 100%);
  pointer-events: none;
}

.result-page--brand-v1 .result-overview-card:hover {
  box-shadow: var(--ui-shadow-card-hover);
}

.result-overview-card__head {
  margin-bottom: 16px;
}

.result-overview-card__title {
  margin: 0 0 8px;
  font-size: 1.45rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--ui-text-primary);
  line-height: 1.25;
}

.result-overview-card__lead {
  margin: 0;
  font-size: var(--font-sm, 15px);
  line-height: 1.65;
  color: var(--ui-text-secondary);
}

.result-overview-scoreblock {
  display: grid;
  grid-template-columns: minmax(120px, 200px) minmax(0, 1fr);
  gap: 20px 28px;
  align-items: start;
  margin-bottom: 16px;
}

@media (min-width: 1280px) {
  .result-overview-scoreblock {
    grid-template-columns: minmax(160px, 240px) minmax(0, 1fr);
    gap: 22px 36px;
  }
}

.result-overview-total__label {
  font-size: var(--font-sm, 15px);
  font-weight: 600;
  color: var(--ui-text-secondary);
  margin-bottom: 8px;
}

.result-overview-total__value {
  font-size: clamp(2.85rem, 5vw, 3.85rem);
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1;
  color: var(--ui-text-primary);
}

.result-overview-dims {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.result-overview-dim {
  padding: 14px 16px;
  border-radius: var(--ui-radius-md);
  background: var(--ui-surface-subtle);
  border: 1px solid var(--ui-border);
}

.result-overview-dim__label {
  font-size: var(--font-sm, 15px);
  font-weight: 600;
  color: var(--ui-text-secondary);
}

.result-overview-dim__value {
  margin-top: 8px;
  font-size: clamp(1.45rem, 2.4vw, 1.85rem);
  font-weight: 800;
  color: var(--ui-accent);
  letter-spacing: -0.02em;
  line-height: 1.1;
}

.result-overview-chiprow {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 0 0 16px;
}

.result-overview-chip {
  font-size: var(--font-sm, 15px);
  padding: 6px 12px;
}

.result-overview-narrative {
  padding-top: 4px;
  border-top: 1px dashed var(--ui-border);
}

.result-overview-narrative__k {
  display: inline-block;
  margin-right: 8px;
  font-size: var(--font-xs, 14px);
  font-weight: 800;
  color: var(--ui-text-secondary);
  letter-spacing: 0.02em;
}

.result-overview-overall,
.result-overview-tip {
  margin: 0 0 12px;
  font-size: var(--font-base, 16px);
  line-height: 1.65;
  color: var(--ui-text-primary);
}

.result-overview-tip:last-child {
  margin-bottom: 0;
}

.result-goal-narrative {
  margin-bottom: 20px;
}

.result-goal-narrative__list {
  margin: 6px 0 0;
  padding-left: 1.15rem;
  font-size: 0.9rem;
  line-height: 1.55;
}

.result-goal-narrative__list li {
  margin-bottom: 4px;
}

.result-goal-status-reminder {
  margin-bottom: 20px;
}

.result-goal-status-reminder__list {
  margin: 6px 0 0;
  padding-left: 1.15rem;
  font-size: 0.9rem;
  line-height: 1.55;
}

.result-goal-status-reminder__list li {
  margin-bottom: 4px;
}

.result-goal-status-reminder__next {
  margin: 10px 0 0;
  font-size: 0.88rem;
  line-height: 1.5;
}

.result-rhythm-reminder {
  margin-bottom: 20px;
}

.result-rhythm-reminder__list {
  margin: 6px 0 0;
  padding-left: 1.15rem;
  font-size: 0.9rem;
  line-height: 1.55;
}

.result-rhythm-reminder__list li {
  margin-bottom: 4px;
}

.score-card {
  margin-bottom: 30px;
  padding: 20px 22px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-lg);
  box-shadow: var(--ui-shadow-card);
  transition: box-shadow var(--ui-transition);
}

.result-page--brand-v1 .score-card:hover {
  box-shadow: var(--ui-shadow-card-hover);
}

.result-page--brand-v1 .score-card h3 {
  margin-top: 0;
  font-size: 1.08rem;
  font-weight: 700;
  color: var(--ui-text-primary);
  letter-spacing: -0.02em;
}

.next-round-training-card .next-round-lead {
  margin: 0 0 10px;
  font-size: 0.9rem;
  line-height: 1.5;
}

.next-round-training-card .next-round-overview-hint {
  margin: 0 0 10px;
  font-size: 0.85rem;
  line-height: 1.5;
}

.next-round-training-card .next-round-recommend {
  margin: 0 0 14px;
  font-size: 0.95rem;
  line-height: 1.5;
}

.focus-outcome-card .focus-outcome-line {
  margin: 0 0 10px;
  font-size: 0.95rem;
  line-height: 1.6;
}

.focus-outcome-card .focus-outcome-trend {
  font-size: 0.9rem;
}

.focus-outcome-card .focus-outcome-next {
  margin-bottom: 0;
}

.focus-metric-compare-sub {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px dashed #e4e7ed;
}

.focus-metric-subtitle {
  margin: 0 0 8px;
  font-size: 0.95rem;
  font-weight: 600;
  color: #303133;
}

.focus-metric-lead {
  margin: 0 0 8px;
  font-size: 0.88rem;
  line-height: 1.55;
}

.focus-metric-list {
  margin: 0;
  padding-left: 1.2rem;
  font-size: 0.88rem;
  line-height: 1.55;
  color: #606266;
}

.focus-metric-list li {
  margin-bottom: 4px;
}

.focus-metric-fallback {
  margin: 0;
  font-size: 0.88rem;
}

.next-round-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.next-round-actions {
  margin-top: 4px;
}

.result-closure-actions {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px dashed #dcdfe6;
}

.result-closure-lead {
  margin: 0 0 10px;
  font-size: 0.9rem;
}

.result-closure-dropdown {
  display: inline-block;
  margin-top: 2px;
}

.result-closure-footnote {
  margin: 12px 0 0;
  font-size: 0.82rem;
  line-height: 1.5;
}

.long-session-summary-card {
  border: 1px solid #dcdfe6;
  background: linear-gradient(180deg, #fafcff 0%, #f5f7fa 100%);
}

.session-summary-hint {
  font-size: 13px;
  line-height: 1.5;
}

.session-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-top: 8px;
}

.session-summary-subtitle {
  font-weight: 600;
  margin-bottom: 8px;
  color: #303133;
}

.explain-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 18px;
  margin-top: 16px;
}

@media (min-width: 1280px) {
  .result-content .explain-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.explain-item {
  padding: 16px 18px;
  border-radius: var(--ui-radius-md);
  background: var(--ui-surface);
  border: 1px solid var(--ui-card-border, #e4e7ed);
}

.explain-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: var(--font-base, 16px);
}

.explain-head strong {
  font-weight: 800;
}

.explain-head span {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--ui-accent);
}

.explain-validity {
  margin-bottom: 8px;
  color: #606266;
  font-size: var(--font-sm, 15px);
  line-height: 1.55;
}

.explain-summary {
  margin-bottom: 8px;
  color: #303133;
  font-size: var(--font-base, 16px);
  line-height: 1.65;
}

.explain-list {
  margin: 0;
  padding-left: 18px;
  color: #303133;
}

.content-breakdown-hint {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #e4e7ed;
  font-size: 13px;
  color: #606266;
}

.content-breakdown-title {
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}

.content-breakdown-list {
  margin-top: 4px;
}

.coach-ai-card {
  border-color: #e1f3d8;
  background: linear-gradient(180deg, #f6fff4 0%, #fafafa 100%);
}

.teacher-feedback-card {
  border: 1px solid #e1e4e8;
  background: linear-gradient(165deg, #faf8ff 0%, #f7f9fc 45%, #f5f7fa 100%);
}

.teacher-feedback-card h3 {
  margin-top: 0;
  color: #303133;
  font-size: 1.15rem;
}

.teacher-focus-context {
  margin: 0 0 12px;
  font-size: 0.88rem;
  line-height: 1.55;
}

.cognitive-provider-strip {
  margin: 0 0 14px;
  padding: 12px 14px;
  border-radius: var(--ui-radius-md);
  background: var(--ui-accent-soft);
  border: 1px solid var(--ui-accent-muted);
}

.cognitive-provider-line {
  margin: 4px 0;
  font-size: 13px;
  color: var(--ui-text-secondary);
  line-height: 1.5;
}

.cognitive-provider-line strong {
  color: var(--ui-text-primary);
  font-weight: 600;
}

.teacher-overall {
  margin: 0 0 16px;
  line-height: 1.7;
  color: #303133;
  font-size: var(--font-md, 17px);
}

.teacher-subsection {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #e4e7ed;
}

.teacher-subtitle {
  margin: 0 0 10px;
  font-size: 1.12rem;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.01em;
}

.teacher-bullet-list {
  margin: 0;
}

.teacher-weak-list li {
  color: #606266;
}

.teacher-advice-list li {
  font-weight: 500;
  color: #303133;
}

.teacher-muted {
  margin-top: 4px;
}

.coach-followup-list {
  margin: 0;
  padding-left: 0;
  list-style: none;
}

.coach-followup-item {
  padding: 10px 0;
  border-bottom: 1px solid #ebeef5;
}

.coach-followup-item:last-child {
  border-bottom: none;
}

.fq-question,
.fq-reason {
  margin-bottom: 6px;
  color: #303133;
  line-height: 1.5;
}

.fq-source {
  font-size: 12px;
  color: #909399;
}

.coach-commentary-text {
  margin: 0 0 12px;
  line-height: 1.65;
  color: #303133;
}

.coach-advice-title {
  font-weight: 600;
  margin-bottom: 6px;
  color: #303133;
}

.coach-advice-list {
  margin-top: 0;
}

.total-explain-list {
  margin-bottom: 16px;
}

.ppt-analysis-card {
  border: 1px solid #d9ecff;
  background: linear-gradient(180deg, #f8fbff 0%, #f5f7fa 100%);
}

.score-item {
  margin: 10px 0;
  padding: 8px 0;
  border-bottom: 1px solid #e4e7ed;
}

.score-item:last-child {
  border-bottom: none;
}

.source-tag {
  border-bottom: 1px dashed #e4e7ed;
  color: #606266;
  font-size: 0.95rem;
}

.defense-flow-hint {
  font-size: 0.88rem;
  color: #909399;
  line-height: 1.45;
  border-bottom: none;
  padding-bottom: 0;
}

.module-source-line {
  margin: 8px 0 10px;
  padding: 8px 10px;
  background: #fafafa;
  border-radius: 6px;
  font-size: 0.92rem;
  color: #606266;
  border: 1px solid #ebeef5;
}

.followup-reason-line {
  font-size: 0.9rem;
  background: #fdf6ec;
  border-color: #faecd8;
  color: #606266;
}

.qa-card-tip {
  margin: 10px 0;
  padding: 10px;
  background: #f0f9ff;
  color: #409eff;
  border: 1px solid #d9ecff;
  border-radius: 4px;
  font-size: 0.9em;
  text-align: center;
}

.analysis-overall {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 10px 12px;
  margin-bottom: 10px;
  border-radius: 8px;
  background: #edf6ff;
  border: 1px solid #d9ecff;
}

.analysis-overall-label {
  font-weight: 600;
  color: #606266;
}

.analysis-overall-value {
  font-size: 24px;
  font-weight: 800;
  color: #1f2937;
}

.analysis-subtitle {
  margin: 12px 0 8px;
  font-weight: 700;
  color: #303133;
}

.analysis-slides {
  display: grid;
  gap: 12px;
}

.analysis-slide-row {
  padding: 10px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: white;
}

.analysis-slide-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.analysis-slide-page {
  font-weight: 600;
  color: #303133;
}

.analysis-slide-score {
  font-weight: 700;
  color: #409eff;
}

.analysis-progress-track {
  height: 8px;
  border-radius: 999px;
  background: #eef2f7;
  overflow: hidden;
}

.analysis-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #7cc7ff 0%, #409eff 100%);
  border-radius: 999px;
}

.analysis-preview {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.analysis-hints {
  margin-top: 12px;
  padding: 10px;
  border-radius: 8px;
  background: #fff;
  border: 1px dashed #dcdfe6;
}

.analysis-hint-item {
  margin: 4px 0;
  color: #606266;
}

.result-metrics-collapse {
  margin-bottom: 24px;
}

.metrics-section {
  margin-bottom: 0;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.metric-item {
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
}

.metric-name {
  font-weight: bold;
  margin-bottom: 5px;
}

.metric-value {
  font-size: 1.2em;
  margin-bottom: 5px;
  color: #409eff;
}

.metric-score {
  margin-top: 6px;
  font-size: 0.9em;
  color: #606266;
}

.metric-description {
  font-size: 0.9em;
  color: #909399;
}

.suggestions-section {
  margin-bottom: 30px;
}

.suggestions-list {
  list-style: none;
  padding: 0;
}

.suggestion-item {
  margin: 10px 0;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
  display: flex;
  align-items: flex-start;
}

.suggestion-category {
  font-weight: bold;
  margin-right: 10px;
  min-width: 80px;
  color: #409eff;
}

.suggestion-content {
  flex: 1;
}

.result-inference-chain {
  margin: 0.5rem 0 0;
  font-size: 0.85rem;
  line-height: 1.5;
}

.result-demo-mode-banner {
  width: 100%;
  max-width: min(var(--app-content-max-width, 1360px), 100%);
  margin-bottom: 14px;
}

.result-demo-mode-banner__body {
  margin: 0 0 8px;
  font-size: 0.88rem;
}

.result-demo-mode-banner__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.result-demo-soft {
  opacity: 0.68;
}

.result-page--demo-mode .result-overview-card {
  border: 2px solid rgba(64, 158, 255, 0.55);
  box-shadow: 0 10px 28px rgba(64, 158, 255, 0.12);
}

.result-page--demo-mode .teacher-feedback-card {
  border: 2px solid rgba(103, 194, 58, 0.45);
}

.result-inference-chain--demo-spotlight {
  font-weight: 600;
  color: #303133 !important;
  font-size: 0.95rem;
}

@media (max-width: 1024px) {
  .result-page {
    padding: 24px 14px 40px;
  }

  .result-hero-v1__top {
    flex-direction: column;
    align-items: flex-start;
  }

  .result-hero-v1__chips {
    width: 100%;
  }

  .result-overview-scoreblock {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

@media (max-width: 768px) {
  .result-page {
    padding: 20px 10px 36px;
  }

  .result-overview-card {
    padding: 18px 16px;
  }

  .result-overview-dims {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .explain-grid {
    grid-template-columns: 1fr;
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .session-summary-grid {
    grid-template-columns: 1fr;
  }

  .result-next-actions__primary,
  .result-next-actions__aux {
    flex-direction: column;
    align-items: stretch;
  }

  .result-next-actions__primary .el-button,
  .result-next-actions__aux .el-button {
    width: 100%;
    margin: 0;
  }

  .result-next-actions__primary :deep(.el-dropdown) {
    width: 100%;
  }

  .result-next-actions__primary :deep(.el-dropdown .el-button) {
    width: 100%;
  }

  .next-round-chips {
    flex-direction: column;
    align-items: stretch;
  }

  .next-round-chips .el-button {
    width: 100%;
    margin: 0;
  }

  .next-round-actions .el-button {
    width: 100%;
  }

  .result-closure-dropdown {
    width: 100%;
  }

  .result-closure-dropdown :deep(.el-button) {
    width: 100%;
  }

  .analysis-slide-head {
    flex-wrap: wrap;
    gap: 6px;
  }
}

@media print {
  .result-hero-2col {
    display: block !important;
  }

  .result-hero-2col .result-primary-actions--hero-dock {
    margin-top: 12px;
  }

  .no-print {
    display: none !important;
  }

  .result-aux-for-print .el-collapse-item__wrap,
  .result-aux-for-print .el-collapse-item__content {
    display: block !important;
    height: auto !important;
  }

  .result-aux-for-print .el-collapse-item__header,
  .result-aux-for-print .el-collapse-item__arrow {
    display: none !important;
  }

  .result-aux-for-print.el-collapse {
    border: none;
  }
}
</style>