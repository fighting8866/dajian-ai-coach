<template>
  <div
    class="home-page home-page--brand-v1 home-page--console-v2 ui-page-frame ui-page-shell-inset"
    :class="{ 'home-page--demo-mode': demoModeState.active }"
  >
    <section
      class="home-tier-welcome ui-surface ui-panel--hero home-tier-welcome--v2 home-console-hero no-print"
      aria-labelledby="home-welcome-heading"
    >
      <div class="ui-l-desk-2 home-hero-2col home-console-grid">
        <div class="home-hero-2col__left home-console-hero__primary">
          <p class="ui-page-header__eyebrow home-welcome-eyebrow">答见 · 训练工作台</p>
          <h1 id="home-welcome-heading" class="home-welcome-hero-title">个人训练控制台</h1>
          <p class="home-welcome-line home-welcome-line--compact">
            <strong>{{ appDisplayName }}</strong><span class="muted"> · 答辩与演讲模拟训练，本页均为手动跳转</span>
          </p>
          <p class="home-welcome-action-line muted home-welcome-action-line--compact">{{ homeWelcomeActionLine }}</p>

          <div class="home-cta-block home-cta-block--primary home-cta-block--hero" role="group" aria-label="开始训练">
            <el-button type="primary" size="large" class="home-cta-main home-cta-main--xl" @click="onStartRegular">
              开始训练
            </el-button>
            <p class="home-cta-block-hint muted home-cta-block-hint--tight">
              训练页内完成环境检查后再手动开始；不会自动录音。
            </p>
          </div>

          <div class="home-cta-row home-cta-row--secondary home-cta-row--hero" role="group" aria-label="继续与常用入口">
            <el-dropdown trigger="click" @command="onWelcomeContinueCommand">
              <el-button
                size="large"
                plain
                :disabled="overviewLoading"
                :aria-label="'继续训练，沿用上次或按建议方向'"
              >
                继续训练
                <span class="home-dropdown-caret" aria-hidden="true">▾</span>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    command="resume"
                    :disabled="overviewLoading || !overviewReady"
                    :title="resumeLastDisabledTitle"
                  >
                    继续上次训练方式
                  </el-dropdown-item>
                  <el-dropdown-item
                    command="recommended"
                    :disabled="overviewLoading || !canApplyRecommended"
                    :title="applyRecommendedDisabledTitle"
                  >
                    按建议方向训练
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button size="large" plain @click="onViewHistory">历史</el-button>
            <el-button
              size="large"
              plain
              :disabled="!latestSessionId"
              :title="!latestSessionId ? '需先有一次有效训练' : '打开最近一次有效训练的报告'"
              @click="onDemoQuickViewLatestReport"
            >
              报告
            </el-button>
            <router-link class="home-cta-link-profile" to="/profile">档案</router-link>
          </div>

          <p
            v-if="!overviewLoading && (homeEmptyMode === 'first_time' || homeEmptyMode === 'no_valid_training')"
            class="home-cta-aux-hint muted"
          >
            完成一轮并提交后，「继续训练」与右侧概况会逐步可用。
          </p>
          <div class="home-welcome-aux-row no-print">
            <el-button type="info" text size="small" @click="openHomeDemoAuxCollapse">
              附录：演示向导与系统状态
            </el-button>
          </div>
        </div>

        <div class="home-hero-2col__right home-console-hero__aside">
          <section
            v-if="showReturnUserSummary"
            class="home-first-screen-summary home-first-screen-summary--spotlight ui-surface ui-surface--subtle no-print"
            aria-label="最近有效训练摘要"
          >
            <p class="home-first-screen-summary__eyebrow">最近一轮（有效训练）</p>
            <h2 class="home-first-screen-summary__title">表现快照</h2>
            <ul class="home-first-screen-summary__grid" aria-label="最近一轮要点">
              <li>
                <span class="home-first-screen-summary__k">时间</span>
                <strong class="home-first-screen-summary__v">{{ latestTimeLabel }}</strong>
              </li>
              <li class="home-first-screen-summary__li--score">
                <span class="home-first-screen-summary__k">总分</span>
                <strong class="home-first-screen-summary__v home-first-screen-summary__v--score">{{ latestScoreLabel }}</strong>
              </li>
              <li>
                <span class="home-first-screen-summary__k">训练重点</span>
                <strong class="home-first-screen-summary__v">{{ latestFocusLabel }}</strong>
              </li>
              <li class="home-first-screen-summary__li--rec">
                <span class="home-first-screen-summary__k">推荐继续</span>
                <strong class="home-first-screen-summary__v">{{ recommendFocusLabel }}</strong>
              </li>
            </ul>
            <p v-if="returnSummaryDetailLine" class="home-first-screen-summary__line muted">
              {{ returnSummaryDetailLine }}
            </p>
            <p class="home-first-screen-summary__more muted">
              <el-button type="primary" text size="small" @click="openHomeCoreCollapseFromSummary">
                完整数据、目标与设置
              </el-button>
            </p>
          </section>
          <div
            v-else
            class="home-hero-2col__stub home-hero-2col__stub--compact ui-surface ui-surface--subtle no-print"
            aria-label="完成首轮后的概况"
          >
            <p class="home-hero-2col__stub-eyebrow muted">概况预览</p>
            <h2 class="home-hero-2col__stub-title">先完成一轮有效训练</h2>
            <p class="home-hero-2col__stub-lead muted">
              提交后此处会显示最近得分、专项与系统建议方向。
            </p>
          </div>
        </div>
      </div>
    </section>

    <section class="home-console-mid no-print" aria-label="训练数据概览">
      <ul class="home-metric-deck">
        <li class="home-metric-deck__cell">
          <span class="home-metric-deck__k">有效训练</span>
          <strong class="home-metric-deck__v">{{ homeConsoleValidSessionsLabel }}</strong>
          <span class="home-metric-deck__unit muted">次</span>
        </li>
        <li class="home-metric-deck__cell">
          <span class="home-metric-deck__k">最佳总分</span>
          <strong class="home-metric-deck__v">{{ homeConsoleBestScoreLabel }}</strong>
        </li>
        <li class="home-metric-deck__cell">
          <span class="home-metric-deck__k">最近得分</span>
          <strong class="home-metric-deck__v">{{ latestScoreLabel }}</strong>
        </li>
        <li class="home-metric-deck__cell">
          <span class="home-metric-deck__k">当前专项</span>
          <strong class="home-metric-deck__v">{{ latestFocusLabel }}</strong>
        </li>
        <li class="home-metric-deck__cell home-metric-deck__cell--accent">
          <span class="home-metric-deck__k">推荐方向</span>
          <strong class="home-metric-deck__v">{{ recommendFocusLabel }}</strong>
        </li>
        <li class="home-metric-deck__cell">
          <span class="home-metric-deck__k">最近训练时间</span>
          <strong class="home-metric-deck__v home-metric-deck__v--time">{{ latestTimeLabel }}</strong>
        </li>
      </ul>
      <div class="home-console-quicklinks" role="navigation" aria-label="快捷入口">
        <span class="home-console-quicklinks__label muted">快捷</span>
        <router-link class="home-console-quicklinks__a" to="/training">训练</router-link>
        <router-link class="home-console-quicklinks__a" to="/history">历史</router-link>
        <router-link class="home-console-quicklinks__a" to="/profile">档案</router-link>
        <el-button link type="primary" class="home-console-quicklinks__btn" @click="openHomeCoreCollapseFromSummary">
          概况与设置
        </el-button>
      </div>
    </section>

    <el-alert
      v-if="demoModeState.active"
      class="home-demo-mode-banner home-demo-mode-banner--compact no-print"
      type="success"
      :closable="false"
      show-icon
      title="当前为演示用精简模式"
    >
      <p class="home-demo-mode-banner__body muted">
        本页会突出分步说明、运行状态与产品能力。可随时退出，恢复与日常一致的排布。
      </p>
      <div class="home-demo-mode-banner__actions">
        <el-button size="small" type="primary" plain @click="onExitDemoMode">退出演示模式</el-button>
        <el-button size="small" @click="onStartRegular">去训练</el-button>
      </div>
    </el-alert>

    <el-collapse v-model="homeAuxCollapse" class="ui-aux-collapse ui-aux-collapse--low home-aux-collapse no-print">
      <el-collapse-item title="附录：演示向导、系统状态与产品说明（默认收起）" name="aux">
        <p v-if="!demoModeState.active" class="home-demo-mode-enter no-print">
          <el-button text type="primary" size="small" @click="onEnterDemoMode">开启适合演示的精简展示</el-button>
          <span class="home-demo-mode-enter__hint muted">仅影响本页与说明的排布，训练与评分规则不变</span>
        </p>
    <header class="home-hero">
      <h2 class="home-title">产品说明与可选演示流程</h2>
      <p class="home-hero-eyebrow muted">答辩与演讲的模拟训练、复盘与留档</p>
      <p v-if="homeEmptyMode === 'first_time'" class="home-lead home-lead--compact">
        需要对外讲解产品能力时，可按「训练 → 结果 → 报告 → 历史」顺序手动跳转完成闭环介绍；与日常训练为同一套页面，每步需自行操作，不会自动开始训练。
      </p>
      <p v-else class="home-lead">
        对评审或内部分享时，可用下方分步说明配合快捷入口在约一两分钟内说清主路径；与训练前自检同源的链路与本机/开发板状态见「系统状态」区域。
      </p>
      <p class="home-competition-tag muted">
        你的最近一次有效训练与统计仍在下方「训练数据、目标与设置」中展示；与导航栏中「历史」一致。
      </p>
    </header>

    <section
      class="home-demo-entry ui-surface"
      :class="{ 'home-demo-entry--spotlight': demoModeState.active }"
      aria-labelledby="home-demo-entry-title"
    >
      <h2 id="home-demo-entry-title" class="home-section-title">分步：训练、结果、报告、历史</h2>
      <p class="home-demo-lead muted">
        建议顺序（均为手动跳转，不会自动开始训练）：完整训练 — 结果与本次链路 — 可打印报告 — 历史与专项复盘。
      </p>
      <ol class="home-demo-steps">
        <li><strong>训练</strong>：完成一轮讲解与问答并提交结果</li>
        <li><strong>结果</strong>：展示评分、点评与本轮分析链路（本机/开发板）</li>
        <li><strong>报告</strong>：结构化留档，可现场打印或导出 PDF</li>
        <li><strong>历史</strong>：专项筛选与有效训练总览，收束复盘叙事</li>
      </ol>

      <div class="home-demo-primary" aria-live="polite">
        <template v-if="overviewLoading">
          <p class="home-demo-primary-wait muted">{{ PAGE_LOADING.homeDemoPrimary }}</p>
        </template>
        <template v-else-if="demoPrimaryKind === 'continue_latest'">
          <el-button type="primary" size="large" class="home-demo-primary-btn" @click="onDemoContinueLatest">
            继续演示最近一轮
          </el-button>
          <p class="home-demo-primary-hint muted">
            将打开<strong>最近一次有效训练</strong>的结果页，便于接着向评委展示报告与历史环节。
          </p>
        </template>
        <template v-else-if="demoPrimaryKind === 'first_round'">
          <el-button type="primary" size="large" class="home-demo-primary-btn" @click="onDemoStartFirstRound">
            开始第一轮训练演示
          </el-button>
          <p class="home-demo-primary-hint muted">尚无训练记录：从训练页完成自检后，手动开始本轮演示即可。</p>
        </template>
        <template v-else>
          <el-button type="primary" size="large" class="home-demo-primary-btn" @click="onDemoFullTraining">
            开始完整训练演示
          </el-button>
          <p v-if="homeEmptyMode === 'no_valid_training'" class="home-demo-primary-hint muted">
            当前尚无可纳入统计的完整训练：请先完整跑通一轮并提交，演示数据会更完整。
          </p>
          <p v-else-if="overviewLoadError" class="home-demo-primary-hint muted">
            概况暂时不可用，仍可由此进入训练页；加载恢复后首页将自动更新。
          </p>
        </template>
      </div>

      <div class="home-demo-quick">
        <p class="home-demo-quick-label">同一路径的快捷入口</p>
        <div class="home-demo-quick-grid">
          <el-button size="large" @click="onDemoQuickFullTraining">去训练（演示）</el-button>
          <el-button
            size="large"
            :disabled="!latestSessionId"
            :title="!latestSessionId ? '需先有一次有效训练记录' : '打开最近一次有效训练结果'"
            @click="onDemoQuickViewLatestResult"
          >
            最近有效结果
          </el-button>
          <el-button
            size="large"
            :disabled="!latestSessionId"
            :title="!latestSessionId ? '需先有一次有效训练记录' : '打开可打印的对应报告'"
            @click="onDemoQuickViewLatestReport"
          >
            最近有效报告
          </el-button>
          <el-button size="large" @click="onDemoQuickViewHistory">查看历史</el-button>
        </div>
        <p class="home-demo-quick-foot muted">
          「最近有效」与顶部概况同源；无记录时请先跑通主按钮中的完整训练并提交，再回来看结果/报告。
        </p>
      </div>
    </section>

    <section
      class="home-system-overview ui-surface ui-surface--subtle"
      :class="{ 'home-system-overview--spotlight': demoModeState.active }"
      aria-labelledby="home-system-overview-title"
    >
      <h2 id="home-system-overview-title" class="home-section-title">系统状态</h2>
      <p class="home-section-sub muted">
        与训练前自检同源，便于确认语音、视觉、文档解析与开发板连通性（仅展示，不会自动开始训练）。
      </p>
      <div v-if="systemStatusLoading" class="home-system-loading muted" aria-busy="true" aria-live="polite">
        {{ PAGE_LOADING.systemStatus }}
      </div>
      <div v-else-if="systemStatusError" class="home-system-error">
        <el-alert type="error" :closable="false" show-icon :title="PAGE_ERROR_ALERT_TITLE.systemStatus">
          <p class="home-system-error__body">{{ systemStatusError }}</p>
          <div class="home-system-error__actions">
            <el-button size="small" type="primary" @click="loadSystemStatus">重试</el-button>
            <el-button size="small" @click="onStartRegular">去训练</el-button>
          </div>
        </el-alert>
      </div>
      <ul v-else-if="systemStatus" class="home-system-grid">
        <li>
          <span class="home-sys-k">语音分析</span>
          <strong class="home-sys-v">{{ humanSpeechRoute(systemStatus.speech_provider) }}</strong>
        </li>
        <li>
          <span class="home-sys-k">画面与仪态分析</span>
          <strong class="home-sys-v">{{ humanVisionRoute(systemStatus.vision_provider) }}</strong>
        </li>
        <li>
          <span class="home-sys-k">课件文档解析</span>
          <strong class="home-sys-v">{{ humanDocParser(systemStatus.document_parser_provider) }}</strong>
        </li>
        <li>
          <span class="home-sys-k">开发板参与推理</span>
          <strong class="home-sys-v">{{ systemBoardParticipationLabel }}</strong>
        </li>
        <li>
          <span class="home-sys-k">开发板地址已配置</span>
          <strong class="home-sys-v">{{ systemStatus.ascend_base_url_configured ? '是' : '否' }}</strong>
        </li>
        <li>
          <span class="home-sys-k">开发板健康检查</span>
          <strong class="home-sys-v">{{ systemBoardHealthLabel }}</strong>
        </li>
        <li class="home-system-grid__full">
          <span class="home-sys-k">系统状态摘要</span>
          <span class="home-sys-desc">{{ systemHealthUserLine }}</span>
        </li>
        <li v-if="ascendRuntimeSummaryLine" class="home-system-grid__full">
          <span class="home-sys-k">板侧服务运行环境</span>
          <span class="home-sys-desc home-sys-desc--code">{{ ascendRuntimeSummaryLine }}</span>
        </li>
      </ul>
    </section>

    <section
      class="home-capabilities ui-surface ui-surface--subtle"
      :class="{ 'home-capabilities--spotlight': demoModeState.active }"
      aria-labelledby="home-capabilities-title"
    >
      <h2 id="home-capabilities-title" class="home-section-title">产品能力</h2>
      <ul class="home-capabilities-list">
        <li><strong>语音表达分析：</strong>语速、停顿、口头禅与转写，支撑答辩表达复盘。</li>
        <li><strong>仪态与视觉分析：</strong>正视、低头与稳定度等，支撑仪态专项训练。</li>
        <li><strong>模拟答辩问答：</strong>讲解后与问答评估、规则追问衔接，贴近真实答辩节奏。</li>
        <li><strong>训练报告与专项复盘：</strong>结构化报告可打印留档，历史页支持专项筛选与有效训练总览。</li>
      </ul>
      <p class="home-capabilities-foot muted">
        分析任务可在本机或昇腾开发板上执行，具体以「系统状态」与训练页当前链路为准。
      </p>
    </section>
      </el-collapse-item>
    </el-collapse>

    <el-alert
      v-if="returnFromTrainingNoticeVisible"
      class="home-return-alert no-print"
      :class="{ 'home-when-demo-soft': demoModeState.active }"
      type="success"
      :closable="true"
      show-icon
      title="已完成上一轮训练"
      @close="returnFromTrainingNoticeVisible = false"
    >
      <p class="home-return-alert__body">
        下方已展开「训练数据、目标与设置」，可查看更新后的概况与目标；需要时仍可从顶部主按钮与「继续训练」继续练习。
      </p>
    </el-alert>

    <el-collapse
      v-model="homeCoreCollapse"
      class="ui-aux-collapse ui-aux-collapse--low home-core-collapse no-print"
    >
      <el-collapse-item title="详细：训练数据、目标与设置（默认收起）" name="core">
    <div class="home-tier-core ui-stack home-tier-core--brand ui-dashboard-spine">
      <header class="ui-page-header home-main-header no-print">
        <p class="ui-page-header__eyebrow">主页</p>
        <h2 class="ui-section-title home-main-header__title">概况与目标</h2>
        <p class="ui-section-sub home-main-header__sub">
          {{
            overviewLoading
              ? PAGE_LOADING.homeOverview.hint
              : '可纳入统计的练习、目标、节奏与周报集中在此，便于安排后续练习。'
          }}
        </p>
      </header>
    <section class="home-overview ui-surface home-overview--v1" aria-labelledby="home-overview-title">
      <h2 id="home-overview-title" class="home-section-title">
        {{ homeEmptyMode === 'first_time' ? '从这里开始' : SECTION.recentOverview }}
      </h2>
      <p
        v-if="homeEmptyMode === 'first_time'"
        class="home-section-sub muted"
        :class="{ 'home-when-demo-soft': demoModeState.active }"
      >
        本账号下暂时还没有历史记录。下面用最短路径说明如何开始训练、练完能看什么，不必一次记全。
      </p>
      <p
        v-else-if="homeEmptyMode === 'no_valid_training'"
        class="home-section-sub muted"
        :class="{ 'home-when-demo-soft': demoModeState.active }"
      >
        你已有部分记录，但尚<strong>没有可纳入趋势与总览的完整训练</strong>（与历史总览统计口径一致）。再完成一轮并正常提交即可。
      </p>
      <p
        v-else-if="!showReturnUserSummary"
        class="home-section-sub muted"
        :class="{ 'home-when-demo-soft': demoModeState.active }"
      >
        以下仅统计<strong>可纳入统计的练习</strong>，与历史页「{{ SECTION.validTrainingOverview }}」同源；数据不足时会自动弱化展示。
      </p>
      <p
        v-else
        class="home-section-sub muted"
        :class="{ 'home-when-demo-soft': demoModeState.active }"
      >
        与页面顶部「最近有效训练」摘要同源；下含目标、节奏、周报与下阶段建议等完整说明。
      </p>

      <div v-if="overviewLoading" class="home-overview-loading" aria-busy="true" aria-live="polite">
        <p class="home-overview-loading-label muted">{{ PAGE_LOADING.homeOverview.label }}</p>
        <p class="home-overview-loading-hint muted">{{ PAGE_LOADING.homeOverview.hint }}</p>
        <el-skeleton animated :rows="4" />
      </div>
      <div v-else-if="overviewLoadError" class="home-overview-error">
        <el-alert type="error" :closable="false" show-icon :title="PAGE_ERROR_ALERT_TITLE.homeOverview">
          <p class="home-overview-error__body">{{ overviewLoadError }}</p>
          <p class="home-overview-error__next muted">可先使用顶部「开始训练」；网络正常后点「重试」以刷新概况。</p>
          <div class="home-overview-error__actions">
            <el-button type="primary" size="small" :loading="overviewLoading" @click="retryLoadOverview">
              重试
            </el-button>
            <el-button size="small" @click="onStartRegular">去训练</el-button>
          </div>
        </el-alert>
      </div>
      <div v-else-if="homeEmptyMode === 'first_time'" class="home-onboarding">
        <p class="home-onboarding-lead">
          一轮训练里通常先<strong>讲解</strong>（可配合课件再猜页）再进<strong>模拟问答</strong>。结束后你会看到总分、分项、文字点评，以及可打印的报告；也可在「历史」中继续查看与复盘。
        </p>
        <ul class="home-onboarding-list" :class="{ 'home-when-demo-soft': demoModeState.active }">
          <li><strong>现在：</strong>到页面最上方点「开始训练」，在训练页通过准备检查后手动开始；麦克风与摄像头需由你授权。</li>
          <li><strong>选模式：</strong>有课件/无课件均可完整练完；有课件时多了对齐与猜页，无课件时更侧重语言与问答。</li>
          <li><strong>之后：</strong>练完会回到结果页，再从菜单进历史；首页「概况」在产生有效训练后会自动变丰富。</li>
        </ul>
        <div class="home-onboarding-cta-row">
          <el-button type="primary" plain size="large" class="home-onboarding-cta" @click="onStartRegular">
            去训练
          </el-button>
          <el-button size="large" plain @click="onViewHistory">查看历史</el-button>
        </div>
        <p class="home-onboarding-foot muted">
          与页面顶部主按钮相同，会进入训练页。点击「更多：演示、系统状态与产品说明」可查看分步演示与系统状态，不影响训练与评分规则。
        </p>
      </div>
      <div v-else-if="homeEmptyMode === 'no_valid_training'" class="home-no-valid-card">
        <p class="home-no-valid-title">还没有可纳入汇总的记录</p>
        <p class="home-no-valid-lead muted">
          常见原因：环境过吵、未跑完全程、未正常提交，或单轮未满足统计条件。与历史里「有效训练总览」口径一致。
        </p>
        <p class="muted">建议回到训练页再跑通完整一轮，并在结束时看到提交成功提示或自动跳转结果页。</p>
        <div class="home-no-valid-actions">
          <el-button type="primary" class="home-no-valid-cta" @click="onDemoFullTraining">去训练并提交</el-button>
          <el-button plain class="home-no-valid-cta" @click="onViewHistory">到历史看已有记录</el-button>
        </div>
      </div>
      <ul v-else-if="overviewReady && !showReturnUserSummary" class="home-overview-grid">
        <li>
          <span class="home-ok">最近一次有效训练时间</span>
          <strong class="home-ov-value">{{ latestTimeLabel }}</strong>
        </li>
        <li>
          <span class="home-ok">最近一次训练重点</span>
          <strong class="home-ov-value">{{ latestFocusLabel }}</strong>
        </li>
        <li>
          <span class="home-ok">最近一次有效总分</span>
          <strong class="home-ov-value">{{ latestScoreLabel }}</strong>
        </li>
        <li>
          <span class="home-ok">建议继续训练方向</span>
          <strong class="home-ov-value">{{ recommendFocusLabel }}</strong>
        </li>
      </ul>
      <p v-if="overviewReady && overviewNote && !showReturnUserSummary" class="home-overview-note muted">
        {{ overviewNote }}
      </p>
    </section>

    <section
      class="home-training-goals ui-surface home-panel-pad"
      :class="{ 'home-when-demo-soft': demoModeState.active }"
      aria-labelledby="home-training-goals-title"
    >
      <h2 id="home-training-goals-title" class="home-section-title">训练目标与当前进度</h2>
      <p class="home-section-sub muted">
        在下方设定轻量目标后，系统会结合你已有的<strong>有效训练</strong>记录，估算总分与次数进度（仅展示，不改评分与流程）。
      </p>
      <div v-if="overviewLoading" class="home-goal-loading muted" aria-busy="true" aria-live="polite">
        {{ PAGE_LOADING.homeOverview.label }}
      </div>
      <template v-else-if="!overviewLoadError">
        <ul v-if="homeGoalDisplayLines.length" class="home-goal-lines">
          <li v-for="(ln, i) in homeGoalDisplayLines" :key="`hg-${i}`">{{ ln }}</li>
        </ul>
        <p v-else class="home-goal-empty muted">
          尚未设定训练目标。可点击按钮添加「目标总分 / 目标专项 / 有效训练次数」中的任意组合。
        </p>
        <div v-if="homeGoalStatusHeadline" class="home-goal-status-banner">
          <span class="home-goal-status-label">目标状态</span>
          <strong class="home-goal-status-text">{{ homeGoalStatusHeadline }}</strong>
        </div>
        <div v-if="homeStageSummaryVisible" class="home-goal-stage">
          <p class="home-goal-stage-title">阶段小结（规则版）</p>
          <p class="home-goal-stage-k muted">当前阶段主要进步</p>
          <ul class="home-goal-stage-list muted">
            <li v-for="(ln, i) in homeStageMainLines" :key="`sm-${i}`">{{ ln }}</li>
          </ul>
          <p class="home-goal-stage-k muted">仍需继续关注</p>
          <ul class="home-goal-stage-list muted">
            <li v-for="(ln, i) in homeStageNeedLines" :key="`sn-${i}`">{{ ln }}</li>
          </ul>
          <p v-if="homeStageNextLabel" class="home-goal-stage-next muted">{{ homeStageNextLabel }}</p>
        </div>
        <div v-if="homeGoalAchieved" class="home-goal-achieved-actions">
          <el-button type="success" plain size="small" @click="openGoalDialog">调整目标</el-button>
          <el-button v-if="homeHasTargetFocus" size="small" @click="onConsolidateGoalFocus">
            继续巩固当前专项
          </el-button>
        </div>
        <div class="home-goal-actions">
          <el-button type="primary" plain size="default" @click="openGoalDialog">
            {{ goalDialogButtonLabel }}
          </el-button>
        </div>
      </template>
      <p v-else class="home-goal-empty muted">概况暂不可用，无法计算进度；网络恢复后刷新首页即可。</p>
    </section>

    <section
      class="home-training-rhythm ui-surface home-panel-pad"
      :class="{ 'home-when-demo-soft': demoModeState.active }"
      aria-labelledby="home-training-rhythm-title"
    >
      <h2 id="home-training-rhythm-title" class="home-section-title">训练节奏与连续练习</h2>
      <p class="home-section-sub muted">
        仅统计<strong>有效训练</strong>的日期与次数，帮助你把握最近一周、两周的练习密度与连续性（本地自然日，不做社交打卡）。
      </p>
      <div v-if="overviewLoading" class="home-rhythm-loading muted" aria-busy="true" aria-live="polite">
        {{ PAGE_LOADING.homeOverview.label }}
      </div>
      <template v-else-if="!overviewLoadError">
        <ul v-if="homeRhythmLines.length" class="home-rhythm-lines">
          <li v-for="(ln, i) in homeRhythmLines" :key="`hr-${i}`">{{ ln }}</li>
        </ul>
        <p
          v-else
          class="home-rhythm-empty muted"
        >
          {{
            homeEmptyMode === 'first_time' || homeEmptyMode === 'no_valid_training'
              ? '出现有效训练后，这里会汇总近一两周的练习日期与强度，帮你看清节奏。'
              : '暂无足够数据生成节奏说明，多练几轮有效训练后会自动填充。'
          }}
        </p>
      </template>
      <p v-else class="home-rhythm-empty muted">概况暂不可用，无法汇总节奏。</p>
    </section>

    <section
      v-if="homeWeeklyReviewVisible"
      class="home-weekly-summary ui-surface home-panel-pad"
      :class="{ 'home-when-demo-soft': demoModeState.active }"
      aria-labelledby="home-weekly-summary-title"
    >
      <h2 id="home-weekly-summary-title" class="home-section-title">{{ SECTION.weeklySummary }}</h2>
      <p class="home-section-sub muted">
        用最近一周的有效训练快速回答「练了多少、练了什么、接下来往哪走」（数据不足时会自动多看几轮，方便起步阶段也能参考）。
      </p>
      <ul v-if="homeWeeklyLines.length" class="home-weekly-lines">
        <li v-for="(ln, i) in homeWeeklyLines" :key="`hw-${i}`">{{ ln }}</li>
      </ul>
    </section>

    <section
      v-if="homeNextPlanVisible"
      class="home-next-plan ui-surface home-panel-pad"
      :class="{ 'home-when-demo-soft': demoModeState.active }"
      aria-labelledby="home-next-plan-title"
    >
      <h2 id="home-next-plan-title" class="home-section-title">{{ SECTION.nextStageSuggest }}</h2>
      <p class="home-section-sub muted">
        结合你的目标进度、最近周报和练习节奏给出的<strong>规则版</strong>提示，不代替你自己的安排。
      </p>
      <div class="home-next-plan-card">
        <p class="home-next-plan-kind">
          <span class="muted">当前建议类型：</span>
          <strong>{{ homeNextPlan.next_plan_action_label }}</strong>
        </p>
        <p class="home-next-plan-body">{{ homeNextPlan.next_plan_user_line }}</p>
        <p v-if="homeNextPlanFocusLine" class="home-next-plan-focus muted">{{ homeNextPlanFocusLine }}</p>
      </div>
    </section>
    </div>

    <p class="home-settings-migrate muted">
      默认训练偏好、历史页与训练页提示等已迁至侧栏「设置中心」。
      <el-button link type="primary" @click="goSettingsPage">前往设置中心</el-button>
    </p>
      </el-collapse-item>
    </el-collapse>

    <el-dialog
      v-model="goalDialogOpen"
      title="训练目标"
      width="min(480px, 92vw)"
      destroy-on-close
      class="home-goal-dialog-el"
      @opened="onGoalDialogOpened"
    >
      <div class="home-goal-dialog">
        <p class="home-goal-dialog-lead muted">
          任选一项或多项组合即可。保存后会在首页、历史、训练与结果页轻量提示进度（数据来自当前账号在本机的历史记录）。
        </p>
        <div class="home-goal-form-row">
          <span class="home-goal-form-k">目标总分</span>
          <div class="home-goal-form-v">
            <el-input-number
              v-model="trainingGoalsUi.target_total_score"
              :min="0"
              :max="100"
              :step="0.5"
              :precision="1"
              placeholder="不设"
              controls-position="right"
              class="home-goal-num"
            />
            <el-button link type="primary" size="small" @click="trainingGoalsUi.target_total_score = null">
              不设总分目标
            </el-button>
          </div>
        </div>
        <div class="home-goal-form-row">
          <span class="home-goal-form-k">目标专项</span>
          <el-select v-model="trainingGoalsUi.target_focus" placeholder="可选" clearable class="home-goal-select">
            <el-option label="语言专项" value="language" />
            <el-option label="仪态专项" value="posture" />
            <el-option label="问答专项" value="qa" />
            <el-option label="内容专项" value="content" />
          </el-select>
        </div>
        <div class="home-goal-form-row">
          <span class="home-goal-form-k">目标有效训练次数</span>
          <el-select
            v-model="trainingGoalsUi.target_valid_session_count"
            placeholder="可选"
            clearable
            class="home-goal-select"
          >
            <el-option label="3 次" :value="3" />
            <el-option label="5 次" :value="5" />
            <el-option label="10 次" :value="10" />
          </el-select>
        </div>
        <div class="home-goal-dialog-actions">
          <el-button type="primary" @click="saveTrainingGoalsFromDialog">保存</el-button>
          <el-button @click="goalDialogOpen = false">取消</el-button>
          <el-button link type="danger" @click="onResetTrainingGoals">清除全部目标</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, inject, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getJson } from '../api/base'
