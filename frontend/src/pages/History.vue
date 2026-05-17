<template>
  <div class="history-page history-page--brand-v1 history-page--admin-v2 ui-page-frame ui-page-shell-inset">
    <header class="history-page-head history-page-head--admin">
      <p class="ui-page-header__eyebrow">复盘台</p>
      <h1 class="ui-page-title">{{ SECTION.historyTitle }}</h1>
    </header>

    <el-alert
      v-if="showReportContextHint"
      class="history-report-nav-hint history-report-nav-hint--compact no-print"
      type="info"
      closable
      show-icon
      title="打开训练报告"
      @close="clearReportContextHint"
    >
      <p class="history-report-nav-hint__one muted">在列表中点「查看详情」进入该次结果，再点「查看训练报告」。</p>
    </el-alert>

    <div v-if="loading" class="history-loading-panel" aria-busy="true" aria-live="polite">
      <p class="history-loading-panel__label muted">{{ PAGE_LOADING.history.label }}</p>
      <p class="history-loading-panel__hint muted">{{ PAGE_LOADING.history.hint }}</p>
      <el-skeleton :rows="8" animated />
    </div>

    <div v-else-if="error" class="history-error-panel">
      <el-alert type="error" :closable="false" show-icon :title="PAGE_ERROR_ALERT_TITLE.history">
        <p class="history-error-panel__body">{{ historyErrorUserMessage }}</p>
        <div class="history-error-panel__actions history-page-error-actions">
          <el-button type="primary" @click="retryLoadHistory">重试</el-button>
          <el-dropdown trigger="click" class="history-page-actions-more">
            <el-button type="default" plain
              >其他路线
              <span class="ui-dropdown-caret" aria-hidden="true">▾</span></el-button
            >
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="goHomeFromHistory">返回首页</el-dropdown-item>
                <el-dropdown-item @click="goTrainingFromHistory">去训练</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-alert>
    </div>

    <div v-else class="history-main history-main--admin ui-stack">
      <section
        v-if="history.length > 0"
        class="history-summary-bar ui-surface no-print"
        role="region"
        aria-label="训练记录概览"
      >
        <div class="history-summary-bar__metrics">
          <div class="history-summary-metric">
            <span class="history-summary-metric__k">有效训练</span>
            <span class="history-summary-metric__v">{{ validHistoryItemCount }} 条</span>
          </div>
          <div class="history-summary-metric">
            <span class="history-summary-metric__k">当前列表</span>
            <span class="history-summary-metric__v">{{ displayHistory.length }} 条</span>
          </div>
          <div v-if="displayHistory.length > 0" class="history-summary-metric">
            <span class="history-summary-metric__k">最佳总分</span>
            <span class="history-summary-metric__v">{{ statsSummary.bestTotal }}</span>
          </div>
          <div v-if="displayHistory.length > 0" class="history-summary-metric">
            <span class="history-summary-metric__k">近5次均分</span>
            <span class="history-summary-metric__v">{{ statsSummary.lastFiveAvgTotal }}</span>
          </div>
          <div v-if="displayHistory.length >= 2" class="history-summary-metric">
            <span class="history-summary-metric__k">较上次</span>
            <span
              class="history-summary-metric__v history-summary-metric__v--trend"
              :class="statsSummary.trendClass"
              >{{ statsSummary.lastVsPrevText }}</span
            >
          </div>
          <div v-if="historyNextPlanFocusLine" class="history-summary-metric history-summary-metric--soft">
            <span class="history-summary-metric__k">建议专项</span>
            <span class="history-summary-metric__v muted">{{ historyNextPlanFocusLine }}</span>
          </div>
        </div>
        <div class="history-summary-bar__filters muted" aria-label="当前筛选">
          <span
            >浏览 <strong class="history-summary-bar__strong">{{ HISTORY_FOCUS_FILTER_LABELS[selectedFocusFilter] || selectedFocusFilter }}</strong></span
          >
          <span class="history-summary-bar__dot" aria-hidden="true">·</span>
          <span
            >范围
            <strong class="history-summary-bar__strong">{{
              validRecordFilter === 'valid' ? '仅统计中' : '含未纳入统计'
            }}</strong></span
          >
        </div>
      </section>

      <el-alert
        v-if="historyEmptyMode === 'no_valid_history'"
        class="history-invalid-only-alert"
        type="info"
        :closable="false"
        show-icon
        title="目前还没有可参与统计与趋势复盘的记录"
      >
        <p class="history-invalid-only-alert__body">
          你可能已有练习行，但尚未有符合「统计中」条件的一条。完成并提交后概览会丰富；也可在上方筛选区切到「含未纳入统计的全部记录」先浏览。
        </p>
        <el-button type="primary" size="small" class="history-invalid-only-cta" @click="goFirstTrainingFromHistory">
          去训练，完成一轮可参与统计的练习
        </el-button>
      </el-alert>

      <div v-if="history.length === 0 && selectedFocusFilter === 'all'" class="history-empty-card">
        <h2 class="history-empty-title">这里还没有历史记录</h2>
        <p class="history-empty-lead muted">用本账号开始训练后，记录会按时间排在这里；有数据后可用上方筛选区调整专项与统计范围。</p>
        <el-button type="primary" @click="goFirstTrainingFromHistory">去训练</el-button>
        <p class="history-empty-foot muted">仅跳转到训练页，不会自动开始录音或训练。</p>
      </div>
      <div v-else-if="history.length === 0" class="history-filter-empty muted">
        <p>在当前的训练重点下暂时还没有记录。可切回「全部」、换其它专项，或开一轮新练习；有数据后在上方筛选区调整条件。</p>
        <el-button type="primary" plain size="small" class="history-filter-empty-cta" @click="goFirstTrainingFromHistory">
          去训练
        </el-button>
        <p class="history-filter-empty-foot muted">仅跳转，不会自动开始训练。</p>
      </div>

      <template v-if="history.length > 0">
      <div id="history-anchor-recent" tabindex="-1" class="history-recent-block inpage-nav-target">
      <div class="history-admin-console history-admin-console--grid no-print">
        <div id="history-anchor-refine" tabindex="-1" class="history-filter-toolbar ui-surface ui-surface--subtle">
          <div class="history-filter-toolbar__head">
            <p class="history-filter-toolbar__title">筛选与查看</p>
            <p class="history-filter-toolbar__hint muted">
              选择会更新列表与右侧趋势摘要；一般无需手动刷新。
            </p>
          </div>
          <div class="history-filter-toolbar__body">
            <div class="history-filter-toolbar__chunk">
              <h3 class="history-filter-toolbar__h">训练重点</h3>
              <section class="focus-filter-bar" aria-label="按训练重点筛选">
                <el-radio-group
                  v-model="selectedFocusFilter"
                  size="default"
                  class="focus-filter-group focus-filter-group--history"
                  aria-label="按训练重点筛选"
                >
                  <el-radio-button label="all">全部</el-radio-button>
                  <el-radio-button label="none">常规</el-radio-button>
                  <el-radio-button label="language">语言</el-radio-button>
                  <el-radio-button label="posture">仪态</el-radio-button>
                  <el-radio-button label="qa">问答</el-radio-button>
                  <el-radio-button label="content">内容</el-radio-button>
                </el-radio-group>
              </section>
            </div>
            <div class="history-filter-toolbar__chunk">
              <h3 class="history-filter-toolbar__h">是否纳入统计</h3>
              <section class="valid-filter-bar" aria-label="按是否计为有效筛选">
                <div class="valid-filter-row">
                  <el-radio-group
                    v-model="validRecordFilter"
                    size="default"
                    class="focus-filter-group focus-filter-group--history-valid"
                    aria-label="仅统计中或全部记录"
                  >
                    <el-radio-button label="valid">仅看统计中的</el-radio-button>
                    <el-radio-button label="all">含未纳入统计的全部记录</el-radio-button>
                  </el-radio-group>
                  <el-button
                    v-if="invalidHistoryCount > 0"
                    type="warning"
                    plain
                    size="default"
                    class="history-clear-invalid-btn"
                    @click="confirmClearInvalidTraining"
                  >
                    处理未纳入项（{{ invalidHistoryCount }} 条）
                  </el-button>
                </div>
                <p v-if="invalidHistoryCount > 0" class="history-manage-hint muted">
                  仅清理「未纳入统计」条目，不可恢复；已纳入记录不受影响。
                </p>
              </section>
            </div>
          </div>
          <p class="history-training-resume-hint muted">
            进入训练页后可使用「继续上次训练方式」对齐最近一次可纳入统计的练习（不会自动开始训练）。
          </p>
        </div>
        <aside
          v-if="displayHistory.length > 0"
          class="history-trend-compact ui-surface ui-surface--subtle"
          aria-label="趋势摘要"
        >
          <p class="history-trend-compact__eyebrow">趋势</p>
          <p class="history-trend-compact__line">{{ historyTrendConclusionLine }}</p>
          <ul v-if="narrativeLines.length" class="history-trend-compact__bullets muted">
            <li v-for="(line, i) in narrativeLines.slice(0, 2)" :key="`tc-${i}`">{{ line }}</li>
          </ul>
          <p class="history-trend-compact__foot muted">列表 {{ displayHistory.length }} 条 · 更多曲线与统计在下方「深度复盘」</p>
        </aside>
        <aside
          v-else
          class="history-trend-compact history-trend-compact--empty ui-surface ui-surface--subtle muted"
          aria-label="趋势摘要"
        >
          <p class="history-trend-compact__eyebrow">趋势</p>
          <p class="history-trend-compact__line">当前列表暂无数据。放宽筛选或切换专项后，摘要会与列表同步更新。</p>
        </aside>
      </div>

      <div v-if="displayHistory.length === 0" class="filter-empty" role="status">
        <p v-if="validRecordFilter === 'valid' && history.length > 0" class="filter-empty__main">
          在「仅看统计中」时，未纳入记录会暂时不出现在本列表。
          <a
            href="#history-anchor-refine"
            class="ui-inpage-nav__link filter-empty__anchor"
            @click="onInpageNavLinkClick"
            >去精细筛选</a
          >，改为「含未纳入统计的全部记录」或换训练重点。
        </p>
        <p v-else class="filter-empty__main">
          当前没有符合条件的记录。
          <a
            href="#history-anchor-refine"
            class="ui-inpage-nav__link filter-empty__anchor"
            @click="onInpageNavLinkClick"
            >去精细筛选</a
          >
          放宽条件，或把范围切为「含全部」。
        </p>
      </div>

      <div v-else class="history-list history-list-panel">
      <div class="history-list-panel__head">
        <p class="history-tier-eyebrow history-list-eyebrow">记录列表</p>
        <p class="history-list-panel__meta muted">共 {{ displayHistory.length }} 条 · 主操作：查看详情</p>
      </div>
      <div
        v-for="item in displayHistory"
        :key="item.session_id"
        class="history-item history-item--v1"
        :class="{ 'history-item--invalid': item.training_valid === false }"
      >
        <div class="history-item-top">
          <div class="history-item-main">
            <div class="history-item-title-row item-header item-header--compact">
              <h3 class="history-item-session-title">{{ item.session_name }}</h3>
              <span
                v-if="item.training_valid === false"
                class="ui-tag ui-tag--status-invalid history-item-status-tag"
                >未纳入统计</span
              >
            </div>
            <div class="history-item-primary history-item-primary--scan" aria-label="本条训练摘要">
              <div class="hip-block hip-block--time">
                <span class="hip-k">时间</span>
                <span class="hip-v">{{ formatDate(item.timestamp || item.created_at) }}</span>
              </div>
              <div class="hip-block hip-block--score">
                <span class="hip-k">总分</span>
                <span class="hip-v hip-v--score">{{ formatScore(item.total_score) }}</span>
              </div>
              <div class="hip-block hip-block--focus">
                <span class="hip-k">训练重点</span>
                <span class="hip-v">
                  <span class="ui-tag" :class="historyItemFocusTagClass(item)">{{
                    historyItemTrainingFocusShort(item)
                  }}</span>
                </span>
              </div>
            </div>
          </div>
          <div class="history-item-primary-cta">
            <el-button type="primary" @click="viewDetail(item.session_id)">查看详情</el-button>
          </div>
        </div>

        <div class="history-item-subrow no-print">
          <div class="history-item-subrow__left">
            <el-button type="primary" text size="small" @click="continueTrainingFromHistory(item)">
              {{ historyContinueTrainingLabel(item) }}
            </el-button>
            <el-button
              text
              type="default"
              size="small"
              :aria-expanded="isHistoryItemDetailOpen(item.session_id)"
              :aria-controls="`history-item-detail-${String(item.session_id)}`"
              :id="`history-item-expand-btn-${String(item.session_id)}`"
              @click="toggleHistoryItemDetail(item.session_id)"
            >
              {{ isHistoryItemDetailOpen(item.session_id) ? '收起详情' : '展开详情' }}
            </el-button>
          </div>
          <el-dropdown trigger="click" class="history-page-actions-more history-item-subrow__manage">
            <el-button type="default" plain size="small" class="history-item-manage-btn">
              本记录
              <span class="ui-dropdown-caret" aria-hidden="true">▾</span>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="confirmDeleteHistoryItem(item)">
                  <span class="history-dropdown-danger-label">删除本记录</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <div
          v-show="isHistoryItemDetailOpen(item.session_id)"
          :id="`history-item-detail-${String(item.session_id)}`"
          class="history-item-details"
          role="region"
          :aria-labelledby="`history-item-expand-btn-${String(item.session_id)}`"
        >
          <div
            v-if="item.training_valid !== false"
            class="hip-block hip-block--inline valid-status-block"
          >
            <span class="hip-k">是否纳入总览与趋势</span>
            <span class="ui-tag ui-tag--status-valid">已纳入统计</span>
          </div>
          <p
            v-else
            class="history-item-detail-preface muted"
          >
            本条未纳入总览与趋势；下方为环境与信号、专项对照与各项得分，便于你核对当次情况。
          </p>
          <div class="modality-row">
            <span class="modality" :class="modalityClass(item.audio_valid)">
              音频：{{ modalityLabel(item.audio_valid) }}
            </span>
            <span class="modality" :class="modalityClass(item.vision_valid)">
              视觉：{{ modalityLabel(item.vision_valid) }}
            </span>
            <span class="ui-tag history-training-focus-badge" :class="historyItemFocusTagClass(item)">{{
              historyItemTrainingFocusShort(item)
            }}</span>
            <span
              v-if="historyItemFocusTrendShort(item)"
              class="mode-badge history-focus-trend-badge"
              >{{ historyItemFocusTrendShort(item) }}</span
            >
            <span v-if="item.scoring_profile_label" class="mode-badge mode-badge--trailing">{{
              item.scoring_profile_label
            }}</span>
          </div>
          <p v-if="item.training_valid === false" class="history-invalid-reason muted">
            {{ historyInvalidReasonLine(item) }}
          </p>
          <div v-if="historyItemFocusMetaVisible(item)" class="focus-meta-block muted">
            <p class="focus-meta-line">
              <strong>训练重点：</strong>{{ historyItemFocusCardLabel(item) }}
            </p>
            <p class="focus-meta-line">
              <strong>本专项核心分：</strong>{{ historyItemFocusPrimaryDisplay(item) }}
            </p>
            <p class="focus-meta-line">
              <strong>和上一次同专项比：</strong>{{ historyItemFocusVsPrevDisplay(item) }}
            </p>
            <p class="focus-meta-line">
              <strong>最近趋势：</strong>{{ historyItemFocusTrendLabel(item) }}
            </p>
            <p v-if="historyItemKeyMetricsVsPrev(item)" class="focus-meta-line">
              <strong>关键指标较上次同专项：</strong>{{ historyItemKeyMetricsVsPrev(item) }}
            </p>
          </div>
          <div class="item-scores">
            <div class="score-item total">
              <span class="label">总分</span>
              <span class="value">{{ formatScore(item.total_score) }}</span>
            </div>
            <div class="score-item">
              <span class="label">语言分</span>
              <span class="value">{{ formatScore(item.language_score) }}</span>
            </div>
            <div class="score-item">
              <span class="label">仪态分</span>
              <span class="value">{{ formatScore(item.posture_score) }}</span>
            </div>
            <div class="score-item">
              <span class="label">内容分</span>
              <span class="value">{{ formatScore(item.content_score) }}</span>
            </div>
            <div class="score-item">
              <span class="label">问答分</span>
              <span class="value">{{ formatScore(item.qa_score) }}</span>
            </div>
          </div>
        </div>
      </div>
      </div>
      </div>

      <el-collapse
        id="history-anchor-overview"
        tabindex="-1"
        v-model="historyOverviewCollapse"
        class="history-collapse-block history-collapse--overview history-collapse--sink inpage-nav-target no-print"
      >
        <el-collapse-item name="ov" title="总览、目标与阶段（可展开）">
      <section class="valid-training-overview ui-surface ui-panel--hero history-overview-surface">
        <p class="history-tier-eyebrow">总览</p>
        <h2 class="overview-title">{{ SECTION.validTrainingOverview }}</h2>
        <p v-if="overviewDegradedLine" class="overview-degraded muted">{{ overviewDegradedLine }}</p>
        <ul v-else-if="overviewBodyLines.length" class="overview-body-list">
          <li v-for="(ln, i) in overviewBodyLines" :key="`ov-${i}`">{{ ln }}</li>
        </ul>
        <p v-else class="overview-degraded muted">总览暂不可用，请稍后刷新。</p>
        <div v-if="historyGoalSummaryLines.length" class="history-goal-summary">
          <p class="history-goal-summary__title">训练目标（摘要）</p>
          <ul class="history-goal-summary__list muted">
            <li v-for="(ln, i) in historyGoalSummaryLines" :key="`hgs-${i}`">{{ ln }}</li>
          </ul>
        </div>
        <div v-if="historyWeeklyReviewVisible" class="history-weekly-review">
          <p class="history-weekly-review__title">{{ SECTION.stageReviewSummary }}</p>
          <ul class="history-weekly-review__list muted">
            <li v-for="(ln, i) in historyWeeklyReviewLines" :key="`hwr-${i}`">{{ ln }}</li>
          </ul>
        </div>
        <div v-if="historyNextPlanVisible" class="history-next-plan">
          <p class="history-next-plan__title">{{ SECTION.nextStagePlan }}</p>
          <p class="history-next-plan__action muted">
            <span class="history-next-plan__k">当前阶段建议：</span>{{ historyNextPlan.next_plan_action_label }}
          </p>
          <p class="history-next-plan__body">{{ historyNextPlan.next_plan_user_line }}</p>
          <p v-if="historyNextPlanFocusLine" class="history-next-plan__focus muted">
            <span class="history-next-plan__k">建议专项：</span>{{ historyNextPlanFocusLine }}
          </p>
          <p v-if="historyNextPlanReasonLine" class="history-next-plan__reason muted">
            <span class="history-next-plan__k">理由：</span>{{ historyNextPlanReasonLine }}
          </p>
        </div>
        <div v-if="historyStageSummaryVisible" class="history-stage-summary">
          <p class="history-stage-summary__title">阶段总结（规则版）</p>
          <p class="history-stage-k muted">当前阶段主要进步</p>
          <ul class="history-stage-list muted">
            <li v-for="(ln, i) in historyStageMainLines" :key="`hst-m-${i}`">{{ ln }}</li>
          </ul>
          <p class="history-stage-k muted">当前阶段仍需继续关注</p>
          <ul class="history-stage-list muted">
            <li v-for="(ln, i) in historyStageNeedLines" :key="`hst-n-${i}`">{{ ln }}</li>
          </ul>
        </div>
        <div v-if="historyRhythmSummaryLines.length" class="history-rhythm-summary">
          <p class="history-rhythm-summary__title">训练节奏（摘要）</p>
          <ul class="history-rhythm-summary__list muted">
            <li v-for="(ln, i) in historyRhythmSummaryLines" :key="`hrh-${i}`">{{ ln }}</li>
          </ul>
        </div>
      </section>
        </el-collapse-item>
      </el-collapse>

      <el-collapse
        id="history-anchor-more"
        tabindex="-1"
        v-model="historyMoreInsightsCollapse"
        v-if="displayHistory.length > 0"
        class="history-collapse-block history-collapse--more inpage-nav-target no-print"
      >
        <el-collapse-item name="more" title="深度复盘：专项摘要、完整趋势、统计与曲线（可展开）">
      <section v-if="showFocusReviewPanel" class="focus-review-summary ui-surface history-focus-review-card">
        <p class="history-tier-eyebrow history-tier-eyebrow--in-card">{{ SECTION.focusReview }}</p>
        <h2 class="focus-review-h2">{{ focusReviewCardTitle }}</h2>
        <p class="focus-review-subline muted">基于当前筛选与列表范围、该专项近期训练，由规则生成摘要，便于与曲线对照。</p>
        <p v-if="focusReview?.summary" class="focus-review-body focus-review-body--text">{{ focusReview.summary }}</p>
        <ul v-if="focusReviewBulletLines.length" class="focus-review-bullets">
          <li v-for="(ln, i) in focusReviewBulletLines" :key="`frb-${i}`">{{ ln }}</li>
        </ul>
        <p v-if="focusReview?.nextAction" class="focus-review-next">
          <strong>下一轮建议：</strong>{{ focusReview.nextAction }}
        </p>
      </section>
      <section
        v-else-if="showFocusReviewPlaceholder"
        class="focus-review-placeholder ui-hint history-focus-placeholder"
      >
        <p class="focus-review-placeholder__title">专项复盘摘要在你选好专项后展示</p>
        <p class="focus-review-placeholder__body muted">
          在上方「筛选与查看」里将训练重点选为<strong>语言 / 仪态 / 问答 / 内容</strong>之一（不要停在「全部」或「常规」），专项要点会出现在本区。
        </p>
      </section>

      <section v-if="displayHistory.length > 0" class="trend-summary history-subsection ui-surface history-trend-card history-trend-card--sink">
      <p class="history-tier-eyebrow history-tier-eyebrow--in-section">完整趋势说明</p>
      <h2 class="history-trend-sink__h2">最近训练趋势总结</h2>
      <ul class="trend-summary-list trend-summary-list--compact">
        <li v-for="(line, i) in narrativeLines" :key="i">{{ line }}</li>
      </ul>
      </section>

      <section v-if="displayHistory.length > 0" class="stats-summary history-stats-card history-stats-card--sink">
      <div class="stat-card">
        <span class="stat-label">总训练次数</span>
        <span class="stat-value">{{ statsSummary.totalSessions }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">最近 5 次平均总分</span>
        <span class="stat-value">{{ statsSummary.lastFiveAvgTotal }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">最佳总分</span>
        <span class="stat-value">{{ statsSummary.bestTotal }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">较上一次</span>
        <span class="stat-value" :class="statsSummary.trendClass">{{ statsSummary.lastVsPrevText }}</span>
      </div>
      </section>

      <section v-if="displayHistory.length > 0" class="charts-section">
      <h2>进步曲线</h2>
      <p class="charts-hint">时间从左到右为从旧到新；未纳入统计或缺少得分的点会断开（断线），不表示图坏了。</p>
      <div class="charts-grid">
        <div class="chart-card">
          <h3>总分趋势</h3>
          <LineSpark
            :labels="chartLabels"
            :values="seriesTotal"
            color="#5b4fcf"
          />
        </div>
        <div class="chart-card">
          <h3>语言分趋势</h3>
          <LineSpark
            :labels="chartLabels"
            :values="seriesLanguage"
            color="#409eff"
          />
        </div>
        <div class="chart-card">
          <h3>仪态分趋势</h3>
          <LineSpark
            :labels="chartLabels"
            :values="seriesPosture"
            color="#67c23a"
          />
        </div>
      </div>
      </section>

      <div v-if="displayHistory.length >= 2 && trendMessage" class="trend-message" :class="trendType">
        {{ trendMessage }}
      </div>

      <div v-if="displayHistory.length > 0 && bestScoreMessage" class="best-score">
        {{ bestScoreMessage }}
      </div>

        </el-collapse-item>
      </el-collapse>

      </template>
    </div>

    <div v-if="!loading && !error" class="history-page-sink-hints no-print">
      <el-alert class="history-demo-hint history-demo-hint--sink" type="info" :closable="false" show-icon title="比赛演示提示">
        <p class="history-demo-hint__body muted">
          复盘后可回首页用「比赛演示入口」手动串起训练 → 结果 → 报告 → 历史（不会自动开始训练）。
        </p>
        <el-button type="primary" size="small" plain class="history-demo-hint__cta" @click="goHomeFromHistory">
          返回演示首页
        </el-button>
      </el-alert>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, h, defineComponent, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getJson, postJson, deleteJson } from '../api/base'
import { toUserFacingMessage } from '../utils/userFacingError'
import { pageFeedback, trainingConfirmDanger } from '../utils/pageFeedback'
import {
  readAppPreferences,
  preferencesSnapshotForLog,
  TRAINING_FOCUS_HANDOFF_KEY,
  TRAINING_RUNTIME_SNAPSHOT_KEY,
} from '../utils/appPreferences'
import {
  readUserScopedItem,
  writeUserScopedItem,
  getActiveUserId,
  removeUserScopedItem,
} from '../utils/userScopedStorage'
import { hydrateAccountSettings } from '../utils/accountSettingsSync'
import {
  readTrainingGoals,
  computeTrainingGoalProgress,
  hasActiveTrainingGoals,
  TRAINING_GOAL_FOCUS_LABEL,
  TRAINING_GOALS_CHANGED_EVENT,
} from '../utils/trainingGoals'
import { computeGoalStatusPack, buildStageSummary } from '../utils/trainingGoalStatus'
import { computeTrainingRhythm, buildHistoryRhythmSummaryLines } from '../utils/trainingStreaks'
import { computeWeeklyTrainingReview, buildHistoryStageReviewLines } from '../utils/trainingWeeklyReview'
import { computeNextTrainingPlan } from '../utils/nextTrainingPlan'
import { SECTION, TRAINING_FOCUS_LABEL, trainingFocusLabel } from '../constants/productTerms'
import { PAGE_LOADING, PAGE_ERROR_ALERT_TITLE } from '../constants/pageStatusCopy'

const HISTORY_DATA_CHANGED_EVENT = 'mianshi-history-changed'
const HISTORY_UI_STORAGE_KEY = 'mianshi_history_ui_v1'

function notifyHistoryDataChanged() {
  try {
    window.dispatchEvent(new Event(HISTORY_DATA_CHANGED_EVENT))
  } catch (_) {}
}

const route = useRoute()
const router = useRouter()

const showReportContextHint = computed(() => String(route.query.need_report_context || '') === '1')
function clearReportContextHint() {
  const nextQuery = { ...route.query }
  delete nextQuery.need_report_context
  router.replace({ name: 'History', query: nextQuery })
}
const history = ref([])
/** 无专项筛选的完整列表，用于训练目标进度（与当前列表筛选解耦） */
const historyForGoals = ref([])
const loading = ref(false)
const error = ref('')

const historyGoalsRevision = ref(0)
function bumpHistoryGoalsRevision() {
  historyGoalsRevision.value++
}

const historyErrorUserMessage = computed(() =>
  error.value ? toUserFacingMessage(error.value, '暂时无法加载历史记录，请稍后重试。') : ''
)

function parseHistoryUiState(raw) {
  try {
    const o = JSON.parse(raw)
    if (!o || typeof o !== 'object') return null
    const focus = String(o.focus_filter || 'all')
    const valid = o.valid_record_filter === 'all' ? 'all' : 'valid'
    if (!['all', 'none', 'language', 'posture', 'qa', 'content'].includes(focus)) return null
    return { focus, valid }
  } catch {
    return null
  }
}

function readStoredHistoryFilters() {
  const uid = getActiveUserId()
  const raw = readUserScopedItem(localStorage, HISTORY_UI_STORAGE_KEY, uid, { migrateLegacy: true })
  const parsed = raw ? parseHistoryUiState(raw) : null
  const prefs = readAppPreferences()
  const defValid = prefs.history_valid_only_default !== false ? 'valid' : 'all'
  if (!parsed) {
    return { focus: 'all', valid: defValid, from: 'defaults' }
  }
  return { focus: parsed.focus, valid: parsed.valid, from: 'storage' }
}

/** all | none | language | posture | qa | content（具体值在 onMounted 经 hydrate 后再对齐账号偏好） */
const selectedFocusFilter = ref('all')

/** valid：默认仅展示有效训练；all：含无效记录 */
const validRecordFilter = ref('valid')

const historyOverviewCollapse = ref([])
const historyMoreInsightsCollapse = ref([])

/** 单条记录卡「展开详情」：按 session_id 记布尔，仅 UI，不改接口与列表逻辑。 */
const historyItemDetailOpen = ref(/** @type {Record<string, boolean>} */ ({}))
function isHistoryItemDetailOpen(sessionId) {
  return !!historyItemDetailOpen.value[String(sessionId)]
}
function toggleHistoryItemDetail(sessionId) {
  const k = String(sessionId)
  historyItemDetailOpen.value = { ...historyItemDetailOpen.value, [k]: !historyItemDetailOpen.value[k] }
}

function persistHistoryUiFilters() {
  try {
    writeUserScopedItem(
      localStorage,
      HISTORY_UI_STORAGE_KEY,
      JSON.stringify({
        v: 1,
        focus_filter: selectedFocusFilter.value,
        valid_record_filter: validRecordFilter.value,
      })
    )
  } catch (_) {}
}

watch([selectedFocusFilter, validRecordFilter], () => {
  persistHistoryUiFilters()
}, { flush: 'post' })

const REVIEWABLE_FOCUS = new Set(['language', 'posture', 'qa', 'content'])

/** 后端 /history?review_focus= 返回的专项复盘 */
const focusReview = ref(null)

const validTrainingOverview = ref(null)

function overviewFocusFullLabel(k) {
  const raw = k == null || k === '' ? 'none' : k
  return trainingFocusLabel(raw)
}

function focusDistributionHumanLine(dist) {
  const labels = { ...TRAINING_FOCUS_LABEL }
  const keys = ['language', 'posture', 'qa', 'content', 'none']
  const pairs = keys.map((k) => ({ k, n: Number(dist?.[k]) || 0 }))
  const maxN = Math.max(0, ...pairs.map((p) => p.n))
  if (maxN <= 0) return ''
  const tops = pairs.filter((p) => p.n === maxN && p.n > 0)
  if (tops.length > 1) {
    return '最近几次有效训练里，专项分布比较平均，可多关注分项里最弱的一环。'
  }
  return `其中「${labels[tops[0].k]}」出现最多（${maxN} 次）。`
}

function formatOverviewDateTime(ts) {
  if (ts == null || String(ts).trim() === '') return '—'
  try {
    return new Date(ts).toLocaleString()
  } catch (_) {
    return String(ts)
  }
}

const overviewDegradedLine = computed(() => {
  const o = validTrainingOverview.value
  if (!o) return ''
  if (o.overview_ready === true && (o.valid_count_recent || 0) > 0) return ''
  return (
    o.overview_message ||
    '暂无足够有效训练数据，先完成几次有效训练后这里会汇总近期情况。'
  )
})

const overviewBodyLines = computed(() => {
  const o = validTrainingOverview.value
  if (!o || !o.overview_ready || !(o.valid_count_recent > 0)) return []
  const n = o.valid_count_recent
  const cap = o.recent_window_size || 7
  const avg = o.avg_total_score_recent
  const avgTxt =
    avg != null && Number.isFinite(Number(avg)) ? Number(avg).toFixed(1) : '—'
  const lines = []
  lines.push(
    `最近 ${n} 次有效训练（统计窗口最多 ${cap} 次）中，平均总分约 ${avgTxt} 分。`
  )
  const distLn = focusDistributionHumanLine(o.focus_distribution_recent || {})
  if (distLn) lines.push(distLn)
  lines.push(
    `最近一次有效训练在 ${formatOverviewDateTime(o.latest_valid_created_at)}，训练重点为「${overviewFocusFullLabel(
      o.latest_valid_training_focus
    )}」。`
  )
  lines.push(`当前更建议继续：${overviewFocusFullLabel(o.recommended_continue_focus)}。`)
  const sparse = String(o.overview_message || '').trim()
  if (sparse) lines.push(sparse)
  return lines
})

const historyGoalSummaryLines = computed(() => {
  void historyGoalsRevision.value
  const p = computeTrainingGoalProgress({
    goals: readTrainingGoals(),
    historyList: historyForGoals.value,
    overview: validTrainingOverview.value,
  })
  const g = p.goals
  if (!hasActiveTrainingGoals(g)) return []
  const lines = []
  if (g.target_total_score != null) {
    const bt = p.bestTotal != null ? `${p.bestTotal.toFixed(1)}` : '—'
    const gap =
      p.gapToTarget != null && p.gapToTarget > 0 ? `，距目标还差 ${p.gapToTarget.toFixed(1)} 分` : ''
    lines.push(`目标总分 ${Number(g.target_total_score).toFixed(1)}：当前最好 ${bt}${gap}`)
  }
  if (g.target_focus) {
    const lab = TRAINING_GOAL_FOCUS_LABEL[g.target_focus] || g.target_focus
    const fb = p.focusBest != null ? `约 ${p.focusBest.toFixed(1)} 分` : '暂无可对照分数'
    lines.push(`目标专项「${lab}」——有效训练中该项最高 ${fb}`)
  }
  if (p.validCountProgress) {
    lines.push(`有效训练次数进度：${p.validCountProgress.current} / ${p.validCountProgress.target}`)
  }
  return lines
})

const historyWeeklyReview = computed(() => {
  void historyGoalsRevision.value
  try {
    return computeWeeklyTrainingReview(historyForGoals.value, {
      overview: validTrainingOverview.value,
      goals: readTrainingGoals(),
    })
  } catch (e) {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.warn('[History] historyWeeklyReview', e)
    }
    return null
  }
})

const historyWeeklyReviewLines = computed(() => buildHistoryStageReviewLines(historyWeeklyReview.value || null))

const historyWeeklyReviewVisible = computed(() => {
  if (loading.value || error.value) return false
  return (historyWeeklyReview.value?.weekly_valid_count || 0) > 0
})

watch(validTrainingOverview, (o) => {
  console.log('[History.overview] valid_training_overview=', o)
})

watch(
  historyWeeklyReview,
  (r) => {
    if (loading.value || error.value) return
    if (!r?.weekly_valid_count) return
    console.log('[History.review_stage] summary=', r.weekly_trend_summary)
    console.log('[History.review_stage] next_action=', r.weekly_next_focus)
  },
  { flush: 'post' }
)

const validHistoryItemCount = computed(
  () => (history.value || []).filter((it) => it?.training_valid !== false).length
)

const invalidHistoryCount = computed(
  () => (history.value || []).filter((it) => it?.training_valid === false).length
)

const historyEmptyMode = computed(() => {
  if (loading.value || error.value) return null
  if (history.value.length === 0 && selectedFocusFilter.value === 'all') return 'no_history'
  if (history.value.length > 0 && validHistoryItemCount.value === 0) return 'no_valid_history'
  if (history.value.length > 0 && validHistoryItemCount.value > 0) return 'has_valid_history'
  return null
})

watch(
  historyEmptyMode,
  (m) => {
    if (m) console.log('[History.empty] mode=', m)
  },
  { flush: 'post' }
)

function goFirstTrainingFromHistory() {
  router.push('/training')
}

const displayHistory = computed(() => {
  const raw = history.value || []
  const f = selectedFocusFilter.value
  let base = f === 'all' ? raw : raw.filter((it) => String(it?.training_focus ?? 'none').trim().toLowerCase() === f)
  if (validRecordFilter.value === 'valid') {
    base = base.filter((it) => it?.training_valid !== false)
  }
  return base
})

watch([selectedFocusFilter, history, validRecordFilter], () => {
  console.log(
    '[History.filter] selected_focus=',
    selectedFocusFilter.value,
    'filtered_count=',
    displayHistory.value.length
  )
})

watch(
  [validRecordFilter, displayHistory],
  () => {
    console.log(
      '[History.invalid] filter_valid_only=',
      validRecordFilter.value === 'valid',
      'visible_count=',
      displayHistory.value.length
    )
  },
  { flush: 'post' }
)

const showFocusReviewPanel = computed(
  () => REVIEWABLE_FOCUS.has(selectedFocusFilter.value) && !!(focusReview.value && focusReview.value.summary)
)

const showFocusReviewPlaceholder = computed(
  () =>
    (selectedFocusFilter.value === 'all' || selectedFocusFilter.value === 'none') &&
    history.value.length > 0
)

const focusReviewCardTitle = computed(() => {
  const k = selectedFocusFilter.value
  return TRAINING_FOCUS_LABEL[k] || SECTION.focusReview
})

const focusReviewBulletLines = computed(() => {
  const fr = focusReview.value
  if (!fr) return []
  const lines = []
  if (Array.isArray(fr.scores) && fr.scores.length) {
    const chain = fr.scores
      .map((x) => {
        const n = Number(x)
        return Number.isFinite(n) ? n.toFixed(1) : '—'
      })
      .join(' → ')
    lines.push(`最近该专项核心分（时间由旧到新）：${chain}`)
  }
  if (fr.trend) {
    lines.push(`当前整体趋势：${fr.trend}`)
  }
  if (fr.summary) {
    const dm = fr.summary.match(/关键指标变化摘要：[^。]+。/)
    if (dm) lines.push(dm[0].trim())
    const pm = fr.summary.match(/近期主要问题[^。]+。/)
    if (pm) lines.push(pm[0].trim())
  }
  const uniq = []
  const seen = new Set()
  for (const s of lines) {
    const t = String(s || '').trim()
    if (!t || seen.has(t)) continue
    seen.add(t)
    uniq.push(t)
  }
  return uniq.slice(0, 4)
})

watch([selectedFocusFilter, focusReview], () => {
  console.log(
    '[History.review] selected_focus=',
    selectedFocusFilter.value,
    ' summary=',
    focusReview.value?.summary || '(n/a)'
  )
})

/** 时间正序（旧 → 新），用于曲线与规则总结（随筛选变化） */
const chronological = computed(() => [...displayHistory.value].reverse())

const chartLabels = computed(() =>
  chronological.value.map((item) => formatChartTime(item.timestamp || item.created_at))
)

const seriesTotal = computed(() => chronological.value.map((h) => numOrNull(h.total_score)))
const seriesLanguage = computed(() => chronological.value.map((h) => numOrNull(h.language_score)))
const seriesPosture = computed(() => chronological.value.map((h) => numOrNull(h.posture_score)))

function numOrNull(v) {
  if (v === null || v === undefined || v === '') return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

function formatScore(v) {
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  return Number.isFinite(n) ? n.toFixed(1) : '—'
}

function formatChartTime(timestamp) {
  try {
    const d = new Date(timestamp)
    if (Number.isNaN(d.getTime())) return String(timestamp || '')
    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  } catch {
    return String(timestamp || '')
  }
}

const statsSummary = computed(() => {
  const h = displayHistory.value
  const n = h.length
  if (n === 0) {
    return {
      totalSessions: 0,
      lastFiveAvgTotal: '—',
      bestTotal: '—',
      lastVsPrevText: '—',
      trendClass: '',
    }
  }
  const firstFive = h.slice(0, 5)
  const sum = firstFive.reduce((s, x) => s + (Number(x.total_score) || 0), 0)
  const lastFiveAvg = sum / firstFive.length
  const best = Math.max(...h.map((x) => Number(x.total_score) || 0))

  let lastVsPrevText = '—'
  let trendClass = ''
  if (n >= 2) {
    const last = Number(h[0].total_score) || 0
    const prev = Number(h[1].total_score) || 0
    const d = last - prev
    const ad = Math.abs(d)
    if (d > 0.05) {
      lastVsPrevText = `上升 +${ad.toFixed(1)}`
      trendClass = 'up'
    } else if (d < -0.05) {
      lastVsPrevText = `下降 −${ad.toFixed(1)}`
      trendClass = 'down'
    } else {
      lastVsPrevText = '持平（±0.1 内）'
      trendClass = 'flat'
    }
  }

  return {
    totalSessions: n,
    lastFiveAvgTotal: lastFiveAvg.toFixed(1),
    bestTotal: best.toFixed(1),
    lastVsPrevText,
    trendClass,
  }
})

const historyStageSummary = computed(() => {
  void historyGoalsRevision.value
  const progress = computeTrainingGoalProgress({
    goals: readTrainingGoals(),
    historyList: historyForGoals.value,
    overview: validTrainingOverview.value,
  })
  const statusPack = computeGoalStatusPack(progress)
  const ss = statsSummary.value
  return buildStageSummary({
    progress,
    statusPack,
    overview: validTrainingOverview.value,
    trendHint: {
      lastVsPrevText: ss.lastVsPrevText,
      trendClass: ss.trendClass,
      bestTotalStr: ss.bestTotal,
    },
  })
})

const historyStageSummaryVisible = computed(() => {
  if (!hasActiveTrainingGoals(readTrainingGoals())) return false
  return (historyForGoals.value || []).some((it) => it?.training_valid !== false)
})

const historyStageMainLines = computed(() => historyStageSummary.value.mainProgress.slice(0, 3))
const historyStageNeedLines = computed(() => historyStageSummary.value.stillNeed.slice(0, 3))

const historyRhythmStats = computed(() => {
  void historyGoalsRevision.value
  const progress = computeTrainingGoalProgress({
    goals: readTrainingGoals(),
    historyList: historyForGoals.value,
    overview: validTrainingOverview.value,
  })
  const pack = computeGoalStatusPack(progress)
  let countRemaining = null
  if (progress.validCountProgress) {
    const r = progress.validCountProgress.target - progress.validCountProgress.current
    countRemaining = r > 0 ? r : null
  }
  return computeTrainingRhythm(historyForGoals.value, {
    goalStatus: pack.status,
    targetFocus: progress.goals?.target_focus || null,
    countRemaining,
  })
})

const historyRhythmSummaryLines = computed(() => buildHistoryRhythmSummaryLines(historyRhythmStats.value))

const historyGoalProgressForPlan = computed(() => {
  void historyGoalsRevision.value
  return computeTrainingGoalProgress({
    goals: readTrainingGoals(),
    historyList: historyForGoals.value,
    overview: validTrainingOverview.value,
  })
})

const historyGoalStatusPackForPlan = computed(() => computeGoalStatusPack(historyGoalProgressForPlan.value))

const historyNextPlan = computed(() => {
  void historyGoalsRevision.value
  return computeNextTrainingPlan({
    historyList: historyForGoals.value,
    overview: validTrainingOverview.value,
    goals: readTrainingGoals(),
    goalProgress: historyGoalProgressForPlan.value,
    goalStatusPack: historyGoalStatusPackForPlan.value,
    rhythmStats: historyRhythmStats.value,
    weeklyReview: historyWeeklyReview.value,
  })
})

const historyNextPlanVisible = computed(() => {
  if (loading.value || error.value) return false
  return !!historyNextPlan.value?.next_plan_action
})

const historyNextPlanFocusLine = computed(() => {
  const f = historyNextPlan.value?.next_plan_focus
  if (!f) return ''
  const lab = TRAINING_GOAL_FOCUS_LABEL[f] || f
  return `「${lab}」`
})

const historyNextPlanReasonLine = computed(() => {
  const r = historyNextPlan.value?.next_plan_reason
  if (!r) return ''
  const map = {
    valid_or_weekly_window_sparse: '有效训练次数或周报窗口内样本偏少。',
    goal_achieved: '当前保存的目标维度上已达标。',
    near_complete_with_momentum: '目标已很近且最近练习节奏、走势支持加码。',
    target_focus_improved_other_weak: '目标专项近期更稳，另有分项仍明显偏低。',
    overview_recommend_differs: '近期总览建议的专项与当前目标专项不一致。',
    no_goal_follow_overview: '尚未设定目标时，先跟随总览建议最省心。',
    steady_push: '离目标仍有空间，适合按原目标继续推进。',
    push_with_volatile_trend: '近期总分略有波动，先稳住再考虑调整目标。',
  }
  return map[r] || '按规则汇总近期表现与目标状态。'
})

watch(
  historyNextPlan,
  (p) => {
    if (loading.value || error.value) return
    if (!p?.next_plan_action) return
    console.log('[History.next_plan] action=', p.next_plan_action)
    console.log('[History.next_plan] focus=', p.next_plan_focus || '(none)')
  },
  { flush: 'post' }
)

const narrativeLines = computed(() => {
  const ch = chronological.value
  if (ch.length < 2) {
    return ['完成至少两次训练后，这里会基于历史记录生成趋势总结。']
  }
  const lastN = ch.length <= 5 ? ch : ch.slice(-5)
  const nLabel = lastN.length
  const totals = lastN.map((x) => Number(x.total_score) || 0)
  const langs = lastN.map((x) => numOrNull(x.language_score)).filter((v) => v != null)
  const posts = lastN.map((x) => numOrNull(x.posture_score)).filter((v) => v != null)

  const lines = []
  const scopePhrase = nLabel >= 5 ? '最近 5 次训练' : `最近 ${nLabel} 次训练`

  if (totals.length >= 2) {
    const delta = totals[totals.length - 1] - totals[0]
    const step = delta / (totals.length - 1)
    if (step > 0.5) {
      lines.push(`${scopePhrase}总分整体呈上升趋势。`)
    } else if (step < -0.5) {
      lines.push(`${scopePhrase}总分整体呈下降趋势，可适当回顾反馈重点。`)
    } else {
      lines.push(`${scopePhrase}总分相对平稳，仍有细化提升空间。`)
    }
  }

  if (posts.length >= 3) {
    const first = posts[0]
    const last = posts[posts.length - 1]
    if (last - first >= 3) {
      lines.push('仪态表现改善较明显，建议保持镜头前的稳定发挥。')
    } else if (first - last >= 3) {
      lines.push('仪态得分近期有所回落，可关注视线与姿态稳定性。')
    }
  }

  if (langs.length >= 3) {
    const mean = langs.reduce((a, b) => a + b, 0) / langs.length
    const varSum = langs.reduce((s, v) => s + (v - mean) ** 2, 0)
    const std = Math.sqrt(varSum / langs.length)
    if (std >= 8) {
      lines.push('语言模块波动较大，建议继续稳定语速与停顿。')
    } else {
      lines.push('语言得分波动相对可控，可针对弱项做专项练习。')
    }
  }

  if (!lines.length) {
    lines.push('继续积累训练次数，趋势特征会更清晰。')
  }

  return lines
})

const trendMessage = computed(() => {
  if (displayHistory.value.length < 2) return ''

  const latest = displayHistory.value[0]
  const previous = displayHistory.value[1]
  const diff = (Number(latest.total_score) || 0) - (Number(previous.total_score) || 0)

  if (diff > 0) {
    return `你比上一次进步了 ${diff.toFixed(1)} 分`
  }
  if (diff < 0) {
    return `你比上一次下降了 ${Math.abs(diff).toFixed(1)} 分`
  }
  return '你和上一次表现持平'
})

const trendType = computed(() => {
  if (displayHistory.value.length < 2) return ''

  const latest = displayHistory.value[0]
  const previous = displayHistory.value[1]
  const diff = (Number(latest.total_score) || 0) - (Number(previous.total_score) || 0)

  if (diff > 0) return 'positive'
  if (diff < 0) return 'negative'
  return 'neutral'
})

const bestScoreMessage = computed(() => {
  if (displayHistory.value.length === 0) return ''

  const best = displayHistory.value.reduce((max, item) =>
    (Number(item.total_score) || 0) > (Number(max.total_score) || 0) ? item : max
  )

  return `当前最佳成绩：${formatScore(best.total_score)} 分（${best.session_name}）`
})

/** 首屏趋势一句：有两次以上优先用较上次；否则用叙事首句 */
const historyTrendConclusionLine = computed(() => {
  if (displayHistory.value.length === 0) return ''
  if (displayHistory.value.length >= 2 && trendMessage.value) return trendMessage.value
  if (narrativeLines.value.length) return narrativeLines.value[0]
  return bestScoreMessage.value
})

function formatDate(timestamp) {
  try {
    const date = new Date(timestamp)
    return date.toLocaleString()
  } catch {
    return timestamp
  }
}

function modalityLabel(v) {
  if (v === true) return '已采集'
  if (v === false) return '未通过检测'
  return '未记录'
}

function modalityClass(v) {
  if (v === true) return 'ok'
  if (v === false) return 'bad'
  return 'unk'
}

const HISTORY_FOCUS_ORDER = { language: 0, posture: 1, content: 2, qa: 3 }

const HISTORY_FOCUS_SHORT_LABEL = {
  language: '语言',
  posture: '仪态',
  content: '内容',
  qa: '问答',
}

function historyItemTrainingFocusShort(item) {
  const k = String(item?.training_focus ?? 'none').trim().toLowerCase()
  return trainingFocusLabel(k)
}

function historyItemFocusTagClass(item) {
  const k = String(item?.training_focus ?? 'none').trim().toLowerCase()
  const map = {
    language: 'ui-tag--focus-lang',
    posture: 'ui-tag--focus-posture',
    qa: 'ui-tag--focus-qa',
    content: 'ui-tag--focus-content',
  }
  return map[k] || 'ui-tag--focus-none'
}

const HISTORY_FOCUS_TREND_SHORT = {
  up: '同专项回看：上升',
  flat: '同专项回看：持平',
  volatile: '同专项回看：波动',
  insufficient: '同专项回看：暂无足够历史',
}

function historyItemFocusTrendShort(item) {
  const fk = String(item?.training_focus ?? 'none').trim().toLowerCase()
  if (fk === 'none') return ''
  const k = String(item?.focus_trend_kind ?? '').trim().toLowerCase()
  if (k in HISTORY_FOCUS_TREND_SHORT) return HISTORY_FOCUS_TREND_SHORT[k]
  return ''
}

const FOCUS_TREND_KIND_CN = {
  up: '上升',
  flat: '持平',
  volatile: '波动',
  insufficient: '暂无足够历史',
}

function historyItemFocusMetaVisible(item) {
  const k = String(item?.training_focus ?? 'none').trim().toLowerCase()
  return k !== 'none'
}

function historyItemFocusCardLabel(item) {
  const k = String(item?.training_focus ?? 'none').trim().toLowerCase()
  return trainingFocusLabel(k)
}

function historyItemFocusPrimaryDisplay(item) {
  const raw = item?.focus_primary_score ?? item?.training_focus_primary_score
  if (raw == null || raw === '') return '—'
  const n = Number(raw)
  return Number.isFinite(n) ? `${n.toFixed(1)} 分` : '—'
}

function historyItemFocusVsPrevDisplay(item) {
  const v = item?.focus_vs_previous
  if (v != null && String(v).trim()) return String(v).trim()
  return '—'
}

function historyItemFocusTrendLabel(item) {
  const k = String(item?.focus_trend_kind ?? '').trim().toLowerCase()
  return FOCUS_TREND_KIND_CN[k] || '—'
}

function historyItemKeyMetricsVsPrev(item) {
  const v = item?.focus_key_metrics_vs_previous
  if (v == null || !String(v).trim()) return ''
  return String(v).trim()
}

function historyInvalidReasonLine(item) {
  const s = String(item?.invalid_reason_summary || '').trim()
  if (s) return `原因：${s}。本轮分数仍可供你对照；同专项趋势会优先使用已纳入统计的记录。`
  return '本轮未纳入统计条件；同专项趋势会优先使用已纳入统计的记录。可完成一轮完整练习后再看对比。'
}

function historyContinueTrainingLabel(item) {
  if (item?.training_valid === false) {
    const fk = String(item?.training_focus ?? 'none').trim().toLowerCase()
    if (fk !== 'none' && HISTORY_FOCUS_SHORT_LABEL[fk]) {
      return `设备就绪后再试：${HISTORY_FOCUS_SHORT_LABEL[fk]}`
    }
    return '设备就绪后再试一次'
  }
  const k = inferFocusFromHistoryItem(item)
  const name = HISTORY_FOCUS_SHORT_LABEL[k] || '综合'
  return `继续练：${name}专项`
}

function inferFocusFromHistoryItem(item) {
  const pairs = [
    ['language', numOrNull(item.language_score)],
    ['posture', numOrNull(item.posture_score)],
    ['content', numOrNull(item.content_score)],
    ['qa', numOrNull(item.qa_score)],
  ].filter(([, v]) => v != null && Number.isFinite(v))
  if (!pairs.length) return 'language'
  pairs.sort(
    (a, b) => a[1] - b[1] || HISTORY_FOCUS_ORDER[a[0]] - HISTORY_FOCUS_ORDER[b[0]]
  )
  return pairs[0][0]
}

const HISTORY_FOCUS_FILTER_LABELS = {
  all: '全部',
  none: TRAINING_FOCUS_LABEL.none,
  language: TRAINING_FOCUS_LABEL.language,
  posture: TRAINING_FOCUS_LABEL.posture,
  qa: TRAINING_FOCUS_LABEL.qa,
  content: TRAINING_FOCUS_LABEL.content,
}

const continueTrainingFromHistory = (item) => {
  if (!item?.session_id) return
  const focus = inferFocusFromHistoryItem(item)
  const profile = String(item.scoring_profile || 'defense').trim() || 'defense'
  const dm = 'with_ppt'
  const payload = {
    recommended_focus: focus,
    scoring_profile: profile,
    defense_material_mode: dm,
    source: 'result_page',
    from_session_id: item.session_id,
    ts: Date.now(),
  }
  try {
    writeUserScopedItem(sessionStorage, TRAINING_FOCUS_HANDOFF_KEY, JSON.stringify(payload))
  } catch (_) {}
  try {
    removeUserScopedItem(localStorage, TRAINING_RUNTIME_SNAPSHOT_KEY, undefined, true)
  } catch (_) {}
  if (item.training_valid === false) {
    pageFeedback(
      'History',
      'continue_weak_focus',
      '该条未纳入统计，仍会按推断薄弱专项预填训练页，分数仅供对照；建议在环境与流程正常后再练一轮，以便形成可纳入趋势的记录。',
      'warning'
    )
  } else {
    pageFeedback('History', 'continue_weak_focus', '已按该条预填训练页，请在本页内再点开始（不会自动开始训练）。', 'success')
  }
  router.push({
    path: '/training',
    query: {
      entry: 'history',
      recommended_focus: focus,
      scoring_profile: profile,
      defense_material_mode: dm,
    },
  })
}

const viewDetail = (sid) => {
  if (!sid) {
    pageFeedback('History', 'view_detail', '找不到这条记录的编号，请返回列表重试。', 'warning')
    return
  }
  pageFeedback('History', 'view_detail', '正在打开该条训练的详情页。', 'success')
  router.push({
    path: '/result',
    query: { session_id: sid },
  })
}

async function confirmDeleteHistoryItem(item) {
  const sid = String(item?.session_id || '').trim()
  if (!sid) return
  console.log('[History.manage] action=delete_one session_id=', sid)
  const name = String(item?.session_name || '该条训练').trim() || '该条训练'
  const ok = await trainingConfirmDanger({
    title: '从「历史」中删除这条记录？',
    message: `将永久删除「${name}」在本列表中的行与对应复盘引用。若其它页仍打开该次结果，刷新后将无法加载。此操作不可恢复。`,
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  if (!ok) {
    console.log('[History.manage] result=cancel action=delete_one')
    return
  }
  try {
    await deleteJson(`/history/${encodeURIComponent(sid)}`)
    console.log('[History.manage] result=success action=delete_one')
    pageFeedback('History', 'delete_one', '历史：该条记录已从本页列表移除。', 'success')
    notifyHistoryDataChanged()
    await loadHistory()
  } catch (e) {
    console.log('[History.manage] result=error action=delete_one', e)
    pageFeedback(
      'History',
      'delete_one',
      toUserFacingMessage(e, '删除失败，请稍后重试。'),
      'warning'
    )
  }
}

async function confirmClearInvalidTraining() {
  const n = invalidHistoryCount.value
  if (n <= 0) return
  console.log('[History.manage] action=clear_invalid pending_count=', n)
  const ok = await trainingConfirmDanger({
    title: '清理未纳入统计的记录？',
    message: `将删除当前共 ${n} 条未纳入统计的记录（常见原因：未完成流程、环境或信号问题）。已纳入统计的记录不受影响。此操作不可恢复。`,
    confirmButtonText: '确定清理',
    cancelButtonText: '取消',
  })
  if (!ok) {
    console.log('[History.manage] result=cancel action=clear_invalid')
    return
  }
  try {
    const res = await postJson('/history/clear-invalid', {})
    const c = Number(res?.deleted_count ?? 0)
    console.log('[History.manage] result=success action=clear_invalid deleted_count=', c)
    pageFeedback('History', 'clear_invalid', `历史：已清理 ${c} 条未纳入统计的记录。`, 'success')
    notifyHistoryDataChanged()
    await loadHistory()
  } catch (e) {
    console.log('[History.manage] result=error action=clear_invalid', e)
    pageFeedback(
      'History',
      'clear_invalid',
      toUserFacingMessage(e, '清理失败，请稍后重试。'),
      'warning'
    )
  }
}

function historyApiPath() {
  const f = selectedFocusFilter.value
  if (REVIEWABLE_FOCUS.has(f)) {
    return `/history?review_focus=${encodeURIComponent(f)}`
  }
  return '/history'
}

const loadHistory = async () => {
  loading.value = true
  error.value = ''
  validTrainingOverview.value = null

  try {
    const data = await getJson(historyApiPath())
    history.value = data.history || []
    validTrainingOverview.value = data.valid_training_overview ?? null
    let listForGoals = history.value
    if (REVIEWABLE_FOCUS.has(selectedFocusFilter.value)) {
      try {
        const full = await getJson('/history')
        listForGoals = full.history || []
      } catch (_) {
        listForGoals = history.value
      }
    }
    historyForGoals.value = listForGoals
    console.log('[History.overview] valid_training_overview=', validTrainingOverview.value)
    if (REVIEWABLE_FOCUS.has(selectedFocusFilter.value)) {
      focusReview.value = {
        summary: data.focus_review_summary || '',
        scores: Array.isArray(data.focus_review_scores) ? data.focus_review_scores : [],
        trend: data.focus_review_trend || '',
        nextAction: data.focus_review_next_action || '',
      }
    } else {
      focusReview.value = null
    }
    for (const it of history.value) {
      console.log(
        '[History.focus] item training_focus=',
        it?.training_focus,
        'session_id=',
        it?.session_id
      )
      console.log('[History.focus] display_label=', historyItemTrainingFocusShort(it))
    }
  } catch (e) {
    error.value = e && e.message ? String(e.message) : 'load_failed'
    validTrainingOverview.value = null
    historyForGoals.value = []
  } finally {
    loading.value = false
  }
}

function retryLoadHistory() {
  console.log('[History.load] retry=', true)
  loadHistory()
}

onMounted(async () => {
  try {
    window.addEventListener(TRAINING_GOALS_CHANGED_EVENT, bumpHistoryGoalsRevision)
  } catch (_) {}
  try {
    await hydrateAccountSettings()
  } catch (_) {}
  const st = readStoredHistoryFilters()
  selectedFocusFilter.value = st.focus
  validRecordFilter.value = st.valid
  console.log('[History.user_scope] user_id=', getActiveUserId() ?? '(none)')
  console.log('[History.user_scope] restored_filter_state=', {
    focus: st.focus,
    valid: st.valid,
    from: st.from,
  })
  const pv = readAppPreferences().history_valid_only_default
  console.log('[History.preferences] applied_valid_only=', pv)
  console.log('[History.settings] applied_global_preferences=', {
    history_valid_only_default: pv,
    snapshot: preferencesSnapshotForLog(),
  })
  await loadHistory()
})

onBeforeUnmount(() => {
  try {
    window.removeEventListener(TRAINING_GOALS_CHANGED_EVENT, bumpHistoryGoalsRevision)
  } catch (_) {}
})

function goHomeFromHistory() {
  router.push('/home')
}

function goTrainingFromHistory() {
  router.push('/training')
}

watch(loading, (v) => {
  console.log('[History.load] loading=', v)
})

watch(error, (m) => {
  if (m) console.log('[History.load] error=', toUserFacingMessage(m))
})

watch(
  selectedFocusFilter,
  (nv, ov) => {
    if (ov !== undefined) {
      pageFeedback(
        'History',
        'focus_filter',
        `历史页：已按「${HISTORY_FOCUS_FILTER_LABELS[nv] || nv}」重新加载。`,
        'info'
      )
    }
    loadHistory()
  },
  { immediate: false }
)

watch(validRecordFilter, (nv, ov) => {
  if (ov === undefined) return
  if (nv === 'valid') {
    pageFeedback('History', 'valid_record_filter', '历史页：列表仅显示已纳入统计的记录。', 'info')
  } else {
    pageFeedback('History', 'valid_record_filter', '历史页：列表已包含全部记录（含未纳入统计）。', 'info')
  }
})

/** 简单折线图：缺失值为断点，多段折线；无复杂交互。 */
const LineSpark = defineComponent({
  name: 'LineSpark',
  props: {
    labels: { type: Array, default: () => [] },
    values: { type: Array, default: () => [] },
    color: { type: String, default: '#409eff' },
  },
  setup(props) {
    return () => {
      const vals = props.values || []
      const labels = props.labels || []
      const n = vals.length
      const w = 320
      const svgH = 140
      const pad = 18
      const innerW = w - pad * 2
      const innerH = svgH - pad * 2

      const finite = vals.filter((v) => v != null && Number.isFinite(v))
      if (finite.length === 0) {
        return h('div', { class: 'spark-empty' }, '暂无数据点')
      }
      let minV = Math.min(...finite)
      let maxV = Math.max(...finite)
      if (minV === maxV) {
        minV -= 1
        maxV += 1
      }
      const span = maxV - minV || 1

      const segments = []
      let cur = []
      for (let i = 0; i < n; i++) {
        const v = vals[i]
        if (v == null || !Number.isFinite(v)) {
          if (cur.length) {
            segments.push(cur)
            cur = []
          }
          continue
        }
        const t = n <= 1 ? 0.5 : i / (n - 1)
        const x = pad + t * innerW
        const y = pad + (1 - (v - minV) / span) * innerH
        cur.push({ x, y, i, v })
      }
      if (cur.length) segments.push(cur)

      const paths = segments.map((seg) => {
        const d = seg.map((p, j) => `${j === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
        return h('path', {
          d,
          fill: 'none',
          stroke: props.color,
          'stroke-width': 2,
          'stroke-linejoin': 'round',
          'stroke-linecap': 'round',
        })
      })

      const dots = segments.flatMap((seg) =>
        seg.map((p) =>
          h('circle', {
            cx: p.x,
            cy: p.y,
            r: 3.5,
            fill: props.color,
          })
        )
      )

      const labelNodes =
        n > 0
          ? vals.map((v, i) => {
              if (v == null || !Number.isFinite(v)) return null
              const t = n <= 1 ? 0.5 : i / (n - 1)
              const lx = pad + t * innerW
              const text = labels[i] || ''
              return h(
                'text',
                {
                  x: lx,
                  y: svgH - 4,
                  class: 'spark-label',
                  'text-anchor': 'middle',
                },
                text
              )
            })
          : []

      return h('div', { class: 'spark-wrap' }, [
        h(
          'svg',
          {
            class: 'spark-svg',
            viewBox: `0 0 ${w} ${svgH}`,
            preserveAspectRatio: 'none',
          },
          [...paths, ...dots, ...labelNodes.filter(Boolean)]
        ),
      ])
    }
  },
})
</script>

<style scoped>
.history-page {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  padding: 0;
  min-height: 100vh;
  box-sizing: border-box;
}

.history-page-head--admin {
  margin-bottom: 2px;
}

.history-page--admin-v2 .ui-page-title {
  margin-bottom: 4px;
}

/* 双栏列定义与 gap 见 ui-hierarchy .history-page--admin-v2 .history-admin-console */
.history-admin-console--grid {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.history-summary-bar {
  padding: 12px 16px 14px;
  text-align: left;
  border-radius: var(--ui-radius-lg);
  border: 1px solid var(--ui-card-border, var(--ui-border));
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;
  overflow: hidden;
}

.history-summary-bar__metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 10px;
  align-items: stretch;
}

.history-summary-metric {
  display: inline-flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  padding: 6px 10px;
  border-radius: var(--ui-radius-sm);
  background: var(--ui-surface-subtle);
  border: 1px solid var(--ui-border);
}

.history-summary-metric--soft {
  background: transparent;
  border-style: dashed;
}

.history-summary-metric__k {
  font-size: var(--font-xs, 14px);
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--ui-text-muted);
}

.history-summary-metric__v {
  font-size: var(--font-md, 17px);
  font-weight: 700;
  color: var(--ui-text-primary);
  line-height: 1.25;
}

.history-summary-metric__v--trend.up {
  color: #059669;
}

.history-summary-metric__v--trend.down {
  color: #dc2626;
}

.history-summary-metric__v--trend.flat {
  color: var(--ui-accent);
}

.history-summary-bar__filters {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--ui-border);
  font-size: var(--font-sm, 15px);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 8px;
}

.history-summary-bar__strong {
  color: var(--ui-text-primary);
  font-weight: 700;
}

.history-summary-bar__dot {
  opacity: 0.45;
}

.history-filter-toolbar {
  padding: var(--ui-card-pad-y, 22px) var(--ui-card-pad-x, 24px);
  text-align: left;
  border-radius: var(--ui-radius-lg);
  min-width: 0;
  max-width: 100%;
  width: 100%;
  box-sizing: border-box;
  overflow: hidden;
  border: 1px solid var(--ui-card-border, var(--ui-border));
}

.history-filter-toolbar__head {
  margin-bottom: 12px;
}

.history-filter-toolbar__title {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 800;
  color: var(--ui-text-primary);
  letter-spacing: -0.02em;
  line-height: 1.25;
}

.history-filter-toolbar__hint {
  margin: 0;
  font-size: var(--font-sm, 15px);
  line-height: 1.55;
}

.history-filter-toolbar__body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-filter-toolbar__chunk {
  min-width: 0;
}

.history-filter-toolbar__h {
  margin: 0 0 8px;
  font-size: var(--font-sm, 15px);
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: none;
  color: var(--ui-text-secondary);
}

.history-filter-toolbar .focus-filter-bar,
.history-filter-toolbar .valid-filter-bar {
  margin-bottom: 0;
  padding: 14px 16px;
  max-width: 100%;
  box-sizing: border-box;
  box-shadow: none;
  background: var(--ui-surface-subtle);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
}

.history-filter-toolbar .focus-filter-group--history,
.history-filter-toolbar .focus-filter-group--history-valid {
  max-width: 100%;
  flex-wrap: wrap;
}

.history-filter-toolbar .valid-filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 12px;
  min-width: 0;
  width: 100%;
  max-width: 100%;
}

.history-filter-toolbar .history-training-resume-hint {
  margin: 10px 0 0;
  padding-top: 10px;
  border-top: 1px dashed var(--ui-border);
  font-size: var(--font-sm, 15px);
  line-height: 1.55;
}

.focus-filter-group--history :deep(.el-radio-button__inner),
.focus-filter-group--history-valid :deep(.el-radio-button__inner) {
  min-height: 36px;
  padding: 0 18px;
  font-size: 15px;
  line-height: 34px;
}

.history-clear-invalid-btn {
  flex-shrink: 0;
  min-height: 40px;
  padding-left: 20px;
  padding-right: 20px;
  font-size: 15px;
}

.history-trend-compact {
  padding: var(--ui-card-pad-y, 22px) var(--ui-card-pad-x, 24px);
  border-radius: var(--ui-radius-lg);
  text-align: left;
  min-height: 0;
  box-sizing: border-box;
  align-self: start;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--ui-card-border, var(--ui-border));
}

.history-trend-compact__eyebrow {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: none;
  color: var(--ui-text-secondary);
}

.history-trend-compact__line {
  margin: 0 0 10px;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.45;
  color: var(--ui-text-primary);
}

.history-trend-compact__bullets {
  margin: 0 0 10px;
  padding-left: 1.15rem;
  font-size: var(--font-sm, 15px);
  line-height: 1.55;
}

.history-trend-compact__bullets li {
  margin-bottom: 2px;
}

.history-trend-compact__foot {
  margin: 0;
  font-size: var(--font-sm, 15px);
  line-height: 1.5;
}

.history-trend-compact--empty .history-trend-compact__line {
  font-weight: 500;
}

.history-list-panel {
  margin-top: 2px;
  padding: var(--ui-card-pad-y, 22px) var(--ui-card-pad-x, 24px);
  border-radius: var(--ui-radius-lg);
  border: 1px solid var(--ui-card-border, var(--ui-border));
  background: var(--ui-surface);
  box-shadow: var(--ui-shadow-card);
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
  overflow: hidden;
}

.history-list-panel__head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px 12px;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--ui-border);
}

.history-list-panel__meta {
  margin: 0;
  font-size: 0.78rem;
}

.history-page-sink-hints {
  margin-top: 20px;
  width: 100%;
}

.history-demo-hint--sink {
  max-width: 100%;
  margin: 0;
}

.history-report-nav-hint--compact {
  margin: 0 0 10px;
}

.history-report-nav-hint__one {
  margin: 0;
  font-size: 0.82rem;
  line-height: 1.45;
}

.history-trend-sink__h2 {
  margin: 0 0 6px;
  font-size: 1rem;
  font-weight: 700;
}

.trend-summary-list--compact {
  font-size: 0.86rem;
  line-height: 1.5;
}

.trend-summary-list--compact li {
  margin-bottom: 4px;
}

.history-collapse--sink {
  margin-bottom: 12px;
}

.history-collapse--sink :deep(.el-collapse-item__header) {
  font-size: 0.88rem;
  color: var(--ui-text-secondary);
}

.history-loading-panel {
  width: 100%;
  margin: 16px 0 24px;
  text-align: left;
}

.history-loading-panel__label {
  margin: 0 0 6px;
  font-size: 0.95rem;
}

.history-loading-panel__hint {
  margin: 0 0 12px;
  font-size: 0.86rem;
  line-height: 1.45;
}

.history-error-panel {
  width: 100%;
  margin: 16px 0 24px;
  text-align: left;
}

.history-error-panel__body {
  margin: 0 0 12px;
  font-size: 0.9rem;
  line-height: 1.55;
}

.history-error-panel__actions {
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

.history-page-error-actions {
  align-items: center;
}

.history-item-actions {
  align-items: center;
}

.history-dropdown-danger-label {
  color: var(--el-color-danger);
  font-weight: 500;
}

.history-main {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.history-recent-block {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.history-collapse-block {
  margin-bottom: 16px;
}

.history-collapse-block :deep(.el-collapse-item__header) {
  font-weight: 600;
  padding: 12px 16px;
  line-height: 1.4;
}

.history-collapse--more :deep(.el-collapse-item__content) {
  padding-top: 4px;
}

.history-page-head {
  width: 100%;
  text-align: left;
  margin-bottom: 4px;
}

.history-page-ribbon {
  margin: 0 0 6px;
  font-size: 0.8rem;
}

.history-page-ribbon__k {
  font-weight: 600;
  color: #334155;
  margin-right: 8px;
}

.history-inpage-nav {
  margin-bottom: 8px;
}

.history-collapse--overview :deep(.el-collapse-item__header) {
  min-height: 40px;
  line-height: 1.3;
  padding-top: 6px;
  padding-bottom: 6px;
  font-size: 0.88rem;
}

.history-report-nav-hint {
  margin: 0 0 12px;
}

.history-overview-surface {
  padding: 18px 20px;
  margin-bottom: 0;
  text-align: left;
}

.history-tier-eyebrow {
  margin: 0 0 8px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
}

.history-tier-eyebrow--in-section {
  margin-bottom: 6px;
}

.history-tier-eyebrow--in-card {
  margin-bottom: 6px;
}

.history-page--brand-v1 .history-tier-eyebrow {
  color: var(--ui-text-muted);
}

.history-focus-review-card {
  padding: 18px 20px !important;
  margin-bottom: 20px;
  transition: box-shadow var(--ui-transition);
}

.history-focus-review-card:hover {
  box-shadow: var(--ui-shadow-card-hover);
}

.history-focus-review-card h2,
.history-focus-review-card .focus-review-h2 {
  margin: 0 0 6px;
  font-size: 1.08rem;
  font-weight: 700;
  color: var(--ui-text-primary);
  letter-spacing: -0.02em;
}

.history-trend-card {
  padding: 16px 18px !important;
  margin-bottom: 16px;
}

.history-stats-card .stat-card {
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  box-shadow: var(--ui-shadow-card);
  transition: box-shadow var(--ui-transition), border-color var(--ui-transition);
}

.history-stats-card .stat-card:hover {
  box-shadow: var(--ui-shadow-card-hover);
}

.history-focus-placeholder {
  margin-bottom: 16px;
}

.history-filter-tier {
  padding: 14px 16px 16px;
  text-align: left;
}

.history-filter-tier .focus-filter-bar,
.history-filter-tier .valid-filter-bar {
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 0;
  margin-bottom: 14px;
}

.history-filter-tier .valid-filter-bar {
  margin-bottom: 0;
}

.history-filter-kicker {
  margin: 0 0 4px;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ui-text-muted, #64748b);
}

.history-filter-lead {
  margin: 0 0 14px;
  font-size: 0.88rem;
  line-height: 1.55;
  max-width: 52ch;
}

.history-filter-h3 {
  margin: 0 0 4px;
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--ui-text-primary, #0f172a);
  letter-spacing: -0.01em;
}

.history-filter-hint-line {
  margin: 0 0 10px;
  font-size: 0.82rem;
  line-height: 1.5;
  max-width: 58ch;
}

.history-list-eyebrow {
  margin: 0;
}

.history-item-top {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px 16px;
  margin-bottom: 4px;
}

.history-item-main {
  flex: 1 1 220px;
  min-width: 0;
}

.history-item-primary-cta {
  flex: 0 0 auto;
  align-self: center;
}

.history-item-title-row.item-header {
  margin-bottom: 8px;
}

.history-item-session-title {
  font-size: 0.98rem;
  line-height: 1.3;
  word-break: break-word;
}

.history-item-status-tag {
  flex-shrink: 0;
}

.history-item-primary--scan {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px 14px;
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
  align-items: end;
}

@media (min-width: 560px) and (max-width: 719px) {
  .history-item-primary--scan {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 720px) {
  .history-item-primary--scan {
    grid-template-columns: minmax(0, 1.1fr) auto minmax(0, 1.1fr);
  }
}

.history-item-subrow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 12px;
  margin-top: 2px;
  padding-top: 10px;
  border-top: 1px solid var(--ui-border);
}

.history-item-subrow__left {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px 8px;
  min-width: 0;
}

.history-item-subrow__manage {
  margin-left: auto;
}

.history-item-manage-btn {
  font-weight: 500;
}

.history-item-details {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}

.valid-status-block {
  margin-bottom: 10px;
}

.history-item-detail-preface {
  margin: 0 0 10px;
  font-size: 0.86rem;
  line-height: 1.5;
}

.hip-block.hip-block--inline {
  display: flex;
  flex-direction: row;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 10px;
}

.hip-block.hip-block--inline .hip-k {
  margin: 0;
}

.hip-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.hip-k {
  font-size: 0.72rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.hip-v {
  font-size: 0.95rem;
  color: #0f172a;
  line-height: 1.35;
  word-break: break-word;
}

.hip-v--score {
  font-size: 1.22rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.hip-block--valid .ui-tag {
  align-self: flex-start;
}

.timestamp--secondary {
  font-size: 0.8em;
}

.history-item--v1 {
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-lg);
  border-left: 3px solid var(--ui-accent-muted);
  box-shadow: var(--ui-shadow-card);
  transition: box-shadow var(--ui-transition);
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
  overflow: hidden;
}

.history-page--brand-v1 .history-item--v1:hover {
  box-shadow: var(--ui-shadow-card-hover);
}

.focus-filter-bar {
  width: 100%;
  margin-bottom: 20px;
  padding: 12px 14px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-card-border, #dfe7f2);
  border-radius: var(--ui-radius-md);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.focus-filter-label {
  display: block;
  font-size: var(--font-sm, 15px);
  color: var(--ui-text-secondary);
  margin-bottom: 8px;
}

.focus-filter-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.valid-filter-bar {
  width: 100%;
  margin-bottom: 20px;
  padding: 12px 14px;
  background: var(--ui-surface-subtle);
  border: 1px solid var(--ui-card-border, #dfe7f2);
  border-radius: var(--ui-radius-md);
}

.valid-filter-bar .focus-filter-label {
  margin-bottom: 6px;
}

.valid-filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
}

.history-manage-hint {
  margin: 10px 0 0;
  font-size: var(--font-sm, 15px);
  line-height: 1.55;
}

.history-training-resume-hint {
  width: 100%;
  margin: 0 0 16px;
  font-size: var(--font-sm, 15px);
  line-height: 1.55;
}

.valid-training-overview {
  width: 100%;
  margin-bottom: 20px;
  padding: 14px 16px;
  background: linear-gradient(180deg, var(--ui-accent-soft) 0%, var(--ui-surface) 64%);
  border: 1px solid var(--ui-accent-muted);
  border-radius: var(--ui-radius-lg);
  text-align: left;
}

.overview-title {
  margin: 0 0 10px;
  font-size: 1.06rem;
  font-weight: 700;
  color: var(--ui-text-primary);
  letter-spacing: -0.015em;
}

.overview-degraded {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.55;
}

.overview-body-list {
  margin: 0;
  padding-left: 1.15rem;
  font-size: 0.9rem;
  line-height: 1.65;
  color: var(--ui-text-secondary);
}

.overview-body-list li {
  margin-bottom: 6px;
}

.history-goal-summary {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed #c6e2ff;
}

.history-goal-summary__title {
  margin: 0 0 6px;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--ui-accent);
}

.history-goal-summary__list {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.86rem;
  line-height: 1.55;
}

.history-goal-summary__list li {
  margin-bottom: 4px;
}

.history-weekly-review {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed #a5b4fc;
}

.history-weekly-review__title {
  margin: 0 0 6px;
  font-size: 0.82rem;
  font-weight: 600;
  color: #4f46e5;
}

.history-weekly-review__list {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.86rem;
  line-height: 1.55;
}

.history-weekly-review__list li {
  margin-bottom: 4px;
}

.history-next-plan {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed #6ee7b7;
}

.history-next-plan__title {
  margin: 0 0 8px;
  font-size: 0.82rem;
  font-weight: 600;
  color: #047857;
}

.history-next-plan__action {
  margin: 0 0 6px;
  font-size: 0.86rem;
}

.history-next-plan__body {
  margin: 0 0 6px;
  font-size: 0.9rem;
  line-height: 1.55;
  color: #0f172a;
}

.history-next-plan__focus,
.history-next-plan__reason {
  margin: 0 0 4px;
  font-size: 0.84rem;
  line-height: 1.5;
}

.history-next-plan__k {
  font-weight: 600;
  color: #64748b;
}

.history-stage-summary {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed #a7f3d0;
}

.history-stage-summary .history-stage-summary__title {
  margin: 0 0 8px;
  font-size: 0.82rem;
  font-weight: 600;
  color: #059669;
}

.history-stage-k {
  margin: 8px 0 4px;
  font-size: 0.8rem;
}

.history-stage-list {
  margin: 0 0 6px;
  padding-left: 1.1rem;
  font-size: 0.86rem;
  line-height: 1.55;
}

.history-stage-list li {
  margin-bottom: 4px;
}

.history-rhythm-summary {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed #cbd5e1;
}

.history-rhythm-summary__title {
  margin: 0 0 6px;
  font-size: 0.82rem;
  font-weight: 600;
  color: #64748b;
}

.history-rhythm-summary__list {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.86rem;
  line-height: 1.55;
}

.history-rhythm-summary__list li {
  margin-bottom: 4px;
}

.empty--inline {
  margin: 16px 0 24px;
  text-align: center;
}

.history-empty-card {
  margin: 20px 0 28px;
  padding: 24px 20px;
  max-width: 720px;
  margin-left: auto;
  margin-right: auto;
  text-align: center;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}

.history-empty-title {
  margin: 0 0 10px;
  font-size: 1.15rem;
  font-weight: 600;
  color: #0f172a;
}

.history-empty-lead {
  margin: 0 0 16px;
  font-size: 0.92rem;
  line-height: 1.6;
  max-width: 420px;
  margin-left: auto;
  margin-right: auto;
}

.history-empty-foot {
  margin: 12px 0 0;
  font-size: 0.82rem;
}

.history-filter-empty {
  margin: 20px auto 24px;
  max-width: 720px;
  padding: 16px;
  text-align: center;
  font-size: 0.9rem;
  line-height: 1.55;
}

.history-filter-empty-cta {
  margin-top: 12px;
}

.history-filter-empty-foot {
  margin: 8px 0 0;
  font-size: 0.82rem;
}

.history-invalid-only-alert {
  max-width: 720px;
  margin: 0 auto 18px;
}

.history-invalid-only-alert__body {
  margin: 0 0 12px;
  font-size: 0.88rem;
  line-height: 1.55;
}

.history-invalid-only-cta {
  margin-top: 4px;
}

.focus-review-summary {
  width: 100%;
  margin-bottom: 20px;
  text-align: left;
}

.focus-review-summary h2 {
  margin: 0 0 8px;
  font-size: 1.05rem;
  color: #303133;
}

.focus-review-eyebrow {
  margin: 0 0 8px;
  font-size: 0.82rem;
  color: #909399;
  font-weight: 600;
}

.focus-review-body {
  margin: 0 0 10px;
  font-size: 0.92rem;
  line-height: 1.65;
  color: #606266;
}

.focus-review-subline {
  margin: 0 0 10px;
  font-size: 0.84rem;
  line-height: 1.5;
  max-width: 58ch;
}

.focus-review-body--text {
  color: var(--ui-text-primary, #303133);
  line-height: 1.7;
  max-width: 62ch;
}

.focus-review-bullets {
  margin: 0 0 10px;
  padding-left: 1.2rem;
  font-size: 0.88rem;
  line-height: 1.55;
  color: #606266;
}

.focus-review-bullets li {
  margin-bottom: 4px;
}

.focus-review-next {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.55;
  color: #303133;
}

.focus-review-placeholder {
  width: 100%;
  margin-bottom: 16px;
  font-size: 0.88rem;
  line-height: 1.55;
  padding: 12px 14px;
  border-radius: 8px;
}

.focus-review-placeholder__title {
  margin: 0 0 6px;
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--ui-text-primary, #303133);
}

.focus-review-placeholder__body {
  margin: 0;
  font-size: 0.86rem;
  line-height: 1.55;
  max-width: 58ch;
}

.focus-meta-block {
  margin: 8px 0 10px;
  padding: 10px 12px;
  background: #fafafa;
  border-radius: 6px;
  font-size: 0.88rem;
  line-height: 1.55;
}

.focus-meta-line {
  margin: 0 0 4px;
}

.focus-meta-line:last-child {
  margin-bottom: 0;
}

.filter-empty {
  width: 100%;
  text-align: center;
  padding: 28px 16px;
  color: #909399;
  font-size: 0.95rem;
}

.filter-empty__main {
  margin: 0 auto;
  max-width: 40rem;
  line-height: 1.6;
  font-size: 0.92rem;
}

.filter-empty__anchor {
  margin: 0 0.2em;
  white-space: nowrap;
}

.trend-summary {
  width: 100%;
  max-width: 720px;
  margin-bottom: 16px;
  text-align: left;
}

.history-trend-card--sink {
  max-width: 100%;
  padding: 12px 14px !important;
  margin-bottom: 12px;
}

.history-trend-card--sink h2,
.history-trend-card--sink .history-trend-sink__h2 {
  font-size: 0.98rem;
}

.trend-summary h2 {
  margin: 0 0 10px;
  font-size: 1.08rem;
  font-weight: 700;
  color: var(--ui-text-primary);
  letter-spacing: -0.02em;
}

.trend-summary-list {
  margin: 0;
  padding-left: 1.2rem;
  color: #606266;
  line-height: 1.6;
}

.stats-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  width: 100%;
  max-width: 720px;
  margin-bottom: 24px;
  justify-content: center;
}

.history-stats-card--sink {
  max-width: 100%;
  justify-content: flex-start;
  margin-bottom: 16px;
}

.stat-card {
  flex: 1 1 140px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px 14px;
  text-align: center;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.stat-label {
  display: block;
  font-size: 0.75rem;
  color: #909399;
  margin-bottom: 6px;
}

.stat-value {
  font-size: 1.15rem;
  font-weight: 600;
  color: #303133;
}

.stat-value.up {
  color: #67c23a;
}

.stat-value.down {
  color: #f56c6c;
}

.stat-value.flat {
  color: #409eff;
}

.charts-section {
  width: 100%;
  max-width: 720px;
  margin-bottom: 28px;
}

.history-collapse--more .charts-section,
.history-collapse--more .stats-summary,
.history-collapse--more .trend-summary {
  max-width: 100%;
}

.charts-section h2 {
  font-size: 1.05rem;
  margin: 0 0 6px;
}

.charts-hint {
  font-size: 0.85rem;
  color: #909399;
  margin: 0 0 12px;
}

.charts-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chart-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px 14px 8px;
}

.chart-card h3 {
  margin: 0 0 8px;
  font-size: 0.95rem;
  color: #303133;
}

.spark-wrap {
  width: 100%;
}

.spark-svg {
  width: 100%;
  height: 160px;
  display: block;
}

.spark-label {
  font-size: 9px;
  fill: #909399;
}

.spark-empty {
  font-size: 0.85rem;
  color: #909399;
  padding: 24px 0;
  text-align: center;
}

.trend-message {
  width: 100%;
  max-width: 720px;
  padding: 15px;
  margin: 20px 0;
  border-radius: 8px;
  text-align: center;
  font-size: 1.1em;
  font-weight: bold;
}

.trend-message.positive {
  background: #f0f9eb;
  color: #67c23a;
  border: 1px solid #e1f5d9;
}

.trend-message.negative {
  background: #fef0f0;
  color: #f56c6c;
  border: 1px solid #fbc4c4;
}

.trend-message.neutral {
  background: #ecf5ff;
  color: #409eff;
  border: 1px solid #d9ecff;
}

.best-score {
  width: 100%;
  max-width: 720px;
  padding: 10px 15px;
  margin: 10px 0 20px;
  background: #f5f7fa;
  border-radius: 8px;
  text-align: center;
  font-size: 1em;
  color: #666;
}

.loading,
.error,
.empty {
  margin: 40px 0;
  text-align: center;
}

.error {
  color: #f56c6c;
}

.history-list {
  width: 100%;
}

.history-item {
  padding: 14px 16px;
  margin: 8px 0;
  box-sizing: border-box;
}

.history-item--invalid {
  opacity: 0.88;
  border-left-color: var(--ui-border-strong) !important;
  background: var(--ui-surface-subtle);
}

.history-item--invalid .item-header h3,
.history-item--invalid .history-item-session-title {
  color: #909399;
}

.history-invalid-reason {
  margin: 0 0 12px;
  font-size: 0.82rem;
  line-height: 1.5;
}

.mode-badge--invalid {
  background: #fdf6ec;
  color: #e6a23c;
  border: 1px solid #f5dab1;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.item-header h3 {
  margin: 0;
  font-size: 1.1em;
  color: #303133;
}

.timestamp {
  font-size: 0.9em;
  color: #909399;
}

.modality-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}

.modality {
  font-size: 0.8rem;
  padding: 2px 8px;
  border-radius: 4px;
  background: #f0f2f5;
  color: #606266;
}

.modality.ok {
  background: #f0f9eb;
  color: #67c23a;
}

.modality.bad {
  background: #fef0f0;
  color: #f56c6c;
}

.modality.unk {
  background: #f4f4f5;
  color: #909399;
}

.mode-badge {
  font-size: 0.75rem;
  padding: 2px 10px;
  border-radius: 999px;
  background: #ecf5ff;
  color: #409eff;
  border: 1px solid #d9ecff;
  white-space: nowrap;
}

.mode-badge--trailing {
  margin-left: auto;
}

.history-focus-trend-badge {
  background: #fdf6ec;
  color: #e6a23c;
  border-color: #faecd8;
}

.item-scores {
  display: flex;
  justify-content: space-around;
  flex-wrap: wrap;
  margin-bottom: 15px;
  gap: 8px;
}

.score-item {
  text-align: center;
  padding: 10px;
  background: white;
  border-radius: 4px;
  flex: 1;
  min-width: 72px;
  margin: 0 4px;
}

.score-item.total {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.score-item .label {
  display: block;
  font-size: 0.8em;
  margin-bottom: 5px;
}

.score-item .value {
  font-size: 1.2em;
  font-weight: bold;
}

.item-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 15px;
}

.history-demo-hint {
  width: 100%;
  max-width: 720px;
  margin: 0 0 16px;
  text-align: left;
}

.history-demo-hint__body {
  margin: 0 0 10px;
  font-size: 0.88rem;
  line-height: 1.55;
}

.history-demo-hint__cta {
  margin-top: 4px;
}

@media (max-width: 1024px) {
  .stats-summary,
  .charts-section,
  .history-demo-hint {
    max-width: 100%;
  }
}

@media (max-width: 768px) {
  .history-page {
    padding: 22px 10px 40px;
  }

  .item-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }

  .item-actions {
    justify-content: stretch;
  }

  .item-actions .el-button {
    flex: 1 1 calc(50% - 4px);
    min-width: 0;
  }

  .history-filter-tier {
    padding: 12px 12px 14px;
  }

  .valid-filter-row {
    flex-direction: column;
    align-items: stretch;
  }

  .history-clear-invalid-btn {
    width: 100%;
  }

  .modality-row {
    gap: 6px;
  }
}

@media (max-width: 600px) {
  .history-item-top {
    flex-direction: column;
  }

  .history-item-primary-cta {
    width: 100%;
    align-self: stretch;
  }

  .history-item-primary-cta :deep(.el-button--primary) {
    width: 100%;
  }
}

@media (max-width: 560px) {
  .history-item-primary--scan {
    grid-template-columns: 1fr;
    align-items: start;
    gap: 10px;
  }

  .hip-block {
    width: 100%;
  }

  .history-item-subrow {
    flex-direction: column;
    align-items: stretch;
  }

  .history-item-subrow__left {
    justify-content: flex-start;
  }

  .history-item-subrow__manage {
    margin-left: 0;
  }

  .history-item-subrow__manage :deep(.el-button) {
    width: 100%;
  }

  .focus-filter-group {
    width: 100%;
  }

  .focus-filter-group :deep(.el-radio-button) {
    flex: 1 1 calc(50% - 4px);
    min-width: 0;
  }

  .focus-filter-group :deep(.el-radio-button__inner) {
    width: 100%;
    padding: 8px 6px;
    font-size: 0.8rem;
  }
}

@media print {
  .no-print {
    display: none !important;
  }
}
</style>
