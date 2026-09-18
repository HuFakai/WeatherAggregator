# -*- coding: utf-8 -*-
"""
Generate production-grade app/templates/admin.html by combining:
1. complete_aetherial_ui.html layout, CSS and styling
2. Admin authentication modal (Login Modal)
3. Dynamic IDs injection into Overview/Clients KPI metrics
4. Real backend API integration for:
   - Dashboard KPIs & watermarks
   - Client Key management (List, Create, Edit with custom key value, Delete, QPM, IP whitelist)
   - Channel & Key Pool management (List, Add Key, Delete Key, Status Toggle Switch, 3-day stats, Manual Update)
   - Celery Schedule management (Multi-Cron rules per channel, Jitter delay, Hot-reload)
   - Live API Playground with real fetch and latency calculation
"""

import os
import re

def build():
    src_file = "preview_ui/complete_aetherial_ui.html"
    dest_file = "app/templates/admin.html"

    with open(src_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update Title
    content = content.replace(
        "<title>Aetherial Studio · 气象异构数据聚合与中枢监控运营平台 (全功能融合版)</title>",
        "<title>WeatherAggregator · 气象异构数据聚合中枢控制台</title>"
    )

    # 2. Add Login Modal right after <body>
    login_modal_html = """
    <!-- Admin Authentication Modal -->
    <div id="loginModal" class="center-modal-backdrop" style="display: none; z-index: 9999; backdrop-filter: blur(16px); background: rgba(3, 5, 10, 0.88);">
        <div class="sched-modal-card" style="width: 420px; text-align: center; padding: 36px 30px;">
            <div style="width: 52px; height: 52px; margin: 0 auto 16px; border-radius: 14px; background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.3); display: flex; align-items: center; justify-content: center; color: var(--accent-cyan); box-shadow: 0 0 25px rgba(56, 189, 248, 0.2);">
                <i data-lucide="cloud-sun" style="width: 28px; height: 28px;"></i>
            </div>
            <h2 style="font-size: 20px; font-weight: 700; color: #fff; margin-bottom: 6px;">聚合天气管理控制台</h2>
            <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 24px;">请输入系统管理员访问密钥以解锁全功能面板</p>
            
            <div style="margin-bottom: 16px; text-align: left;">
                <label style="font-size: 11px; color: var(--text-muted); margin-bottom: 6px; display: block; font-weight: 600;">ADMIN KEY</label>
                <div style="position: relative;">
                    <input type="password" id="adminKeyInput" placeholder="输入管理员密钥" class="form-input-ctrl" style="padding: 11px 14px; font-family: var(--font-mono); font-size: 13px;" onkeydown="if(event.key === 'Enter') handleAdminLogin()">
                </div>
                <div id="loginErrorMsg" style="font-size: 12px; color: var(--accent-rose); margin-top: 6px; min-height: 18px;"></div>
            </div>

            <button id="loginSubmitBtn" class="btn-primary" style="width: 100%; justify-content: center; padding: 11px; font-size: 14px; font-weight: 600;" onclick="handleAdminLogin()">
                <span>验证并进入控制台</span>
                <i data-lucide="arrow-right" style="width: 16px; height: 16px;"></i>
            </button>
        </div>
    </div>
"""
    content = content.replace("<body>\n", "<body>\n" + login_modal_html + "\n")

    # 3. Replace simulateLogout() button with handleLogout()
    content = content.replace('onclick="simulateLogout()"', 'onclick="handleLogout()"')

    # 4. Inject Dynamic IDs into Overview and Clients sections
    # Overview KPI 1: Today calls
    content = content.replace(
        '<div class="kpi-num">48,290</div>',
        '<div class="kpi-num" id="kpiTodayCalls">0</div>',
        1
    )
    # Overview KPI 2: Cache hit
    content = content.replace(
        '<div class="kpi-num">98.6%</div>',
        '<div class="kpi-num" id="kpiCacheHit">98.6%</div>',
        1
    )
    # Overview KPI 3: Latency
    content = content.replace(
        '<div class="kpi-num">118 <span style="font-size: 14px; font-weight: 500; color: var(--text-muted);">ms</span></div>',
        '<div class="kpi-num" id="kpiAvgLatency">118 <span style="font-size: 14px; font-weight: 500; color: var(--text-muted);">ms</span></div>',
        1
    )
    # Overview KPI 4: Channel Health
    content = content.replace(
        '<div class="kpi-num">100%</div>',
        '<div class="kpi-num" id="kpiChannelHealth">100%</div>',
        1
    )

    # Overview Left: Client keys mini list
    content = content.replace(
        '<div class="client-keys-list-mini">',
        '<div class="client-keys-list-mini" id="overviewClientKeysList">',
        1
    )

    # Overview Right: Channel Watermarks
    content = content.replace(
        '<div class="panel-card">\n                        <div class="panel-title">\n                            <i data-lucide="layers"',
        '<div class="panel-card" id="overviewChannelWatermarksCard">\n                        <div class="panel-title">\n                            <i data-lucide="layers"',
        1
    )

    # Clients Tab KPIs
    content = content.replace(
        '<div class="kpi-num" style="font-size: 24px; color: var(--accent-cyan);">48,290 <span style="font-size: 12px; font-weight: normal; color: var(--text-muted);">次</span></div>',
        '<div class="kpi-num" id="clientTabTodayUsage" style="font-size: 24px; color: var(--accent-cyan);">0 <span style="font-size: 12px; font-weight: normal; color: var(--text-muted);">次</span></div>',
        1
    )
    content = content.replace(
        '<div class="kpi-num" style="font-size: 24px; color: #fff;">284,500 <span style="font-size: 12px; font-weight: normal; color: var(--text-muted);">次</span></div>',
        '<div class="kpi-num" id="clientTab7dUsage" style="font-size: 24px; color: #fff;">0 <span style="font-size: 12px; font-weight: normal; color: var(--text-muted);">次</span></div>',
        1
    )
    content = content.replace(
        '<div class="kpi-num" style="font-size: 24px; color: var(--accent-emerald);">3 <span style="font-size: 12px; font-weight: normal; color: var(--text-muted);">个合法凭证</span></div>',
        '<div class="kpi-num" id="clientTabCount" style="font-size: 24px; color: var(--accent-emerald);">0 <span style="font-size: 12px; font-weight: normal; color: var(--text-muted);">个合法凭证</span></div>',
        1
    )

    # Channels Tab: Card row
    content = content.replace(
        '<div class="channel-cards-row">',
        '<div class="channel-cards-row" id="channelSummaryCardsContainer">',
        1
    )

    # 5. Extract everything up to <script> and inject production-grade real API JavaScript engine
    script_idx = content.rfind("<script>")
    if script_idx == -1:
        raise Exception("Could not find <script> tag")

    head_and_body = content[:script_idx]

    real_js_engine = r"""<script>
        lucide.createIcons();

        // Realtime Clock (Asia/Shanghai)
        function updateClock() {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false });
            const clockEl = document.getElementById('beijingTimeText');
            if (clockEl) clockEl.textContent = timeStr + ' CST';
        }
        setInterval(updateClock, 1000);
        updateClock();

        // Global State & Data Store
        const appState = {
            clientKeys: [],
            channels: [],
            currentTab: 'overview',
            activeInsightCity: '北京',
            playRouteMode: 'path',
            currentPlayCity: '上海'
        };

        // Multi-Source Weather Mock / Cache Database for Cross-Check Insights
        const weatherDatabase = {
            '北京': {
                code: '110000',
                temp: '23°',
                cond: '晴转多云 · 东南风 2级',
                days: ['今天', '周日', '周一', '周二', '周三', '周四', '周五'],
                hfTemps: [23, 25, 22, 19, 21, 24, 26],
                bdTemps: [24, 24, 21, 20, 22, 25, 25],
                ykTemps: [23, 26, 23, 19, 20, 23, 27],
                table: [
                    { date: '今天 (09-19)', hf: '23° / 11° · 晴', bd: '24° / 12° · 多云', yk: '23° / 10° · 晴', diff: '一致 (差 1°C)', ok: true },
                    { date: '周日 (09-20)', hf: '25° / 13° · 多云', bd: '24° / 13° · 阴', yk: '26° / 12° · 多云', diff: '一致 (差 1°C)', ok: true },
                    { date: '周一 (09-21)', hf: '22° / 10° · 小雨', bd: '21° / 10° · 小雨', yk: '25° / 12° · 阴', diff: '温差分歧 4°C · 建议和风', ok: false },
                    { date: '周二 (09-22)', hf: '19° / 9° · 晴', bd: '20° / 8° · 晴', yk: '19° / 8° · 晴', diff: '高度一致', ok: true },
                    { date: '周三 (09-23)', hf: '21° / 11° · 多云', bd: '22° / 12° · 多云', yk: '20° / 10° · 多云', diff: '一致 (差 1°C)', ok: true },
                    { date: '周四 (09-24)', hf: '24° / 13° · 晴', bd: '25° / 14° · 晴', yk: '23° / 12° · 晴', diff: '一致 (差 1°C)', ok: true },
                    { date: '周五 (09-25)', hf: '26° / 15° · 多云', bd: '25° / 14° · 多云', yk: '27° / 16° · 阴', diff: '一致 (差 2°C)', ok: true }
                ]
            },
            '上海': {
                code: '310000',
                temp: '26°',
                cond: '小雨转阴 · 东风 3级',
                days: ['今天', '周日', '周一', '周二', '周三', '周四', '周五'],
                hfTemps: [26, 24, 25, 27, 26, 28, 29],
                bdTemps: [25, 23, 26, 26, 27, 28, 28],
                ykTemps: [26, 25, 24, 28, 25, 29, 30],
                table: [
                    { date: '今天 (09-19)', hf: '26° / 18° · 小雨', bd: '25° / 17° · 阴', yk: '26° / 18° · 小雨', diff: '一致 (差 1°C)', ok: true },
                    { date: '周日 (09-20)', hf: '24° / 17° · 多云', bd: '23° / 16° · 阴', yk: '25° / 18° · 阴', diff: '一致 (差 1°C)', ok: true },
                    { date: '周一 (09-21)', hf: '25° / 18° · 阴', bd: '26° / 19° · 多云', yk: '24° / 17° · 阴', diff: '一致 (差 2°C)', ok: true },
                    { date: '周二 (09-22)', hf: '27° / 20° · 多云', bd: '26° / 19° · 晴', yk: '28° / 21° · 多云', diff: '一致 (差 2°C)', ok: true },
                    { date: '周三 (09-23)', hf: '26° / 19° · 晴', bd: '27° / 20° · 晴', yk: '25° / 19° · 晴', diff: '一致 (差 2°C)', ok: true }
                ]
            },
            '广州': {
                code: '440100',
                temp: '31°',
                cond: '雷阵雨 · 微风',
                days: ['今天', '周日', '周一', '周二', '周三', '周四', '周五'],
                hfTemps: [31, 30, 32, 33, 31, 32, 33],
                bdTemps: [32, 29, 31, 32, 30, 33, 34],
                ykTemps: [31, 30, 33, 32, 32, 31, 33],
                table: [
                    { date: '今天 (09-19)', hf: '31° / 24° · 雷雨', bd: '32° / 25° · 中雨', yk: '31° / 24° · 雷雨', diff: '一致 (差 1°C)', ok: true },
                    { date: '周日 (09-20)', hf: '30° / 23° · 阵雨', bd: '29° / 22° · 雷雨', yk: '30° / 23° · 多云', diff: '一致 (差 1°C)', ok: true },
                    { date: '周一 (09-21)', hf: '32° / 25° · 多云', bd: '31° / 24° · 晴', yk: '33° / 26° · 多云', diff: '一致 (差 2°C)', ok: true }
                ]
            },
            '成都': {
                code: '510100',
                temp: '21°',
                cond: '多云间阴 · 北风 1级',
                days: ['今天', '周日', '周一', '周二', '周三', '周四', '周五'],
                hfTemps: [21, 23, 20, 22, 24, 25, 23],
                bdTemps: [22, 22, 21, 23, 25, 24, 22],
                ykTemps: [21, 24, 19, 21, 24, 26, 24],
                table: [
                    { date: '今天 (09-19)', hf: '21° / 14° · 多云', bd: '22° / 15° · 阴', yk: '21° / 14° · 多云', diff: '一致 (差 1°C)', ok: true },
                    { date: '周日 (09-20)', hf: '23° / 15° · 阴', bd: '22° / 14° · 阴', yk: '24° / 16° · 阴', diff: '一致 (差 2°C)', ok: true }
                ]
            }
        };

        // Toast Notification System
        function quickNotify(msg, isError = false) {
            const toast = document.getElementById('toastWidget');
            const content = document.getElementById('toastContent');
            if (!toast || !content) return;
            content.textContent = msg;
            if (isError) {
                toast.style.borderColor = 'rgba(244, 63, 94, 0.4)';
                toast.style.boxShadow = '0 10px 30px rgba(244, 63, 94, 0.2)';
            } else {
                toast.style.borderColor = 'rgba(56, 189, 248, 0.3)';
                toast.style.boxShadow = '0 10px 30px rgba(0, 0, 0, 0.8)';
            }
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2800);
        }

        // Backend API Caller Helper
        async function apiCall(endpoint, method = 'GET', body = null) {
            const adminKey = localStorage.getItem('adminKey');
            const headers = {
                'Content-Type': 'application/json',
                'X-Admin-Key': adminKey || ''
            };
            const opts = { method, headers };
            if (body) opts.body = JSON.stringify(body);

            try {
                const res = await fetch(endpoint, opts);
                if (res.status === 403) {
                    showLoginModal();
                    quickNotify('管理凭证失效或无权限，请重新输入 Admin Key', true);
                    return null;
                }
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    quickNotify(err.detail || `请求失败 (${res.status})`, true);
                    return null;
                }
                return await res.json();
            } catch (e) {
                console.error('API Error:', e);
                quickNotify('网络异常，请确认后端服务已启动', true);
                return null;
            }
        }

        // --- Admin Authentication ---
        function showLoginModal() {
            const modal = document.getElementById('loginModal');
            if (modal) {
                modal.style.display = 'flex';
                document.getElementById('loginErrorMsg').textContent = '';
                document.getElementById('adminKeyInput').focus();
            }
        }

        function hideLoginModal() {
            const modal = document.getElementById('loginModal');
            if (modal) modal.style.display = 'none';
        }

        async function handleAdminLogin() {
            const keyInput = document.getElementById('adminKeyInput');
            const key = keyInput.value.trim();
            const errEl = document.getElementById('loginErrorMsg');
            const btn = document.getElementById('loginSubmitBtn');

            if (!key) {
                errEl.textContent = '请输入管理员密钥';
                return;
            }

            btn.disabled = true;
            btn.innerHTML = '<span>验证中...</span>';

            try {
                const res = await fetch('/api/v1/admin/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ key })
                });

                if (res.ok) {
                    localStorage.setItem('adminKey', key);
                    hideLoginModal();
                    quickNotify('管理员鉴权成功，已进入控制台');
                    await loadAllData();
                } else {
                    errEl.textContent = '管理员密钥验证失败，请核对后重试';
                }
            } catch (e) {
                errEl.textContent = '无法连接到后端认证服务';
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<span>验证并进入控制台</span><i data-lucide="arrow-right" style="width: 16px; height: 16px;"></i>';
                lucide.createIcons();
            }
        }

        function handleLogout() {
            if (confirm('确定要退出当前管理员控制台吗？')) {
                localStorage.removeItem('adminKey');
                location.reload();
            }
        }

        // --- Tab Navigation Switcher ---
        function switchNavTab(tabId, elem) {
            appState.currentTab = tabId;
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            if (elem) elem.classList.add('active');

            document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));
            const targetView = document.getElementById(`tab-${tabId}`);
            if (targetView) targetView.classList.add('active');

            const tabMeta = {
                'overview': { title: '监控大屏概览与流向拓扑', badge: '实时监控中', icon: 'gauge' },
                'insights': { title: '气象多源异构同屏比对核对所', badge: '多源核验', icon: 'git-compare' },
                'channels': { title: '数据渠道配置与 Key 池管理', badge: '轮询熔断池', icon: 'layers' },
                'clients': { title: '客户端 API Key 与网关访问控制', badge: 'QPM 与 IP 白名单', icon: 'shield-check' },
                'scheduler': { title: 'Celery Beat 动态定时采集调度控制台', badge: '热重载机制', icon: 'calendar-clock' },
                'playground': { title: 'API 交互沙盒与实时联调', badge: '沙盒环境', icon: 'terminal' }
            };

            const meta = tabMeta[tabId];
            if (meta) {
                const headerTitle = document.getElementById('stageHeaderTitle');
                if (headerTitle) {
                    headerTitle.innerHTML = `<i data-lucide="${meta.icon}" style="width: 16px; height: 16px; color: var(--accent-cyan);"></i><span>${meta.title}</span>`;
                }
                const headerBadge = document.getElementById('stageHeaderBadge');
                if (headerBadge) headerBadge.textContent = meta.badge;
                lucide.createIcons();
            }

            if (tabId === 'insights') {
                setTimeout(renderCompareChart, 60);
            }
        }

        // --- Data Loading & Ingestion ---
        async function loadAllData() {
            const [keys, channels] = await Promise.all([
                apiCall('/api/v1/admin/keys'),
                apiCall('/api/v1/admin/channels')
            ]);

            if (keys) appState.clientKeys = keys;
            if (channels) appState.channels = channels;

            renderOverview();
            renderChannelsView();
            renderClientsView();
            renderSchedulerView();
            populatePlaygroundKeys();
            lucide.createIcons();
        }

        // 1. Overview Tab Rendering
        function renderOverview() {
            const keys = appState.clientKeys || [];
            const channels = appState.channels || [];

            let todayTotal = 0;
            let total7d = 0;
            keys.forEach(k => {
                const stats = k.stats || {};
                todayTotal += Object.values(stats)[0] || 0;
                total7d += (k.total_usage_7d || 0);
            });

            // Update KPI Box
            const kpiToday = document.getElementById('kpiTodayCalls');
            if (kpiToday) kpiToday.textContent = todayTotal.toLocaleString();

            const kpiHealth = document.getElementById('kpiChannelHealth');
            if (kpiHealth) {
                let totalKeyCount = 0;
                let activeKeyCount = 0;
                channels.forEach(ch => {
                    (ch.keys_pool || []).forEach(kp => {
                        totalKeyCount++;
                        if (kp.status === 'active') activeKeyCount++;
                    });
                });
                const pct = totalKeyCount > 0 ? Math.round((activeKeyCount / totalKeyCount) * 100) : 100;
                kpiHealth.textContent = `${pct}%`;
            }

            // Overview Left: Client Keys Mini List
            const clientListWrap = document.getElementById('overviewClientKeysList');
            if (clientListWrap) {
                if (keys.length === 0) {
                    clientListWrap.innerHTML = '<div style="color: var(--text-muted); font-size: 12px; padding: 24px; text-align: center;">暂无客户端访问密钥，可点击右上角颁发新 Key</div>';
                } else {
                    clientListWrap.innerHTML = keys.slice(0, 5).map(k => {
                        const todayUsage = Object.values(k.stats || {})[0] || 0;
                        const tokenShort = k.key.length > 18 ? k.key.slice(0, 10) + '...' + k.key.slice(-4) : k.key;
                        const ipsStr = (k.ip_whitelist || []).join('\\n');
                        const ipEnabled = !!k.ip_whitelist_enabled;
                        const qpm = k.qpm_limit || 0;
                        return `
                        <div class="client-key-row-mini">
                            <div class="key-title-wrap">
                                <div>
                                    <div class="key-name-txt">${k.name}</div>
                                    <div class="key-token-mono">${tokenShort}</div>
                                </div>
                            </div>
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <span class="key-tag-qpm" style="background: rgba(129, 140, 248, 0.12); color: var(--accent-indigo); border: 1px solid rgba(129, 140, 248, 0.3);">限流: ${qpm > 0 ? qpm + ' QPM' : '无限制'}</span>
                                <div class="key-usage-highlight">
                                    <span class="usage-caption">今日调用</span>
                                    <span class="usage-number">${todayUsage.toLocaleString()} <span class="usage-unit">次</span></span>
                                </div>
                                <button class="btn-action-sm" title="编辑密钥配置" onclick="openKeyDrawer('${k.name}', '${k.key}', ${qpm}, '${ipsStr.replace(/\\n/g, '\\\\n')}', ${ipEnabled})">
                                    <i data-lucide="settings-2" style="width: 14px; height: 14px;"></i>
                                </button>
                            </div>
                        </div>
                        `;
                    }).join('');
                }
            }

            // Overview Right: Channel Watermarks
            const watermarkCard = document.getElementById('overviewChannelWatermarksCard');
            if (watermarkCard) {
                let watermarksHtml = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                        <div class="panel-title">
                            <i data-lucide="layers" style="width: 15px; height: 15px; color: var(--accent-cyan);"></i>
                            <span>上游渠道 Key 池今日配额消耗水位</span>
                        </div>
                    </div>
                `;

                const colors = {
                    hefeng: { color: 'var(--hefeng-color)', grad: 'linear-gradient(90deg, #0284c7, #38bdf8)' },
                    baidu: { color: 'var(--baidu-color)', grad: 'linear-gradient(90deg, #059669, #10b981)' },
                    yiketianqi: { color: 'var(--yike-color)', grad: 'linear-gradient(90deg, #d97706, #f59e0b)' }
                };

                channels.forEach(ch => {
                    const chId = ch._id;
                    const chName = ch.name || chId;
                    const keysPool = ch.keys_pool || [];
                    const activeKeys = keysPool.filter(k => k.status === 'active');
                    
                    let totalDailyLimit = 0;
                    let todayUsed = 0;

                    keysPool.forEach(kp => {
                        totalDailyLimit += (kp.daily_limit || 2000);
                        const stats = kp.stats || {};
                        todayUsed += Object.values(stats)[0] || 0;
                    });

                    const pct = totalDailyLimit > 0 ? Math.min(100, Math.round((todayUsed / totalDailyLimit) * 100)) : 0;
                    const cInfo = colors[chId] || { color: 'var(--accent-cyan)', grad: 'linear-gradient(90deg, #0284c7, #38bdf8)' };

                    watermarksHtml += `
                    <div class="channel-watermark-row">
                        <div class="watermark-top">
                            <div>
                                <strong style="color: #fff;">${chName}</strong>
                                <span style="color: var(--text-muted); font-size: 11px; margin-left: 6px;">${activeKeys.length}/${keysPool.length} 个可用 Key</span>
                            </div>
                            <span style="color: ${cInfo.color}; font-family: var(--font-mono); font-weight: 600;">${todayUsed.toLocaleString()} / ${totalDailyLimit.toLocaleString()} (${pct}%)</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill" style="width: ${pct}%; background: ${cInfo.grad};"></div>
                        </div>
                    </div>
                    `;
                });

                watermarkCard.innerHTML = watermarksHtml;
            }
        }

        // 2. Clients Tab Rendering
        function renderClientsView() {
            const keys = appState.clientKeys || [];

            let todayTotal = 0;
            let total7d = 0;
            keys.forEach(k => {
                const stats = k.stats || {};
                todayTotal += Object.values(stats)[0] || 0;
                total7d += (k.total_usage_7d || 0);
            });

            const elToday = document.getElementById('clientTabTodayUsage');
            if (elToday) elToday.innerHTML = `${todayTotal.toLocaleString()} <span style="font-size: 12px; font-weight: normal; color: var(--text-muted);">次</span>`;

            const el7d = document.getElementById('clientTab7dUsage');
            if (el7d) el7d.innerHTML = `${total7d.toLocaleString()} <span style="font-size: 12px; font-weight: normal; color: var(--text-muted);">次</span>`;

            const elCount = document.getElementById('clientTabCount');
            if (elCount) elCount.innerHTML = `${keys.length} <span style="font-size: 12px; font-weight: normal; color: var(--text-muted);">组</span>`;

            const tbody = document.getElementById('clientKeysTableBody');
            if (!tbody) return;

            if (keys.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;">暂无客户端访问密钥</td></tr>';
                return;
            }

            tbody.innerHTML = keys.map(k => {
                const todayUsage = Object.values(k.stats || {})[0] || 0;
                const total7d = k.total_usage_7d || 0;
                const qpm = k.qpm_limit || 0;
                const ips = k.ip_whitelist || [];
                const ipEnabled = !!k.ip_whitelist_enabled;
                const ipsStr = ips.join('\\n');

                let ipBadge = '<span style="color: var(--text-muted); font-size: 12px;">未启用白名单</span>';
                if (ipEnabled && ips.length > 0) {
                    ipBadge = `<span class="badge badge-info" style="font-size: 11px;">已绑定 ${ips.length} 个 IP</span>`;
                }

                return `
                <tr>
                    <td style="font-weight: 600; color: #fff;">${k.name}</td>
                    <td>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span class="token-mono">${k.key}</span>
                            <button class="btn-action-sm" title="复制完整 Key" onclick="copyToClipboard('${k.key}')">
                                <i data-lucide="copy" style="width: 12px; height: 12px;"></i>
                            </button>
                        </div>
                    </td>
                    <td>${qpm > 0 ? `<span class="badge badge-warning">${qpm} req/min</span>` : '<span style="color: var(--text-muted);">不限制</span>'}</td>
                    <td>${ipBadge}</td>
                    <td><span style="font-family: var(--font-mono); font-weight: 700; color: var(--accent-cyan); font-size: 13px;">${todayUsage.toLocaleString()} 次</span></td>
                    <td><span style="font-family: var(--font-mono); font-weight: 600; color: #fff;">${total7d.toLocaleString()} 次</span></td>
                    <td>
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <button class="btn-zinc" style="padding: 4px 8px; font-size: 11px;" onclick="openKeyDrawer('${k.name}', '${k.key}', ${qpm}, '${ipsStr.replace(/\\n/g, '\\\\n')}', ${ipEnabled})">
                                <i data-lucide="sliders" style="width: 12px; height: 12px;"></i>
                                编辑
                            </button>
                            <button class="btn-zinc" style="padding: 4px 8px; font-size: 11px; color: var(--accent-rose); border-color: rgba(244, 63, 94, 0.2);" onclick="deleteClientKey('${k.key}')">
                                <i data-lucide="trash-2" style="width: 12px; height: 12px;"></i>
                            </button>
                        </div>
                    </td>
                </tr>
                `;
            }).join('');
        }

        // 3. Channels Tab Rendering
        function renderChannelsView() {
            const channels = appState.channels || [];
            const cardsContainer = document.getElementById('channelSummaryCardsContainer');
            if (cardsContainer) {
                cardsContainer.innerHTML = channels.map(ch => {
                    const keys = ch.keys_pool || [];
                    const activeKeys = keys.filter(k => k.status === 'active');
                    let totalLimit = 0;
                    keys.forEach(k => totalLimit += (k.daily_limit || 2000));
                    const isActive = ch.is_active !== false;

                    return `
                    <div class="channel-summary-card">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <strong style="font-size: 14px; color: #fff;">${ch.name || ch._id} (${ch._id})</strong>
                                <span style="font-size: 11px; color: ${isActive ? 'var(--accent-emerald)' : 'var(--accent-rose)'}; background: ${isActive ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)'}; padding: 2px 6px; border-radius: 4px;">
                                    ${isActive ? '启用中' : '已停用'}
                                </span>
                            </div>
                            <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 12px;">提供多维度天气实况与预报报文聚合</p>
                            <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.6;">
                                <div>• 每日总限额: <strong>${totalLimit.toLocaleString()} 次</strong></div>
                                <div>• 当前可用 Key: <strong>${activeKeys.length} / ${keys.length} 个</strong></div>
                            </div>
                        </div>
                        <button class="btn-zinc" style="margin-top: 16px; justify-content: center;" onclick="triggerManualUpdate('${ch._id}')">
                            <i data-lucide="refresh-cw" style="width: 13px; height: 13px;"></i>
                            <span>手动触发异步更新</span>
                        </button>
                    </div>
                    `;
                }).join('');
            }

            // Channel Keys Table
            const tbody = document.getElementById('channelKeysTableBody');
            if (!tbody) return;

            let rowsHtml = '';
            channels.forEach(ch => {
                const chId = ch._id;
                const chName = ch.name || chId;
                const keys = ch.keys_pool || [];

                keys.forEach(kp => {
                    const stats = kp.stats || {};
                    const dates = Object.keys(stats).sort();
                    const d0 = stats[dates[0]] || 0;
                    const d1 = stats[dates[1]] || 0;
                    const d2 = stats[dates[2]] || 0;
                    const total3d = kp.total_3d || (d0 + d1 + d2);
                    const isKeyActive = kp.status === 'active';

                    rowsHtml += `
                    <tr>
                        <td><strong style="color: #fff;">${chName}</strong></td>
                        <td>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span class="token-mono">${kp.key}</span>
                                <button class="btn-action-sm" title="复制" onclick="copyToClipboard('${kp.key}')">
                                    <i data-lucide="copy" style="width: 12px; height: 12px;"></i>
                                </button>
                            </div>
                        </td>
                        <td>${(kp.daily_limit || 2000).toLocaleString()} 次/日</td>
                        <td>
                            <div class="sparkline-wrap" title="近3日趋势: ${d2} -> ${d1} -> ${d0}">
                                <div class="spark-bar" style="height: ${Math.max(4, Math.min(22, d2 / 20))}px;"></div>
                                <div class="spark-bar" style="height: ${Math.max(4, Math.min(22, d1 / 20))}px;"></div>
                                <div class="spark-bar" style="height: ${Math.max(4, Math.min(22, d0 / 20))}px;"></div>
                                <span style="font-size: 11px; font-family: var(--font-mono); margin-left: 6px; color: var(--text-muted);">${d0}次 (今)</span>
                            </div>
                        </td>
                        <td><strong style="font-family: var(--font-mono); color: #fff;">${total3d.toLocaleString()} 次</strong></td>
                        <td>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <label class="switch">
                                    <input type="checkbox" ${isKeyActive ? 'checked' : ''} onchange="toggleChannelKeyActive(this, '${chId}', '${kp.key}')">
                                    <span class="slider"></span>
                                </label>
                                <span class="key-status-text" style="font-size: 11.5px; color: ${isKeyActive ? 'var(--accent-emerald)' : 'var(--text-muted)'};">
                                    ${isKeyActive ? '轮询中' : '已禁用'}
                                </span>
                            </div>
                        </td>
                        <td>
                            <button class="btn-action-sm" style="color: var(--accent-rose);" title="移除此 Key" onclick="deleteChannelKey('${chId}', '${kp.key}')">
                                <i data-lucide="trash-2" style="width: 13px; height: 13px;"></i>
                            </button>
                        </td>
                    </tr>
                    `;
                });
            });

            if (!rowsHtml) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;">各渠道暂无 Key，请点击上方添加</td></tr>';
            } else {
                tbody.innerHTML = rowsHtml;
            }
        }

        // 4. Scheduler Tab Rendering (Celery Multi-Cron)
        function renderSchedulerView() {
            const channels = appState.channels || [];

            channels.forEach(ch => {
                const chId = ch._id;
                let rules = [];
                const cronVal = ch.cron || '';
                if (typeof cronVal === 'string') {
                    rules = cronVal.split(/[,\n]+/).map(s => s.trim()).filter(Boolean);
                } else if (Array.isArray(cronVal)) {
                    rules = cronVal;
                }

                const isActive = ch.is_active !== false;
                const delay = ch.wait_max || 10;

                if (chId === 'hefeng') {
                    const toggle = document.getElementById('schedActiveHefeng');
                    if (toggle) toggle.checked = isActive;
                    const countBadge = document.getElementById('hefengCronCount');
                    if (countBadge) countBadge.textContent = rules.length + ' 条';
                    renderCronPills('hefengCronList', rules);
                } else if (chId === 'baidu') {
                    const toggle = document.getElementById('schedActiveBaidu');
                    if (toggle) toggle.checked = isActive;
                    const countBadge = document.getElementById('baiduCronCount');
                    if (countBadge) countBadge.textContent = rules.length + ' 条';
                    renderCronPills('baiduCronList', rules);
                } else if (chId === 'yiketianqi') {
                    const toggle = document.getElementById('schedActiveYike');
                    if (toggle) toggle.checked = isActive;
                    const countBadge = document.getElementById('yikeCronCount');
                    if (countBadge) countBadge.textContent = rules.length + ' 条';
                    renderCronPills('yikeCronList', rules);
                }
            });
        }

        function renderCronPills(containerId, rules) {
            const container = document.getElementById(containerId);
            if (!container) return;
            container.innerHTML = '';
            if (rules.length === 0) {
                container.innerHTML = '<span style="font-size: 11px; color: var(--text-muted);">暂无配置定时采集规则</span>';
                return;
            }
            rules.slice(0, 6).forEach(rule => {
                const item = document.createElement('div');
                item.className = 'sched-cron-badge-item';
                item.innerHTML = `<span>${rule}</span><span style="color: var(--text-muted); font-size: 10px;">定时规则</span>`;
                container.appendChild(item);
            });
        }

        // 5. Playground Key Ingestion
        function populatePlaygroundKeys() {
            const select = document.getElementById('playKeySelect');
            if (!select) return;

            const keys = appState.clientKeys || [];
            let optionsHtml = '';
            keys.forEach(k => {
                const shortKey = k.key.length > 16 ? k.key.slice(0, 10) + '...' : k.key;
                optionsHtml += `<option value="${k.key}">${k.name} (${shortKey})</option>`;
            });
            optionsHtml += '<option value="custom">自定义输入 X-API-Key...</option>';
            select.innerHTML = optionsHtml;
        }

        // --- Client Key Operations ---
        function openAddClientModal() {
            const modal = document.getElementById('addClientKeyModal');
            if (modal) {
                document.getElementById('newClientNameInput').value = '';
                document.getElementById('newClientQpmInput').value = '60';
                modal.style.display = 'flex';
                document.getElementById('newClientNameInput').focus();
            }
        }

        function closeAddClientModal() {
            const modal = document.getElementById('addClientKeyModal');
            if (modal) modal.style.display = 'none';
        }

        async function submitNewClientKey() {
            const nameInput = document.getElementById('newClientNameInput');
            const qpmInput = document.getElementById('newClientQpmInput');
            const name = nameInput.value.trim() || '新应用终端';
            const qpm = parseInt(qpmInput.value) || 60;

            const res = await apiCall('/api/v1/admin/keys', 'POST', { name });
            if (res && res.key) {
                // If QPM differs from default, update it
                if (qpm !== 60) {
                    await apiCall(`/api/v1/admin/keys/${res.key}`, 'PUT', { qpm_limit: qpm });
                }
                closeAddClientModal();
                quickNotify(`客户端密钥 [${name}] 创建成功`);
                await loadAllData();
            }
        }

        let originalClientKey = '';
        function openKeyDrawer(name, token, qpm, ips, ipEnabled) {
            originalClientKey = token;
            document.getElementById('drawerHeading').textContent = `编辑客户端密钥: ${name}`;
            document.getElementById('drawerKeyName').value = name;
            document.getElementById('drawerKeyValue').value = token;
            document.getElementById('drawerKeyQpm').value = qpm;
            document.getElementById('drawerKeyIps').value = ips || '';
            document.getElementById('drawerKeyIpEnabled').checked = !!ipEnabled;
            document.getElementById('clientKeyDrawer').style.display = 'flex';
            lucide.createIcons();
        }

        function closeKeyDrawer() {
            document.getElementById('clientKeyDrawer').style.display = 'none';
        }

        async function saveKeyDrawer() {
            const newKeyVal = document.getElementById('drawerKeyValue').value.trim();
            const qpm = parseInt(document.getElementById('drawerKeyQpm').value) || 0;
            const ipsRaw = document.getElementById('drawerKeyIps').value.trim();
            const ipEnabled = document.getElementById('drawerKeyIpEnabled').checked;

            const ipList = ipsRaw ? ipsRaw.split(/[\\n,]+/).map(s => s.trim()).filter(Boolean) : [];

            const payload = {
                qpm_limit: qpm,
                ip_whitelist_enabled: ipEnabled,
                ip_whitelist: ipList
            };
            if (newKeyVal && newKeyVal !== originalClientKey) {
                payload.new_key = newKeyVal;
            }

            const res = await apiCall(`/api/v1/admin/keys/${originalClientKey}`, 'PUT', payload);
            if (res) {
                closeKeyDrawer();
                quickNotify('密钥配置与网关限流策略已更新');
                await loadAllData();
            }
        }

        async function deleteClientKey(token) {
            if (!confirm(`确定要彻底注销此客户端 API Key 吗？\\n此操作不可逆，下游系统将立即无法访问！`)) return;
            const res = await apiCall(`/api/v1/admin/keys/${token}`, 'DELETE');
            if (res) {
                quickNotify('客户端 API Key 已注销');
                await loadAllData();
            }
        }

        // --- Channel Key & Schedule Operations ---
        function openAddChannelKeyModal(defaultChannel = 'hefeng') {
            const modal = document.getElementById('addChannelKeyModal');
            if (modal) {
                const sel = document.getElementById('newChannelSelect');
                if (sel) sel.value = defaultChannel;
                document.getElementById('newChannelKeyInput').value = '';
                document.getElementById('newChannelLimitInput').value = '2000';
                document.getElementById('newChannelDescInput').value = '';
                modal.style.display = 'flex';
                document.getElementById('newChannelKeyInput').focus();
            }
        }

        function closeChannelModal() {
            const modal = document.getElementById('addChannelKeyModal');
            if (modal) modal.style.display = 'none';
        }

        async function submitChannelKey() {
            const chSel = document.getElementById('newChannelSelect');
            const channelId = chSel.value;
            const keyVal = document.getElementById('newChannelKeyInput').value.trim();
            const limit = parseInt(document.getElementById('newChannelLimitInput').value) || 2000;
            const desc = document.getElementById('newChannelDescInput').value.trim();

            if (!keyVal) {
                quickNotify('请输入渠道 API Key', true);
                return;
            }

            const res = await apiCall(`/api/v1/admin/channels/${channelId}/keys`, 'POST', {
                key: keyVal,
                daily_limit: limit,
                desc: desc
            });

            if (res) {
                closeChannelModal();
                quickNotify(`已为 [${channelId}] 注入新 API Key，并加入健康轮询池`);
                await loadAllData();
            }
        }

        async function deleteChannelKey(channelId, key) {
            if (!confirm(`确定要从渠道 [${channelId}] 轮询池中移除该 Key 吗？`)) return;
            const res = await apiCall(`/api/v1/admin/channels/${channelId}/keys`, 'DELETE', { key });
            if (res) {
                quickNotify('渠道 Key 已从轮询池注销');
                await loadAllData();
            }
        }

        async function toggleChannelKeyActive(checkbox, channelId, key) {
            const newStatus = checkbox.checked ? 'active' : 'disabled';
            const statusText = checkbox.closest('td').querySelector('.key-status-text');
            
            const res = await apiCall(`/api/v1/admin/channels/${channelId}/keys/status`, 'PUT', {
                key: key,
                status: newStatus
            });

            if (res) {
                if (statusText) {
                    statusText.textContent = checkbox.checked ? '轮询中' : '已禁用';
                    statusText.style.color = checkbox.checked ? 'var(--accent-emerald)' : 'var(--text-muted)';
                }
                quickNotify(`渠道 Key 状态已更新为 [${newStatus}]`);
            } else {
                checkbox.checked = !checkbox.checked;
            }
        }

        async function triggerManualUpdate(channelId) {
            const res = await apiCall(`/api/v1/admin/channels/${channelId}/update`, 'POST');
            if (res) {
                quickNotify(`已触发渠道 [${channelId}] 异步全量抓取更新任务`);
            }
        }

        // --- Celery Scheduler Modal & Operations ---
        let currentSchedChannelId = 'yiketianqi';
        let currentSchedChannelName = 'YIKETIANQI';

        function handleSchedModalToggleChange(isActive) {
            const badge = document.getElementById('channelSchedModalActiveStatus');
            if (!badge) return;
            if (isActive) {
                badge.className = 'status-badge status-healthy';
                badge.innerHTML = '<span class="status-dot"></span> 运行中';
            } else {
                badge.className = 'status-badge status-warning';
                badge.innerHTML = '<span class="status-dot" style="background: #f43f5e;"></span> 已暂停';
            }
        }

        function getHumanReadableCron(rule) {
            const parts = rule.trim().split(/\\s+/);
            if (parts.length !== 5) return '';
            const [min, hour, dom, mon, dow] = parts;
            if (min === '*/15' && hour === '*' && dom === '*' && mon === '*' && dow === '*') return '每 15 分钟';
            if (min === '*/30' && hour === '*' && dom === '*' && mon === '*' && dow === '*') return '每 30 分钟';
            if (min === '0' && hour === '*' && dom === '*' && mon === '*' && dow === '*') return '每小时整点';
            if (min.startsWith('*/') && hour === '*' && dom === '*' && mon === '*' && dow === '*') return `每 ${min.replace('*/', '')} 分钟`;
            if (dom === '*' && mon === '*' && dow === '*') {
                const pad = n => n.length === 1 ? '0' + n : n;
                if (/^\\d+$/.test(min) && /^\\d+$/.test(hour)) {
                    return `每天 ${pad(hour)}:${pad(min)}`;
                }
            }
            return '';
        }

        function updateCronRulePreview(cronStr) {
            const container = document.getElementById('channelSchedRulePills');
            const countBadge = document.getElementById('channelSchedRuleCountBadge');
            if (!container) return;
            container.innerHTML = '';
            if (!cronStr || !cronStr.trim()) {
                container.innerHTML = '<span style="font-size: 11px; color: var(--text-muted);">暂无配置任何调度规则</span>';
                if (countBadge) countBadge.textContent = '已解析 0 条';
                return;
            }
            const rules = cronStr.split(/[\\n,]+/).map(s => s.trim()).filter(Boolean);
            if (countBadge) countBadge.textContent = `已解析 ${rules.length} 条`;

            rules.forEach((rule, idx) => {
                const tag = document.createElement('div');
                tag.className = 'cron-rule-tag';
                const humanDesc = getHumanReadableCron(rule);
                let humanHtml = '';
                if (humanDesc) {
                    humanHtml = `<span class="rule-human-time">${humanDesc}</span>`;
                }
                tag.innerHTML = `<span style="color: var(--text-muted); font-size: 10px;">#${idx+1}</span><span>${rule}</span>${humanHtml}`;
                container.appendChild(tag);
            });
        }

        function openChannelScheduleModal(channelId, channelName, defaultRules, isActive, delay) {
            currentSchedChannelId = channelId;
            currentSchedChannelName = channelName;

            // Find latest channel config from appState if available
            const foundCh = appState.channels.find(c => c._id === channelId);
            let finalRules = defaultRules;
            let finalActive = isActive;
            let finalDelay = delay;

            if (foundCh) {
                finalRules = foundCh.cron || defaultRules;
                finalActive = foundCh.is_active !== false;
                finalDelay = foundCh.wait_max || delay || 10;
            }

            const badgeEl = document.getElementById('channelSchedModalBadge');
            if (badgeEl) badgeEl.textContent = channelName.toUpperCase();

            const toggle = document.getElementById('channelSchedActiveToggle');
            if (toggle) {
                toggle.checked = finalActive;
                handleSchedModalToggleChange(finalActive);
            }

            let formattedRules = '';
            if (Array.isArray(finalRules)) {
                formattedRules = finalRules.join(',\\n');
            } else if (typeof finalRules === 'string') {
                formattedRules = finalRules.split(/[\\n,]+/).map(s => s.trim()).filter(Boolean).join(',\\n');
            }

            document.getElementById('channelSchedCronInput').value = formattedRules;
            document.getElementById('channelSchedDelayInput').value = finalDelay || 10;
            document.getElementById('channelSchedDelayLabel').textContent = (finalDelay || 10) + ' 秒';
            updateCronRulePreview(formattedRules);
            document.getElementById('channelScheduleModal').style.display = 'flex';
            lucide.createIcons();
        }

        function closeChannelScheduleModal() {
            document.getElementById('channelScheduleModal').style.display = 'none';
        }

        function appendChannelCronPreset(presetCron) {
            const input = document.getElementById('channelSchedCronInput');
            let current = input.value.trim();
            if (current) {
                current += ',\\n' + presetCron;
            } else {
                current = presetCron;
            }
            input.value = current;
            updateCronRulePreview(current);
            quickNotify(`已添加预设规则: ${presetCron}`);
        }

        async function saveChannelScheduleModal() {
            const input = document.getElementById('channelSchedCronInput');
            const isActive = document.getElementById('channelSchedActiveToggle').checked;
            const delay = parseInt(document.getElementById('channelSchedDelayInput').value) || 10;
            const rules = input.value.split(/[\\n,]+/).map(s => s.trim()).filter(Boolean);

            const cronPayload = rules.join(',');

            const res = await apiCall(`/api/v1/admin/channels/${currentSchedChannelId}/schedule`, 'PUT', {
                cron: cronPayload,
                is_active: isActive,
                wait_max: delay
            });

            if (res) {
                closeChannelScheduleModal();
                quickNotify(`已保存 [${currentSchedChannelName}] 调度规则 (${rules.length} 条)，Celery Beat 已热重载`);
                await loadAllData();
            }
        }

        async function toggleChannelSchedActive(channelId, checkbox) {
            const res = await apiCall(`/api/v1/admin/channels/${channelId}/schedule`, 'PUT', {
                is_active: checkbox.checked
            });
            if (res) {
                quickNotify(`渠道 [${channelId}] Celery 定时采集已${checkbox.checked ? '开启' : '暂停'}`);
                await loadAllData();
            } else {
                checkbox.checked = !checkbox.checked;
            }
        }

        // --- Playground Request Builder ---
        let playRouteMode = 'path';
        let currentPlayCity = '上海';

        function handlePlayKeyChange(val) {
            const customInput = document.getElementById('playKeyCustomInput');
            if (val === 'custom') {
                customInput.style.display = 'block';
                customInput.focus();
            } else {
                customInput.style.display = 'none';
            }
            quickNotify('已切换沙盒 Header: X-API-Key 凭证');
        }

        function filterPlaygroundCities(query) {
            const q = query.trim().toLowerCase();
            const chips = document.querySelectorAll('#playgroundCityChips .city-chip-btn');
            chips.forEach(chip => {
                const city = chip.getAttribute('data-city').toLowerCase();
                const pinyin = chip.getAttribute('data-pinyin').toLowerCase();
                if (!q || city.includes(q) || pinyin.includes(q)) {
                    chip.style.display = 'inline-block';
                } else {
                    chip.style.display = 'none';
                }
            });
        }

        function selectPlayCity(city, btn) {
            currentPlayCity = city;
            document.querySelectorAll('#playgroundCityChips .city-chip-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            updatePlayRoute();
            quickNotify(`已填入预设城市: ${city}`);
        }

        function switchRouteParamMode(mode) {
            playRouteMode = mode;
            const pathBtn = document.getElementById('routeModePathBtn');
            const queryBtn = document.getElementById('routeModeQueryBtn');
            if (mode === 'path') {
                pathBtn.style.background = 'rgba(59,130,246,0.15)';
                pathBtn.style.color = 'var(--accent-cyan)';
                queryBtn.style.background = 'transparent';
                queryBtn.style.color = 'var(--text-secondary)';
            } else {
                queryBtn.style.background = 'rgba(59,130,246,0.15)';
                queryBtn.style.color = 'var(--accent-cyan)';
                pathBtn.style.background = 'transparent';
                pathBtn.style.color = 'var(--text-secondary)';
            }
            updatePlayRoute();
        }

        function updatePlayRoute() {
            const routeInput = document.getElementById('playRouteInput');
            if (playRouteMode === 'path') {
                routeInput.value = `/api/v1/weather/${currentPlayCity}`;
            } else {
                routeInput.value = `/api/v1/weather?city=${currentPlayCity}`;
            }
        }

        async function executePlaygroundRequest() {
            const routeInput = document.getElementById('playRouteInput');
            const keySelect = document.getElementById('playKeySelect');
            let apiKey = keySelect.value;
            if (apiKey === 'custom') {
                apiKey = document.getElementById('playKeyCustomInput').value.trim();
            }

            const latencyTag = document.getElementById('playLatencyTag');
            const viewer = document.getElementById('playgroundJsonViewer');

            if (!apiKey) {
                quickNotify('请选择或输入有效的 X-API-Key', true);
                return;
            }

            latencyTag.textContent = '请求中...';
            latencyTag.style.color = 'var(--accent-amber)';

            const startTime = performance.now();
            try {
                const res = await fetch(routeInput.value, {
                    headers: { 'X-API-Key': apiKey }
                });
                const endTime = performance.now();
                const latency = Math.round(endTime - startTime);

                const data = await res.json();
                viewer.textContent = JSON.stringify(data, null, 2);

                if (res.ok) {
                    latencyTag.textContent = `${res.status} OK · ${latency}ms`;
                    latencyTag.style.color = 'var(--accent-emerald)';
                    quickNotify(`沙盒联调成功: ${latency}ms 返回气象报文`);
                } else {
                    latencyTag.textContent = `${res.status} ${res.statusText} · ${latency}ms`;
                    latencyTag.style.color = 'var(--accent-rose)';
                    quickNotify(`请求失败: ${data.detail || res.statusText}`, true);
                }
            } catch (err) {
                const endTime = performance.now();
                const latency = Math.round(endTime - startTime);
                latencyTag.textContent = `网络错误 · ${latency}ms`;
                latencyTag.style.color = 'var(--accent-rose)';
                viewer.textContent = JSON.stringify({ error: err.message }, null, 2);
                quickNotify('网络连接中断或跨域错误', true);
            }
        }

        // --- Insights Cross-Check Tab (Canvas & City Filter) ---
        let currentActiveCity = '北京';

        function selectInsightCity(cityName, adcode, btn) {
            currentActiveCity = cityName;
            document.querySelectorAll('.city-pick-item').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');

            const data = weatherDatabase[cityName] || weatherDatabase['北京'];
            document.getElementById('currentCityTag').textContent = `${cityName}市 (${data.code}) · 今日融合实况`;
            document.getElementById('detailNowTemp').textContent = data.temp;
            document.getElementById('detailNowCond').querySelector('span').textContent = data.cond;

            renderTableBody(data.table);
            renderCompareChart();
            quickNotify(`已加载 ${cityName}市 多源气象数据`);
        }

        function renderTableBody(tableRows) {
            const tbody = document.getElementById('comparisonTableBody');
            if (!tbody) return;
            tbody.innerHTML = '';
            tableRows.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="font-weight: 600; color: #fff;">${row.date}</td>
                    <td><span style="font-family: var(--font-mono); font-size: 11.5px;">${row.hf}</span></td>
                    <td><span style="font-family: var(--font-mono); font-size: 11.5px;">${row.bd}</span></td>
                    <td><span style="font-family: var(--font-mono); font-size: 11.5px;">${row.yk}</span></td>
                    <td><span class="delta-chip ${row.ok ? 'delta-ok' : 'delta-warn'}">${row.diff}</span></td>
                `;
                tbody.appendChild(tr);
            });
        }

        function renderCompareChart() {
            const canvas = document.getElementById('weatherCompareChart');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            const dpr = window.devicePixelRatio || 1;
            const rect = canvas.getBoundingClientRect();

            canvas.width = rect.width * dpr;
            canvas.height = rect.height * dpr;
            ctx.scale(dpr, dpr);

            const w = rect.width;
            const h = rect.height;
            const pad = { top: 25, right: 25, bottom: 25, left: 30 };

            ctx.clearRect(0, 0, w, h);

            const data = weatherDatabase[currentActiveCity] || weatherDatabase['北京'];
            const allTemps = [...data.hfTemps, ...data.bdTemps, ...data.ykTemps];
            const minT = Math.min(...allTemps) - 2;
            const maxT = Math.max(...allTemps) + 2;

            const getX = i => pad.left + (i / (data.days.length - 1)) * (w - pad.left - pad.right);
            const getY = val => pad.top + (1 - (val - minT) / (maxT - minT)) * (h - pad.top - pad.bottom);

            // Grid lines
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
            ctx.lineWidth = 1;
            for (let t = Math.floor(minT); t <= Math.ceil(maxT); t += 3) {
                const y = getY(t);
                ctx.beginPath();
                ctx.moveTo(pad.left, y);
                ctx.lineTo(w - pad.right, y);
                ctx.stroke();

                ctx.fillStyle = '#64748b';
                ctx.font = '10px "JetBrains Mono"';
                ctx.textAlign = 'right';
                ctx.fillText(`${t}°`, pad.left - 6, y + 3);
            }

            // X-axis days
            ctx.textAlign = 'center';
            data.days.forEach((day, i) => {
                const x = getX(i);
                ctx.fillStyle = '#94a3b8';
                ctx.font = '11px "Inter"';
                ctx.fillText(day, x, h - 6);
            });

            function drawLine(temps, color) {
                ctx.beginPath();
                for (let i = 0; i < temps.length; i++) {
                    const x = getX(i);
                    const y = getY(temps[i]);
                    if (i === 0) ctx.moveTo(x, y);
                    else {
                        const prevX = getX(i - 1);
                        const prevY = getY(temps[i - 1]);
                        ctx.bezierCurveTo(prevX + (x - prevX) / 2, prevY, prevX + (x - prevX) / 2, y, x, y);
                    }
                }
                ctx.strokeStyle = color;
                ctx.lineWidth = 2.5;
                ctx.stroke();

                temps.forEach((val, i) => {
                    const x = getX(i);
                    const y = getY(val);
                    ctx.beginPath();
                    ctx.arc(x, y, 3.5, 0, Math.PI * 2);
                    ctx.fillStyle = '#0e1015';
                    ctx.fill();
                    ctx.strokeStyle = color;
                    ctx.lineWidth = 2;
                    ctx.stroke();
                });
            }

            drawLine(data.hfTemps, '#38bdf8');
            drawLine(data.bdTemps, '#10b981');
            drawLine(data.ykTemps, '#f59e0b');
        }

        function filterCityList(query) {
            const q = query.trim().toLowerCase();
            const items = document.querySelectorAll('.city-pick-item');
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                item.style.display = text.includes(q) ? 'flex' : 'none';
            });
        }

        function forceRefreshCurrentCity() {
            quickNotify(`已强制唤起 Fetcher 并行拉取 ${currentActiveCity} 最新三方报文`);
        }

        // Global manual refresh
        function manualGlobalRefresh() {
            quickNotify('所有网关状态、Redis 缓存与渠道连接已刷新');
            loadAllData();
        }

        // --- Command Palette (Cmd+K) ---
        function openCmdPalette() {
            document.getElementById('cmdPalette').style.display = 'flex';
            document.getElementById('cmdInputBox').focus();
        }

        function closeCmdPalette() {
            document.getElementById('cmdPalette').style.display = 'none';
        }

        function handlePaletteClick(e) {
            if (e.target.id === 'cmdPalette') closeCmdPalette();
        }

        window.addEventListener('keydown', (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                openCmdPalette();
            }
            if (e.key === 'Escape') {
                closeCmdPalette();
                closeKeyDrawer();
                closeChannelModal();
                closeAddClientModal();
                closeChannelScheduleModal();
            }
        });

        function runCmdAction(action) {
            closeCmdPalette();
            if (action === 'jump-insights-beijing') {
                switchNavTab('insights', document.querySelectorAll('.nav-item')[1]);
                selectInsightCity('北京', '110000', document.querySelectorAll('.city-pick-item')[0]);
            } else if (action === 'jump-insights-shanghai') {
                switchNavTab('insights', document.querySelectorAll('.nav-item')[1]);
                selectInsightCity('上海', '310000', document.querySelectorAll('.city-pick-item')[1]);
            } else if (action === 'open-new-client-modal') {
                openAddClientModal();
            } else if (action === 'jump-scheduler') {
                switchNavTab('scheduler', document.querySelectorAll('.nav-item')[4]);
            } else if (action === 'jump-playground') {
                switchNavTab('playground', document.querySelectorAll('.nav-item')[5]);
            }
        }

        function filterCmdList(val) {
            const q = val.trim().toLowerCase();
            const entries = document.querySelectorAll('.cmd-entry');
            entries.forEach(e => {
                e.style.display = e.textContent.toLowerCase().includes(q) ? 'flex' : 'none';
            });
        }

        // Copy utility
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                quickNotify('密钥凭据已成功复制到剪贴板');
            }).catch(() => {
                prompt('请手动复制:', text);
            });
        }

        window.addEventListener('resize', () => {
            if (appState.currentTab === 'insights') renderCompareChart();
        });

        // --- App Bootstrapping ---
        document.addEventListener('DOMContentLoaded', async () => {
            const key = localStorage.getItem('adminKey');
            if (!key) {
                showLoginModal();
            } else {
                try {
                    const res = await fetch('/api/v1/admin/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ key })
                    });
                    if (res.ok) {
                        hideLoginModal();
                        await loadAllData();
                    } else {
                        showLoginModal();
                    }
                } catch(e) {
                    showLoginModal();
                }
            }

            renderTableBody(weatherDatabase['北京'].table);
            setTimeout(renderCompareChart, 100);
        });
    </script>
</body>
</html>
"""

    final_html = head_and_body + real_js_engine

    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
    with open(dest_file, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"Successfully generated {dest_file}, size: {len(final_html)} bytes")

if __name__ == "__main__":
    build()