import { toUserFacingMessage } from '../utils/userFacingError'
import { pageFeedback, trainingConfirmDanger } from '../utils/pageFeedback'
import {
  readAppPreferences,
  TRAINING_FOCUS_HANDOFF_KEY,
  TRAINING_RUNTIME_SNAPSHOT_KEY,
} from '../utils/appPreferences'
import { writeUserScopedItem, removeUserScopedItem, getActiveUserId } from '../utils/userScopedStorage'
import { hydrateAccountSettings, pushFullAccountSettingsToServer } from '../utils/accountSettingsSync'
import {
  readTrainingGoals,
  writeTrainingGoals,
  resetTrainingGoals,
  goalsSnapshotForLog,
  computeTrainingGoalProgress,
  hasActiveTrainingGoals,
  TRAINING_GOAL_FOCUS_LABEL,
  TRAINING_GOALS_CHANGED_EVENT,
} from '../utils/trainingGoals'
import { computeGoalStatusPack, buildStageSummary, GOAL_STATUS } from '../utils/trainingGoalStatus'
import { computeTrainingRhythm, buildHomeRhythmLines } from '../utils/trainingStreaks'
import { computeWeeklyTrainingReview, buildHomeWeeklyDisplayLines } from '../utils/trainingWeeklyReview'
import { computeNextTrainingPlan } from '../utils/nextTrainingPlan'
import {
  humanSpeechRoute,
  humanVisionRoute,
  humanDocParser,
} from '../utils/inferenceChainLabels'
import {
  readDemoMode,
  enterDemoMode,
  exitDemoMode,
  activateDemoModeFromRouteQuery,
  stripDemoQueryKeys,
} from '../utils/demoMode'
import { SECTION, trainingFocusLabel } from '../constants/productTerms'
import { PAGE_LOADING, PAGE_ERROR_ALERT_TITLE } from '../constants/pageStatusCopy'
import { focusFirstInContainer } from '../utils/a11yFocus'

const router = useRouter()
const route = useRoute()

const appDisplayName = inject('appDisplayName', ref('同学'))

/** 默认折叠：演示 / 状态与能力，减少首屏噪音 */
const homeAuxCollapse = ref([])
/** 默认折叠：概况、目标与设置，减少首屏信息墙 */
const homeCoreCollapse = ref([])

const demoModeState = ref(readDemoMode())

function refreshDemoModeState() {
  demoModeState.value = readDemoMode()
  const active = !!demoModeState.value.active
  console.log('[Home.demo_mode] active=', active)
  console.log(
    '[Home.demo_mode] highlighted_sections=',
    active ? ['demo_entry', 'system_overview', 'capabilities', 'demo_quick'] : []
  )
}

function onEnterDemoMode() {
  enterDemoMode({})
  refreshDemoModeState()
}

function onExitDemoMode() {
  exitDemoMode()
  refreshDemoModeState()
}

/** 从「比赛演示入口」操作时保持/进入精简态（不强制清除预设标记） */
function engageDemoModeForHomeEntry() {
  enterDemoMode({})
  refreshDemoModeState()
}

const HISTORY_DATA_CHANGED_EVENT = 'mianshi-history-changed'

const validTrainingOverview = ref(null)
/** 与 /history 同源，用于目标进度（含全部记录，不仅概况） */
const homeHistoryList = ref([])
const overviewLoading = ref(true)
const overviewLoadError = ref('')
const returnFromTrainingNoticeVisible = ref(false)

const goalsRevision = ref(0)
function bumpGoalsRevision() {
  goalsRevision.value++
}

const trainingGoalsUi = ref(readTrainingGoals())
const goalDialogOpen = ref(false)

function openGoalDialog() {
  goalDialogOpen.value = true
}

function onGoalDialogOpened() {
  trainingGoalsUi.value = { ...readTrainingGoals() }
  console.log('[Home.goal] goal=', goalsSnapshotForLog(trainingGoalsUi.value))
  nextTick(() => {
    focusFirstInContainer('.home-goal-dialog-el')
  })
}

async function saveTrainingGoalsFromDialog() {
  const next = writeTrainingGoals({ ...trainingGoalsUi.value })
  trainingGoalsUi.value = { ...next }
  goalsRevision.value++
  console.log('[Home.goal] goal=', goalsSnapshotForLog(next))
  try {
    await pushFullAccountSettingsToServer()
    pageFeedback('Home', 'training_goals_saved', '训练目标已保存并同步到账号。', 'success')
  } catch (_) {
    pageFeedback(
      'Home',
      'goals_sync_failed',
      '目标已保存在本机，同步到账号失败，请检查网络后重试。',
      'warning'
    )
  }
  goalDialogOpen.value = false
}

async function onResetTrainingGoals() {
  const ok = await trainingConfirmDanger({
    title: '清除训练目标',
    message: '将清除已保存的总分、专项与次数目标。确定继续？',
    confirmButtonText: '清除',
    cancelButtonText: '取消',
  })
  if (!ok) return
  trainingGoalsUi.value = resetTrainingGoals()
  goalsRevision.value++
  console.log('[Home.goal] goal=', goalsSnapshotForLog(trainingGoalsUi.value))
  try {
    await pushFullAccountSettingsToServer()
    pageFeedback('Home', 'training_goals_reset', '已清除训练目标并同步到账号。', 'success')
  } catch (_) {
    pageFeedback(
      'Home',
      'goals_sync_failed',
      '目标已在本机清除，同步到账号失败，请稍后重试。',
      'warning'
    )
  }
}

const homeGoalProgress = computed(() => {
  void goalsRevision.value
  return computeTrainingGoalProgress({
    goals: readTrainingGoals(),
    historyList: homeHistoryList.value,
    overview: validTrainingOverview.value,
  })
})

const homeGoalStatusPack = computed(() => {
  void goalsRevision.value
  return computeGoalStatusPack(homeGoalProgress.value)
})

const homeRhythmStats = computed(() => {
  void goalsRevision.value
  const p = homeGoalProgress.value
  let countRemaining = null
  if (p.validCountProgress) {
    const r = p.validCountProgress.target - p.validCountProgress.current
    countRemaining = r > 0 ? r : null
  }
  return computeTrainingRhythm(homeHistoryList.value, {
    goalStatus: homeGoalStatusPack.value.status,
    targetFocus: p.goals?.target_focus || null,
    countRemaining,
  })
})

const homeRhythmLines = computed(() => buildHomeRhythmLines(homeRhythmStats.value, homeGoalProgress.value))

const homeWeeklyReview = computed(() => {
  void goalsRevision.value
  return computeWeeklyTrainingReview(homeHistoryList.value, {
    overview: validTrainingOverview.value,
    goals: readTrainingGoals(),
  })
})

const homeWeeklyLines = computed(() => buildHomeWeeklyDisplayLines(homeWeeklyReview.value))

const homeWeeklyReviewVisible = computed(() => {
  if (overviewLoading.value || overviewLoadError.value) return false
  return (homeWeeklyReview.value?.weekly_valid_count || 0) > 0
})

const homeNextPlan = computed(() => {
  void goalsRevision.value
  return computeNextTrainingPlan({
    historyList: homeHistoryList.value,
    overview: validTrainingOverview.value,
    goals: readTrainingGoals(),
    goalProgress: homeGoalProgress.value,
    goalStatusPack: homeGoalStatusPack.value,
    rhythmStats: homeRhythmStats.value,
    weeklyReview: homeWeeklyReview.value,
  })
})

const homeNextPlanVisible = computed(() => {
  if (overviewLoading.value || overviewLoadError.value) return false
  return !!homeNextPlan.value?.next_plan_action
})

const homeNextPlanFocusLine = computed(() => {
  const f = homeNextPlan.value?.next_plan_focus
  if (!f) return ''
  const lab = TRAINING_GOAL_FOCUS_LABEL[f] || f
  return `下一阶段可优先练：${lab}专项`
})

const homeStageSummary = computed(() => {
  void goalsRevision.value
  return buildStageSummary({
    progress: homeGoalProgress.value,
    statusPack: homeGoalStatusPack.value,
    overview: validTrainingOverview.value,
    trendHint: {},
  })
})

const homeGoalStatusHeadline = computed(() => {
  if (!hasActiveTrainingGoals(readTrainingGoals())) return ''
  return homeGoalStatusPack.value.headline || ''
})

const homeStageSummaryVisible = computed(() => {
  if (!hasActiveTrainingGoals(readTrainingGoals())) return false
  return (homeGoalProgress.value.validSessionCount || 0) > 0
})

const homeStageMainLines = computed(() => homeStageSummary.value.mainProgress.slice(0, 2))
const homeStageNeedLines = computed(() => homeStageSummary.value.stillNeed.slice(0, 2))
const homeStageNextLabel = computed(() => homeStageSummary.value.nextSuggestion?.label || '')

const homeGoalAchieved = computed(
  () => homeGoalStatusPack.value.status === GOAL_STATUS.ACHIEVED
)

const homeHasTargetFocus = computed(() => {
  void goalsRevision.value
  return !!readTrainingGoals().target_focus
})

const homeGoalDisplayLines = computed(() => {
  const p = homeGoalProgress.value
  const g = p.goals
  if (!hasActiveTrainingGoals(g)) return []
  const lines = []
  if (g.target_total_score != null) {
    lines.push(`当前目标：总分达到 ${Number(g.target_total_score).toFixed(1)} 分`)
    if (p.bestTotal != null) {
      if (p.gapToTarget != null && p.gapToTarget > 0) {
        lines.push(`当前最好成绩 ${p.bestTotal.toFixed(1)} 分，还差 ${p.gapToTarget.toFixed(1)} 分`)
      } else {
        lines.push(`当前最好成绩 ${p.bestTotal.toFixed(1)} 分，已达到目标线`)
      }
    } else {
      lines.push('暂无有效训练记录，完成一轮有效训练后即可对照目标总分。')
    }
    if (p.recentAvgTotal != null) {
      lines.push(`最近有效训练平均总分约 ${p.recentAvgTotal.toFixed(1)} 分。`)
    }
  }
  if (g.target_focus) {
    const lab = TRAINING_GOAL_FOCUS_LABEL[g.target_focus] || g.target_focus
    if (p.focusBest != null) {
      lines.push(`目标专项：${lab}；该项在有效训练中最好约 ${p.focusBest.toFixed(1)} 分`)
    } else {
      lines.push(`目标专项：${lab}；尚未在有效训练中汇总到该项分数`)
    }
  }
  if (p.validCountProgress) {
    const { current, target } = p.validCountProgress
    lines.push(`已完成 ${current} / ${target} 次有效训练`)
  }
  return lines
})

const goalDialogButtonLabel = computed(() => {
  void goalsRevision.value
  return hasActiveTrainingGoals(readTrainingGoals()) ? '调整训练目标' : '设置训练目标'
})

watch(
  homeGoalProgress,
  (p) => {
    console.log('[Home.goal] progress=', {
      validSessionCount: p.validSessionCount,
      bestTotal: p.bestTotal,
      recentAvgTotal: p.recentAvgTotal,
      targetTotal: p.targetTotal,
      gapToTarget: p.gapToTarget,
      validCountProgress: p.validCountProgress,
      targetFocus: p.targetFocus,
      focusBest: p.focusBest,
    })
  },
  { deep: true, flush: 'post' }
)

watch(
  [homeGoalStatusPack, homeStageSummary],
  () => {
    if (!hasActiveTrainingGoals(readTrainingGoals())) return
    const st = homeGoalStatusPack.value.status
    console.log('[Home.goal_status] status=', st, homeGoalStatusPack.value.summaryForLog)
    console.log('[Home.goal_status] summary=', {
      mainProgress: homeStageSummary.value.mainProgress,
      stillNeed: homeStageSummary.value.stillNeed,
      next: homeStageSummary.value.nextSuggestion,
    })
  },
  { deep: true, flush: 'post' }
)

watch(
  homeRhythmStats,
  (s) => {
    if (overviewLoading.value || overviewLoadError.value) return
    console.log('[Home.streak] streak_days=', s.streak_days)
    console.log('[Home.streak] recent_valid_count=', {
      d7: s.recent_valid_count_7d,
      d14: s.recent_valid_count_14d,
    })
    console.log('[Home.streak] today_done=', s.today_done)
  },
  { flush: 'post' }
)

watch(
  homeWeeklyReview,
  (r) => {
    if (overviewLoading.value || overviewLoadError.value) return
    if (!r?.weekly_valid_count) return
    const summary = [r.stage_one_liner, r.weekly_trend_summary].filter(Boolean).join(' | ')
    console.log('[Home.weekly] summary=', summary)
    console.log('[Home.weekly] next_focus=', r.weekly_next_focus)
  },
  { flush: 'post' }
)

watch(
  homeNextPlan,
  (p) => {
    if (overviewLoading.value || overviewLoadError.value) return
    if (!p?.next_plan_action) return
    console.log('[Home.next_plan] action=', p.next_plan_action)
    console.log('[Home.next_plan] reason=', p.next_plan_reason)
  },
  { flush: 'post' }
)

function goSettingsPage() {
  router.push({ name: 'Settings' })
}

const systemStatus = ref(null)
const systemStatusLoading = ref(true)
const systemStatusError = ref('')

const systemBoardParticipationLabel = computed(() => {
  const s = systemStatus.value
  if (!s) return '—'
  if (s.board_inference_enabled) return '是（语音或视觉至少一项走开发板）'
  return '否（当前为本地链路）'
})

const systemBoardHealthLabel = computed(() => {
  const s = systemStatus.value
  if (!s) return '—'
  const r = s.ascend_health_check?.reachable
  if (r === true) return '可达'
  if (r === false) return '不可达'
  return '未探测（未配置板址）'
})

const systemHealthUserLine = computed(() => {
  const h = String(systemStatus.value?.system_health_hint || '').trim()
  if (h === 'board_url_missing') return '已启用开发板分析，但尚未配置板址，请检查环境变量。'
  if (h === 'board_unreachable') return '已启用开发板分析，但健康检查未通过，请确认开发板服务已启动。'
  return '链路检查正常，可按下方入口使用训练与复盘功能。'
})

/** 板侧 /health：优先 ascend_service_runtime，否则从 ascend_health_check.response 取同名字段 */
const ascendRuntimeSummaryLine = computed(() => {
  const s = systemStatus.value
  if (!s) return ''
  let r = s.ascend_service_runtime
  if (!r || typeof r !== 'object' || !Object.keys(r).length) {
    const resp = s.ascend_health_check?.response
    if (resp && typeof resp === 'object' && (resp.status || resp.service || resp.endpoints)) {
      r = resp
    } else {
      return ''
    }
  }
  const bits = [
    r.runtime_label ? `runtime_label=${r.runtime_label}` : '',
    r.platform_system || '',
    r.hostname ? `host=${r.hostname}` : '',
    r.temp_dir ? `temp_dir=${r.temp_dir}` : '',
  ].filter(Boolean)
  return bits.join(' · ')
})
/** 来自 /history 的列表条数，用于区分「从未训练」与「有记录但无有效训练」 */
const historyRecordCount = ref(0)

function normalizeIncomingFocusKey(k) {
  const x = String(k || '').trim().toLowerCase()
  if (x === 'language' || x === 'posture' || x === 'qa' || x === 'content') return x
  return null
}

function overviewFocusLabel(k) {
  return trainingFocusLabel(k)
}

function formatOverviewTime(ts) {
  if (ts == null || String(ts).trim() === '') return '—'
  try {
    return new Date(ts).toLocaleString()
  } catch (_) {
    return String(ts)
  }
}

function logHomeOverview(o) {
  if (!o) {
    console.log('[Home.overview] latest_valid_training=', null)
    console.log('[Home.overview] recommended_continue_focus=', null)
    return
  }
  console.log('[Home.overview] latest_valid_training=', {
    session_id: o.latest_valid_session_id ?? null,
    created_at: o.latest_valid_created_at ?? null,
    focus: o.latest_valid_training_focus ?? null,
    total_score: o.latest_valid_total_score ?? null,
    scoring_profile: o.latest_valid_scoring_profile ?? null,
    defense_material_mode: o.latest_valid_defense_material_mode ?? null,
  })
  console.log('[Home.overview] recommended_continue_focus=', o.recommended_continue_focus ?? null)
}

function logHomeAction(action) {
  console.log('[Home.action] action=', action)
}

function writeFocusHandoff(payload) {
  try {
    writeUserScopedItem(
      sessionStorage,
      TRAINING_FOCUS_HANDOFF_KEY,
      JSON.stringify({
        ...payload,
        ts: Date.now(),
      })
    )
  } catch (_) {}
}

function onConsolidateGoalFocus() {
  const prefs = readAppPreferences()
  const fk = String(readTrainingGoals().target_focus || '').trim().toLowerCase()
  if (!fk || !['language', 'posture', 'qa', 'content'].includes(fk)) {
    pageFeedback(
      'Home',
      'goal_consolidate',
      '请先在「调整训练目标」中指定目标专项，再使用巩固专项。',
      'warning'
    )
    return
  }
  writeFocusHandoff({
    recommended_focus: fk,
    scoring_profile: prefs.scoring_profile,
    defense_material_mode: prefs.defense_material_mode,
    source: 'goal_consolidate',
  })
  pageFeedback('Home', 'goal_consolidate', '已按目标专项预填训练页（不会自动开始训练）。', 'success')
  router.push({ path: '/training', query: { entry: 'home', recommended_focus: fk } })
}

const overviewReady = computed(() => {
  const o = validTrainingOverview.value
  return !!(o && o.overview_ready && (o.valid_count_recent || 0) > 0)
})

const homeEmptyMode = computed(() => {
  if (overviewLoading.value || overviewLoadError.value) return null
  if (historyRecordCount.value === 0) return 'first_time'
  if (!overviewReady.value) return 'no_valid_training'
  return 'has_valid_training'
})

const overviewNote = computed(() => {
  const o = validTrainingOverview.value
  if (!o?.overview_message) return ''
  return String(o.overview_message).trim()
})

const latestTimeLabel = computed(() => {
  if (!overviewReady.value) return '—'
  return formatOverviewTime(validTrainingOverview.value?.latest_valid_created_at)
})

const latestFocusLabel = computed(() => {
  if (!overviewReady.value) return '—'
  return overviewFocusLabel(validTrainingOverview.value?.latest_valid_training_focus)
})

const latestScoreLabel = computed(() => {
  if (!overviewReady.value) return '—'
  const v = validTrainingOverview.value?.latest_valid_total_score
  if (v == null || v === '') return '—'
  const n = Number(v)
  return Number.isFinite(n) ? n.toFixed(1) : '—'
})

const recommendFocusLabel = computed(() => {
  if (!overviewReady.value) return '—'
  return overviewFocusLabel(validTrainingOverview.value?.recommended_continue_focus)
})

const homeConsoleValidSessionsLabel = computed(() => {
  void goalsRevision.value
  if (overviewLoading.value) return '…'
  const n = homeGoalProgress.value?.validSessionCount
  if (n == null || !Number.isFinite(Number(n))) return '0'
  return String(Math.max(0, Math.floor(Number(n))))
})

const homeConsoleBestScoreLabel = computed(() => {
  void goalsRevision.value
  if (overviewLoading.value) return '…'
  const b = homeGoalProgress.value?.bestTotal
  if (b == null || !Number.isFinite(Number(b))) return '—'
  return Number(b).toFixed(1)
})

const latestSessionId = computed(() => {
  const s = String(validTrainingOverview.value?.latest_valid_session_id || '').trim()
  return s || ''
})

/** 比赛演示主按钮：有有效最近一轮则「继续」，纯新用户则「第一轮」，否则引导完整训练流程 */
const demoPrimaryKind = computed(() => {
  if (overviewLoading.value) return 'loading'
  if (homeEmptyMode.value === 'has_valid_training' && latestSessionId.value) return 'continue_latest'
  if (homeEmptyMode.value === 'first_time') return 'first_round'
  return 'full_training'
})

const canApplyRecommended = computed(() => {
  if (!overviewReady.value) return false
  const rec = validTrainingOverview.value?.recommended_continue_focus
  if (rec == null || String(rec).trim() === '') return false
  return true
})

/** 回访用户：首屏摘要卡（与概况 API 同源，不新增请求） */
const showReturnUserSummary = computed(
  () => homeEmptyMode.value === 'has_valid_training' && overviewReady.value
)

const returnSummaryDetailLine = computed(() => {
  if (!showReturnUserSummary.value) return ''
  const o = String(overviewNote.value || '').trim()
  if (o) return o
  if (homeNextPlanVisible.value) {
    const t = String(homeNextPlan.value?.next_plan_user_line || '').trim()
    if (t) return t.length > 160 ? `${t.slice(0, 160)}…` : t
  }
  return ''
})

/** 欢迎区说明：随概况加载与空状态变化 */
const homeWelcomeActionLine = computed(() => {
  if (overviewLoading.value) {
    return PAGE_LOADING.homeOverview.hint
  }
  if (overviewLoadError.value) {
    return '概况暂时无法加载，不影响开始训练；可在下方展开「训练数据、目标与设置」后重试加载。'
  }
  if (homeEmptyMode.value === 'first_time') {
    return '当前账号尚无训练记录。请先完成一轮并正常提交，概况与快捷操作将随后可用。'
  }
  if (homeEmptyMode.value === 'no_valid_training') {
    return '已有部分记录，但尚没有可纳入统计的完整训练。请再练一轮并正常提交。'
  }
  if (homeEmptyMode.value === 'has_valid_training') {
    return '可先开始新一轮，或使用「继续训练」沿用上次方式或按建议方向。'
  }
  return '可直接开始新一轮，或沿用最近一次已纳入统计的训练方式，并按建议强化专项。'
})

const resumeLastDisabledTitle = computed(() => {
  if (overviewLoading.value) return PAGE_LOADING.homeOverview.label
  if (!overviewReady.value) {
    return '完成至少一次有效训练后，可一键沿用上次的模式、材料与专项。'
  }
  return ''
})

const applyRecommendedDisabledTitle = computed(() => {
  if (overviewLoading.value) return PAGE_LOADING.homeOverview.label
  if (!canApplyRecommended.value) {
    return '有可用建议时，会在此出现；你可先开始训练，待产生可纳入统计的训练后再回来查看。'
  }
  return ''
})

function onWelcomeContinueCommand(cmd) {
  if (cmd === 'resume') onResumeLastStyle()
  else if (cmd === 'recommended') onApplyRecommended()
}

function openHomeCoreCollapseFromSummary() {
  homeCoreCollapse.value = ['core']
  try {
    setTimeout(() => {
      const el = document.querySelector('.home-core-collapse')
      el?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
    }, 200)
  } catch (_) {}
}

function openHomeDemoAuxCollapse() {
  homeAuxCollapse.value = ['aux']
  try {
    setTimeout(() => {
      const el = document.querySelector('.home-aux-collapse')
      el?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
    }, 200)
  } catch (_) {}
}

watch(
  validTrainingOverview,
  (o) => {
    logHomeOverview(o)
  },
  { flush: 'post' }
)

watch(
  homeEmptyMode,
  (m) => {
    if (m) console.log('[Home.empty] mode=', m)
  },
  { flush: 'post' }
)

watch(overviewLoading, (v) => {
  console.log('[Home.load] loading=', v)
})

watch(overviewLoadError, (msg) => {
  if (msg) console.log('[Home.load] error=', msg)
})

function onHistoryDataChanged() {
  loadHomeOverview()
}

async function loadSystemStatus() {
  systemStatusLoading.value = true
  systemStatusError.value = ''
  try {
    const s = await getJson('/system/provider-status')
    systemStatus.value = s
    const board = !!(s && s.board_inference_enabled)
    console.log('[Home.system] provider_status=', {
      speech_provider: s?.speech_provider,
      vision_provider: s?.vision_provider,
      document_parser_provider: s?.document_parser_provider,
      system_health_hint: s?.system_health_hint,
      ascend_reachable: s?.ascend_health_check?.reachable,
    })
    console.log('[Home.system] board_enabled=', board)
  } catch (e) {
    systemStatus.value = null
    systemStatusError.value = toUserFacingMessage(e, '系统状态加载失败，可稍后重试。')
    console.log('[Home.system] provider_status=', null)
    console.log('[Home.system] board_enabled=', false)
  } finally {
    systemStatusLoading.value = false
  }
}

async function loadHomeOverview() {
  overviewLoading.value = true
  overviewLoadError.value = ''
  try {
    const data = await getJson('/history')
    validTrainingOverview.value = data.valid_training_overview ?? null
    historyRecordCount.value = Array.isArray(data.history) ? data.history.length : 0
    homeHistoryList.value = Array.isArray(data.history) ? data.history : []
  } catch (e) {
    historyRecordCount.value = 0
    homeHistoryList.value = []
    validTrainingOverview.value = null
    logHomeOverview(null)
    overviewLoadError.value = toUserFacingMessage(
      e,
      '暂时无法获取训练概况。不影响开始训练，可先点「去训练」；网络正常后再点「重试」。需要对照记录时也可从顶栏进历史。'
    )
  } finally {
    overviewLoading.value = false
    try {
      const lid =
        String(validTrainingOverview.value?.latest_valid_session_id || '').trim() || null
      console.log('[Home.demo] latest_valid_session_id=', lid)
    } catch (_) {
      console.log('[Home.demo] latest_valid_session_id=', null)
    }
  }
}

function retryLoadOverview() {
  console.log('[Home.load] retry=', true)
  loadHomeOverview()
}

onMounted(async () => {
  try {
    window.addEventListener(HISTORY_DATA_CHANGED_EVENT, onHistoryDataChanged)
  } catch (_) {}
  try {
    window.addEventListener(TRAINING_GOALS_CHANGED_EVENT, bumpGoalsRevision)
  } catch (_) {}

  try {
    await hydrateAccountSettings()
  } catch (_) {
    pageFeedback(
      'Home',
      'account_settings_load',
      '暂时无法从账号加载偏好与目标，已使用本机缓存。',
      'warning'
    )
  }
  trainingGoalsUi.value = { ...readTrainingGoals() }

  activateDemoModeFromRouteQuery(route.query)

  const lid = String(route.query.last_completed_session_id || '').trim()
  const esRaw = String(route.query.entry_source || '').trim().toLowerCase()
  const entrySource = esRaw === 'result' || esRaw === 'report' ? esRaw : 'direct'
  const openSettingsRaw = String(route.query.open_settings || '').trim().toLowerCase()
  const shouldOpenSettings = openSettingsRaw === '1' || openSettingsRaw === 'true'

  console.log('[Home.return] last_completed_session_id=', lid || null)
  console.log('[Home.return] entry_source=', entrySource)

  if (lid && (esRaw === 'result' || esRaw === 'report')) {
    returnFromTrainingNoticeVisible.value = true
    homeCoreCollapse.value = ['core']
    router.replace({ path: '/', query: {} })
  } else {
    const q = stripDemoQueryKeys({ ...route.query })
    delete q.open_settings
    if (shouldOpenSettings) {
      router.replace({ name: 'Settings' })
    } else if (JSON.stringify(q) !== JSON.stringify(route.query)) {
      router.replace({ path: route.path || '/', query: q })
    }
  }

  refreshDemoModeState()

  await Promise.all([loadHomeOverview(), loadSystemStatus()])
  console.log('[Home.user_scope] user_id=', getActiveUserId() ?? '(none)')
})

onBeforeUnmount(() => {
  try {
    window.removeEventListener(HISTORY_DATA_CHANGED_EVENT, onHistoryDataChanged)
  } catch (_) {}
  try {
    window.removeEventListener(TRAINING_GOALS_CHANGED_EVENT, bumpGoalsRevision)
  } catch (_) {}
})

function onStartRegular() {
  logHomeAction('start_regular')
  try {
    removeUserScopedItem(sessionStorage, TRAINING_FOCUS_HANDOFF_KEY, undefined, true)
  } catch (_) {}
  router.push({ path: '/training', query: { entry: 'home', home_action: 'regular' } })
}

function onFirstRoundTraining() {
  logHomeAction('first_round_training')
  onStartRegular()
}

function onResumeLastStyle() {
  const o = validTrainingOverview.value
  if (!overviewReady.value) {
    pageFeedback(
      'Home',
      'resume_last_valid',
      '还没有可沿用的有效训练记录。请先在训练页完成一轮并正常出结果，之后这里就能一键对齐上次方式。',
      'warning'
    )
    return
  }
  logHomeAction('resume_last_valid')
  const sp = String(o.latest_valid_scoring_profile || 'defense').trim().toLowerCase()
  const profile = sp === 'interview' ? 'interview' : 'defense'
  const dmRaw = String(o.latest_valid_defense_material_mode || 'with_ppt').trim().toLowerCase()
  const dm = dmRaw === 'without_ppt' ? 'without_ppt' : 'with_ppt'
  const lf = String(o.latest_valid_training_focus ?? 'none').trim().toLowerCase()
  let focus = lf === 'none' || lf === '' ? null : normalizeIncomingFocusKey(lf)
  let source = 'resume_last_config'
  if (focus === 'content' && dm === 'without_ppt') {
    focus = null
    source = 'none'
  }
  writeFocusHandoff({
    recommended_focus: focus,
    scoring_profile: profile,
    defense_material_mode: dm,
    source,
  })
  try {
    removeUserScopedItem(localStorage, TRAINING_RUNTIME_SNAPSHOT_KEY, undefined, true)
  } catch (_) {}
  pageFeedback(
    'Home',
    'resume_last_valid',
    '已按最近一次有效训练对齐模式与专项，正在打开训练页（不会自动开始录音）。',
    'success'
  )
  router.push({ path: '/training', query: { entry: 'home', home_action: 'resume_last' } })
}

function onApplyRecommended() {
  const o = validTrainingOverview.value
  if (!canApplyRecommended.value) {
    pageFeedback(
      'Home',
      'apply_recommended_focus',
      '当前没有可用的建议方向，或概况数据还不足。可先完成一轮常规训练；产生可纳入统计的训练后，这里会给出更清晰建议。',
      'warning'
    )
    return
  }
  logHomeAction('apply_recommended_focus')
  const rec0 = o.recommended_continue_focus
  const sp = String(o.latest_valid_scoring_profile || 'defense').trim().toLowerCase()
  const profile = sp === 'interview' ? 'interview' : 'defense'
  const dmRaw = String(o.latest_valid_defense_material_mode || 'with_ppt').trim().toLowerCase()
  const dm = dmRaw === 'without_ppt' ? 'without_ppt' : 'with_ppt'
  const raw = String(rec0).trim().toLowerCase()
  let focus = null
  let source = 'apply_recommended_focus'
  if (raw === 'none') {
    focus = null
  } else {
    const k = normalizeIncomingFocusKey(rec0)
    if (!k) {
      pageFeedback(
        'Home',
        'apply_recommended_focus',
        '当前建议方向暂时无法识别，可先使用「开始常规训练」自行选择专项。',
        'warning'
      )
      return
    }
    focus = k
    if (k === 'content' && dm === 'without_ppt') {
      focus = null
      source = 'none'
    }
  }
  writeFocusHandoff({
    recommended_focus: focus,
    scoring_profile: profile,
    defense_material_mode: dm,
    source,
  })
  try {
    removeUserScopedItem(localStorage, TRAINING_RUNTIME_SNAPSHOT_KEY, undefined, true)
  } catch (_) {}
  pageFeedback(
    'Home',
    'apply_recommended_focus',
    '已按系统建议带好专项方向，正在打开训练页（不会自动开始录音）。',
    'success'
  )
  router.push({ path: '/training', query: { entry: 'home', home_action: 'apply_recommended' } })
}

function onViewLatestResult() {
  const sid = latestSessionId.value
  if (!sid) {
    pageFeedback(
      'Home',
      'view_latest_result',
      '暂时没有可打开的「最近一次有效训练」结果。请先完成一轮有效训练，或到历史页查看其它记录。',
      'warning'
    )
    return
  }
  logHomeAction('view_latest_result')
  pageFeedback('Home', 'view_latest_result', '正在打开最近一次有效训练的结果页。', 'success')
  router.push({ path: '/result', query: { session_id: sid } })
}

function onViewLatestReport() {
  const sid = latestSessionId.value
  if (!sid) {
    pageFeedback(
      'Home',
      'view_latest_report',
      '暂时没有可打开的「最近一次有效训练」报告。请先完成一轮有效训练，或从结果页进入报告。',
      'warning'
    )
    return
  }
  logHomeAction('view_latest_report')
  pageFeedback('Home', 'view_latest_report', '正在打开最近一次有效训练的报告页（可打印留档）。', 'success')
  router.push({ path: '/report', query: { session_id: sid } })
}

function onViewHistory() {
  logHomeAction('view_history')
  pageFeedback('Home', 'view_history', '正在打开历史页。', 'info')
  router.push('/history')
}

function onDemoContinueLatest() {
  engageDemoModeForHomeEntry()
  console.log('[Home.demo] entry_action=', 'continue_latest_round')
  onViewLatestResult()
}

function onDemoStartFirstRound() {
  engageDemoModeForHomeEntry()
  console.log('[Home.demo] entry_action=', 'start_first_round_demo')
  onFirstRoundTraining()
}

function onDemoFullTraining() {
  engageDemoModeForHomeEntry()
  console.log('[Home.demo] entry_action=', 'start_full_training_demo')
  onStartRegular()
}

function onDemoQuickFullTraining() {
  engageDemoModeForHomeEntry()
  console.log('[Home.demo] entry_action=', 'quick_full_training_demo')
  onStartRegular()
}

function onDemoQuickViewLatestResult() {
  engageDemoModeForHomeEntry()
  console.log('[Home.demo] entry_action=', 'view_latest_result')
  onViewLatestResult()
}

function onDemoQuickViewLatestReport() {
  engageDemoModeForHomeEntry()
  console.log('[Home.demo] entry_action=', 'view_latest_report')
  onViewLatestReport()
}

function onDemoQuickViewHistory() {
  engageDemoModeForHomeEntry()
  console.log('[Home.demo] entry_action=', 'view_history')
  onViewHistory()
}
</script>

<style scoped>
.home-page {
  width: 100%;
  margin: 0 auto;
  padding: 0;
  text-align: left;
  box-sizing: border-box;
}

.home-page--brand-v1 {
  max-width: none;
}

.home-welcome-eyebrow {
  margin: 0 0 10px;
}

.home-main-header {
  margin-bottom: 4px;
}

.home-main-header__title {
  margin: 0 0 6px;
}

.home-main-header__sub {
  margin: 0;
}

.home-tier-core--brand .ui-surface {
  border-color: var(--ui-border);
}

.home-tier-core--brand .home-section-title {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.015em;
  color: var(--ui-text-primary);
}

.home-tier-welcome--v2 {
  margin-bottom: 14px;
  padding: 18px 20px 20px;
}

.home-console-mid {
  margin-bottom: 16px;
  padding: 12px 14px 14px;
  border-radius: var(--ui-radius-lg);
  border: 1px solid var(--ui-border);
  background: var(--ui-surface);
  box-shadow: var(--ui-shadow-card);
}

.home-metric-deck {
  list-style: none;
  margin: 0 0 12px;
  padding: 0;
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

@media (min-width: 640px) {
  .home-metric-deck {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (min-width: 1280px) {
  .home-metric-deck {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }
}

.home-metric-deck__cell {
  padding: 10px 12px;
  border-radius: var(--ui-radius-md);
  border: 1px solid var(--ui-border);
  background: var(--ui-surface-subtle);
  min-width: 0;
}

.home-metric-deck__cell--accent {
  border-color: var(--ui-accent-muted);
  background: linear-gradient(180deg, var(--ui-accent-soft) 0%, var(--ui-surface-subtle) 100%);
  box-shadow: 0 1px 0 rgba(29, 78, 216, 0.06);
}

.home-metric-deck__k {
  display: block;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ui-text-muted);
  margin-bottom: 4px;
}

.home-metric-deck__v {
  display: block;
  font-size: 24px;
  font-weight: 800;
  color: var(--ui-text-primary);
  line-height: 1.25;
  word-break: break-word;
}

.home-metric-deck__unit {
  font-size: 0.75rem;
  margin-left: 2px;
}

.home-metric-deck__v--time {
  font-size: 15px;
  font-weight: 700;
}

.home-console-quicklinks {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 14px;
  padding-top: 10px;
  border-top: 1px dashed var(--ui-border);
}

.home-console-quicklinks__label {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.home-console-quicklinks__a {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--ui-accent);
  text-decoration: none;
}

.home-console-quicklinks__a:hover {
  text-decoration: underline;
  color: var(--ui-accent-hover);
}

.home-console-quicklinks__btn {
  margin-left: auto;
}

@media (max-width: 560px) {
  .home-console-quicklinks__btn {
    margin-left: 0;
  }
}

.home-cta-main--xl {
  min-width: 148px;
  padding-left: 28px;
  padding-right: 28px;
  font-size: 1.05rem;
}

.home-cta-block--hero {
  margin-bottom: 6px;
}

.home-cta-block-hint--tight {
  max-width: 42ch;
  font-size: 0.8rem;
}

.home-cta-row--hero {
  margin-top: 4px;
}

.home-welcome-action-line--compact {
  max-width: 56ch;
  margin-bottom: 12px;
}

.home-welcome-aux-row {
  margin-top: 8px;
}

.home-hero-2col {
  align-items: stretch;
}

.home-hero-2col__left,
.home-hero-2col__right {
  min-width: 0;
}

.home-hero-2col__right {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.home-hero-2col__quick-k {
  margin: 4px 0 0;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: #94a3b8;
}

.home-hero-2col__stub {
  padding: 16px 18px;
  border-radius: var(--ui-radius-md, 10px);
}

.home-hero-2col__stub-title {
  margin: 0 0 8px;
  font-size: 1.02rem;
  font-weight: 700;
  color: #0f172a;
}

.home-hero-2col__stub-lead {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.55;
}

.home-primary-cta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 14px;
  align-items: center;
}

.home-cta-main {
  min-width: 132px;
  font-weight: 600;
}

.home-tier-welcome-foot {
  margin: 12px 0 0;
  font-size: 0.82rem;
  line-height: 1.55;
  color: #64748b;
}

.home-overview--v1 {
  padding: 18px 20px !important;
  margin-bottom: 0 !important;
}

.home-panel-pad {
  padding: 18px 20px !important;
}

.home-tier-core .home-training-goals,
.home-tier-core .home-training-rhythm,
.home-tier-core .home-weekly-summary,
.home-tier-core .home-next-plan {
  margin-bottom: 0 !important;
}

.home-aux-collapse {
  margin: 16px 0 24px;
}

.home-core-collapse {
  margin: 0 0 8px;
}

.home-welcome-hero-title {
  margin: 0 0 10px;
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.2;
  color: #0f172a;
}

.home-cta-sub-label {
  margin: 20px 0 8px;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: #94a3b8;
  text-transform: none;
}

.home-welcome-aux-link {
  margin: 10px 0 0;
}

.home-dropdown-caret {
  display: inline-block;
  margin-left: 4px;
  font-size: 0.7em;
  opacity: 0.75;
  vertical-align: middle;
}

.home-personal-dashboard {
  margin-bottom: 24px;
  padding: 18px 20px;
  border-radius: 12px;
  background: linear-gradient(135deg, #fff 0%, #f0f9ff 100%);
  border: 1px solid #bae6fd;
}

.home-welcome-line {
  margin: 0 0 10px;
  font-size: 0.95rem;
  line-height: 1.6;
  color: #0f172a;
}

.home-welcome-action-line {
  margin: 0 0 16px;
  font-size: 0.9rem;
  line-height: 1.6;
  color: #334155;
  max-width: 52ch;
}

.home-cta-tier-k {
  margin: 18px 0 8px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #94a3b8;
}

.home-cta-tier-k--top {
  margin-top: 6px;
}

.home-cta-block--primary {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 2px;
}

.home-cta-block-hint {
  margin: 0;
  max-width: 40rem;
  font-size: 0.84rem;
  line-height: 1.5;
}

.home-cta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 12px;
  align-items: center;
}

.home-cta-row--secondary .el-button {
  min-width: 0;
}

/* 与「主 CTA/开始训练」区协同：在仍偏窄的视口上提前纵排，避免 769–900 挤一行 */
@media (max-width: 900px) {
  .home-cta-row--secondary {
    flex-direction: column;
    align-items: stretch;
  }

  .home-cta-row--secondary .el-button,
  .home-cta-row--secondary :deep(.el-dropdown) {
    width: 100%;
  }

  .home-cta-link-profile {
    display: block;
    width: 100%;
    text-align: center;
    padding: 10px 12px;
  }
}

.home-first-screen-summary {
  margin: 12px 0 16px;
  padding: 14px 16px;
  border-radius: var(--ui-radius-md, 8px);
  max-width: 42rem;
  border: 1px solid var(--ui-border, #e2e8f0);
}

.home-first-screen-summary__title {
  margin: 0 0 10px;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #64748b;
}

.home-first-screen-summary__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 18px;
  list-style: none;
  margin: 0 0 10px;
  padding: 0;
}

.home-first-screen-summary__k {
  display: block;
  font-size: 0.72rem;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 2px;
}

.home-first-screen-summary__v {
  font-size: 0.95rem;
  color: #0f172a;
  line-height: 1.3;
  word-break: break-word;
}

.home-first-screen-summary__line {
  margin: 0 0 8px;
  font-size: 0.86rem;
  line-height: 1.5;
}

.home-first-screen-summary__more {
  margin: 0;
}

.home-first-screen-summary--spotlight {
  margin: 0;
  max-width: none;
  padding: 16px 18px;
  border: 1px solid var(--ui-accent-muted);
  background: linear-gradient(165deg, var(--ui-accent-soft) 0%, var(--ui-surface) 58%);
  box-shadow: var(--ui-shadow-card);
}

.home-first-screen-summary__eyebrow {
  margin: 0 0 4px;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ui-accent);
}

.home-first-screen-summary--spotlight .home-first-screen-summary__title {
  margin: 0 0 12px;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.02em;
  text-transform: none;
  color: var(--ui-text-primary);
}

.home-first-screen-summary__v--score {
  font-size: 26px;
  font-weight: 900;
  color: var(--ui-accent);
}

.home-first-screen-summary__li--rec .home-first-screen-summary__v {
  font-weight: 800;
  color: #1e40af;
}

.home-hero-2col__stub--compact {
  padding: 14px 16px;
}

.home-hero-2col__stub-eyebrow {
  margin: 0 0 6px;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ui-text-muted);
}

@media (max-width: 560px) {
  .home-first-screen-summary__grid {
    grid-template-columns: 1fr;
  }
}

.home-cta-link-profile {
  align-self: center;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--el-color-primary);
  text-decoration: none;
  padding: 8px 6px;
  border-radius: var(--ui-radius-sm, 6px);
}

.home-cta-link-profile:hover {
  text-decoration: underline;
  color: var(--el-color-primary-light-3);
}

.home-cta-aux-hint {
  margin: 6px 0 0;
  max-width: 40rem;
  font-size: 0.84rem;
  line-height: 1.5;
}

.home-spotlight-strip {
  margin: 0 0 20px;
  max-width: 800px;
  padding: 14px 18px 16px;
  border: 1px solid #c7d2fe;
  border-radius: 12px;
  background: linear-gradient(120deg, #f8fafc 0%, #f1f5f9 100%);
}

.home-spotlight-strip__title {
  margin: 0 0 6px;
  font-size: 0.9rem;
  font-weight: 700;
  color: #0f172a;
}

.home-spotlight-strip__line {
  margin: 0 0 8px;
  font-size: 0.86rem;
  line-height: 1.55;
}

.home-quick-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.home-hero {
  margin-bottom: 32px;
}

.home-competition-tag {
  margin: 12px 0 0;
  font-size: 0.86rem;
  line-height: 1.55;
}

.home-hero-eyebrow {
  margin: 0 0 10px;
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #64748b;
}

.home-demo-entry.ui-surface {
  margin-bottom: 28px;
  padding: 18px 18px 20px;
  background: linear-gradient(165deg, var(--ui-accent-soft) 0%, var(--ui-surface-subtle) 45%, var(--ui-surface) 100%);
  border-color: var(--brand-border-accent-soft);
}

.home-demo-lead {
  margin: 0 0 12px;
  font-size: 0.9rem;
  line-height: 1.55;
}

.home-demo-steps {
  margin: 0 0 18px;
  padding-left: 1.25rem;
  font-size: 0.88rem;
  line-height: 1.65;
  color: #334155;
}

.home-demo-steps li {
  margin-bottom: 6px;
}

.home-demo-primary {
  margin-bottom: 20px;
}

.home-demo-primary-btn {
  font-weight: 600;
}

.home-demo-primary-hint,
.home-demo-primary-wait {
  margin: 10px 0 0;
  font-size: 0.86rem;
  line-height: 1.5;
}

.home-demo-quick-label {
  margin: 0 0 8px;
  font-size: 0.78rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.home-demo-quick-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

@media (min-width: 520px) {
  .home-demo-quick-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
}

.home-demo-quick-foot {
  margin: 12px 0 0;
  font-size: 0.8rem;
  line-height: 1.5;
}

.home-system-overview.ui-surface--subtle,
.home-capabilities.ui-surface--subtle {
  margin-bottom: 28px;
  padding: 16px 18px;
}

.home-system-loading {
  margin: 0;
  font-size: 0.9rem;
}

.home-system-error__body {
  margin: 0 0 10px;
  font-size: 0.88rem;
  line-height: 1.5;
}

.home-system-error__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.home-system-grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px 16px;
  grid-template-columns: 1fr 1fr;
}

@media (max-width: 560px) {
  .home-system-grid {
    grid-template-columns: 1fr;
  }
}

.home-system-grid__full {
  grid-column: 1 / -1;
}

.home-sys-k {
  display: block;
  font-size: 0.78rem;
  color: #909399;
  margin-bottom: 2px;
}

.home-sys-v {
  font-size: 0.95rem;
  font-weight: 600;
  color: #303133;
}

.home-sys-desc {
  display: block;
  font-size: 0.88rem;
  line-height: 1.5;
  color: #606266;
}

.home-sys-desc--code {
  font-family: ui-monospace, 'Consolas', monospace;
  font-size: 0.8rem;
  word-break: break-all;
}

.home-capabilities-list {
  margin: 0;
  padding-left: 1.15rem;
  font-size: 0.9rem;
  line-height: 1.65;
  color: #334155;
}

.home-capabilities-list li {
  margin-bottom: 8px;
}

.home-capabilities-foot {
  margin: 12px 0 0;
  font-size: 0.82rem;
}

.home-onboarding {
  padding: 4px 0 8px;
}

.home-onboarding-lead {
  margin: 0 0 14px;
  font-size: 0.95rem;
  line-height: 1.65;
  color: #334155;
}

.home-onboarding-list {
  margin: 0 0 18px;
  padding-left: 1.2rem;
  font-size: 0.9rem;
  line-height: 1.65;
  color: #475569;
}

.home-onboarding-list li {
  margin-bottom: 10px;
}

.home-onboarding-cta {
  font-weight: 600;
}

.home-onboarding-cta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 12px;
  align-items: center;
  margin-top: 4px;
}

.home-onboarding-foot {
  margin: 12px 0 0;
  font-size: 0.8rem;
  line-height: 1.5;
}

.home-no-valid-card {
  padding: 16px 18px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fafbfc;
}

.home-no-valid-title {
  margin: 0 0 8px;
  font-size: 1.08rem;
  font-weight: 600;
  color: #0f172a;
}

.home-no-valid-lead {
  margin: 0 0 8px;
  font-size: 0.9rem;
  line-height: 1.5;
}

.home-no-valid-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 12px;
  margin-top: 14px;
  align-items: center;
}

.home-no-valid-cta {
  margin-top: 0;
}

.home-return-alert {
  margin-bottom: 20px;
}

.home-return-alert__body {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.5;
}

.home-title {
  margin: 0 0 12px;
  font-size: 2rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.02em;
}

.home-lead {
  margin: 0;
  font-size: 1.05rem;
  line-height: 1.6;
  color: #475569;
}

.home-lead--compact {
  font-size: 1rem;
}

.home-section-title {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 700;
  color: var(--ui-text-primary);
  letter-spacing: -0.015em;
}

.home-section-sub {
  margin: 0 0 16px;
  font-size: 15px;
  line-height: 1.5;
}

.home-sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.home-overview {
  margin-bottom: 28px;
}

.home-overview-state {
  margin: 8px 0 0;
  font-size: 0.92rem;
}

.home-overview-state--warn {
  color: #b45309;
}

.home-overview-loading {
  padding: 8px 0 4px;
}

.home-overview-loading-label {
  margin: 0 0 6px;
  font-size: 0.9rem;
}

.home-overview-loading-hint {
  margin: 0 0 12px;
  font-size: 0.82rem;
  line-height: 1.45;
}

.home-overview-error__body {
  margin: 0 0 10px;
  font-size: 0.9rem;
  line-height: 1.55;
}

.home-overview-error__next {
  margin: 0 0 10px;
  font-size: 0.82rem;
  line-height: 1.5;
}

.home-overview-error__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.home-overview-grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 12px 16px;
}

@media (min-width: 520px) {
  .home-overview-grid {
    grid-template-columns: 1fr 1fr;
  }
}

.home-overview-grid li {
  margin: 0;
  padding: 12px 14px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  box-shadow: var(--ui-shadow-card);
}

.home-ok {
  display: block;
  font-size: 0.78rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 6px;
}

.home-ov-value {
  display: block;
  font-size: 1rem;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.4;
}

.home-overview-empty {
  padding: 8px 0;
}

.home-empty-lead {
  margin: 0 0 8px;
  font-size: 1.05rem;
  font-weight: 600;
  color: #334155;
}

.home-overview-note {
  margin: 14px 0 0;
  font-size: 0.86rem;
  line-height: 1.5;
}

.home-actions {
  padding: 4px 0;
}

.home-action-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

@media (min-width: 520px) {
  .home-action-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
}

.home-action-primary {
  font-weight: 600;
}

.home-action-footnote {
  margin: 16px 0 0;
  font-size: 0.82rem;
  line-height: 1.5;
}

.home-demo-mode-banner {
  margin-bottom: 16px;
}

.home-demo-mode-banner--compact {
  margin-bottom: 12px;
}

.home-demo-mode-banner--compact :deep(.el-alert__title) {
  font-size: 18px;
}

.home-demo-mode-banner--compact :deep(.el-alert__content) {
  padding-top: 4px;
}

.home-demo-mode-banner__body {
  margin: 0 0 10px;
  font-size: 15px;
  line-height: 1.5;
}

.home-demo-mode-banner__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.home-demo-mode-enter {
  margin: 0 0 12px;
  font-size: 0.86rem;
}

.home-demo-mode-enter__hint {
  margin-left: 6px;
}

.home-page--demo-mode .home-competition-tag,
.home-page--demo-mode .home-lead {
  opacity: 0.82;
}

.home-demo-entry--spotlight {
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.35), 0 10px 32px rgba(64, 158, 255, 0.12);
}

.home-system-overview--spotlight {
  border-color: #95de64 !important;
  background: linear-gradient(180deg, #f6ffed 0%, #fafbfc 100%) !important;
}

.home-capabilities--spotlight {
  border-color: #91caff !important;
}

.home-when-demo-soft {
  opacity: 0.72;
}

.home-settings-migrate {
  margin: 20px 0 8px;
  font-size: var(--font-base, 17px);
  line-height: 1.6;
}

.home-training-goals {
  margin-bottom: 28px;
  padding: 18px 18px 20px;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: linear-gradient(165deg, #f0f9ff 0%, #fafbfc 55%, #fff 100%);
}

.home-goal-loading {
  margin: 8px 0;
  font-size: 0.9rem;
}

.home-goal-lines {
  margin: 0 0 14px;
  padding-left: 1.2rem;
  font-size: 0.92rem;
  line-height: 1.65;
  color: #334155;
}

.home-goal-lines li {
  margin-bottom: 6px;
}

.home-goal-empty {
  margin: 0 0 12px;
  font-size: 0.88rem;
  line-height: 1.55;
}

.home-goal-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.home-goal-status-banner {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 12px;
  margin: 12px 0 10px;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
}

.home-goal-status-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: #2563eb;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.home-goal-status-text {
  font-size: 0.95rem;
  color: #0f172a;
}

.home-goal-stage {
  margin: 0 0 14px;
  padding: 12px 12px 10px;
  background: rgba(255, 255, 255, 0.75);
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.home-goal-stage-title {
  margin: 0 0 8px;
  font-size: 0.88rem;
  font-weight: 600;
  color: #334155;
}

.home-goal-stage-k {
  margin: 8px 0 4px;
  font-size: 0.8rem;
}

.home-goal-stage-list {
  margin: 0 0 6px;
  padding-left: 1.1rem;
  font-size: 0.86rem;
  line-height: 1.55;
}

.home-goal-stage-list li {
  margin-bottom: 4px;
}

.home-goal-stage-next {
  margin: 10px 0 0;
  font-size: 0.86rem;
  line-height: 1.5;
}

.home-goal-achieved-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

.home-training-rhythm {
  margin-bottom: 28px;
  padding: 18px 18px 20px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fafafa;
}

.home-rhythm-loading,
.home-rhythm-empty {
  margin: 8px 0;
  font-size: 0.9rem;
}

.home-rhythm-lines {
  margin: 0;
  padding-left: 1.2rem;
  font-size: 0.92rem;
  line-height: 1.65;
  color: #334155;
}

.home-rhythm-lines li {
  margin-bottom: 6px;
}

.home-weekly-summary {
  margin-bottom: 28px;
  padding: 18px 18px 20px;
  border: 1px solid #c7d2fe;
  border-radius: 12px;
  background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
}

.home-weekly-lines {
  margin: 8px 0 0;
  padding-left: 1.2rem;
  font-size: 0.92rem;
  line-height: 1.65;
  color: #1e293b;
}

.home-weekly-lines li {
  margin-bottom: 8px;
}

.home-next-plan {
  margin-bottom: 28px;
  padding: 18px 18px 20px;
  border: 1px solid #bbf7d0;
  border-radius: 12px;
  background: #f0fdf4;
}

.home-next-plan-card {
  margin-top: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid #86efac;
}

.home-next-plan-kind {
  margin: 0 0 8px;
  font-size: 0.9rem;
  color: #14532d;
}

.home-next-plan-body {
  margin: 0 0 8px;
  font-size: 0.95rem;
  line-height: 1.65;
  color: #166534;
}

.home-next-plan-focus {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.5;
}

.home-goal-dialog-lead {
  margin: 0 0 16px;
  font-size: 0.86rem;
  line-height: 1.55;
}

.home-goal-form-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 16px;
  margin-bottom: 14px;
}

.home-goal-form-k {
  min-width: 9em;
  font-size: 0.88rem;
  font-weight: 600;
  color: #475569;
}

.home-goal-form-v {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}

.home-goal-num {
  width: 160px;
}

.home-goal-select {
  min-width: 200px;
}

.home-goal-dialog-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-top: 18px;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
}

@media (max-width: 768px) {
  .home-tier-welcome--v2 {
    padding: 16px 14px;
  }

  .home-primary-cta-row {
    flex-direction: column;
    align-items: stretch;
  }

  .home-primary-cta-row .el-button {
    width: 100%;
    margin: 0;
  }

  .home-demo-primary-btn {
    width: 100%;
  }

  .home-demo-quick-grid .el-button {
    width: 100%;
  }

  .home-cta-row {
    flex-direction: column;
    align-items: stretch;
  }

  .home-cta-row .el-button {
    width: 100%;
    margin: 0;
  }

  .home-onboarding-cta-row {
    flex-direction: column;
  }

  .home-onboarding-cta,
  .home-no-valid-cta,
  .home-onboarding-cta-row .el-button,
  .home-no-valid-actions .el-button {
    width: 100%;
  }

  .home-goal-select,
  .home-goal-num {
    width: 100%;
    max-width: 100%;
    min-width: 0;
  }

  .ui-dashboard-spine {
    padding-left: 10px;
    border-left-width: 2px;
  }
}

@media (max-width: 560px) {
  .home-overview-grid {
    grid-template-columns: 1fr;
  }

  .home-demo-steps {
    font-size: 0.85rem;
  }
}

@media print {
  .no-print {
    display: none !important;
  }
}
</style>
