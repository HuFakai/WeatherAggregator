document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const loginModal = document.getElementById('loginModal');
    const appContainer = document.getElementById('appContainer');
    const adminKeyInput = document.getElementById('adminKeyInput');
    const loginBtn = document.getElementById('loginBtn');
    const loginError = document.getElementById('loginError');
    const logoutBtn = document.getElementById('logoutBtn');

    // Page Header
    const pageTitle = document.getElementById('pageTitle');
    const pageSubtitle = document.getElementById('pageSubtitle');
    const currentTimeEl = document.getElementById('currentTime');

    // Tabs
    const navItems = document.querySelectorAll('.nav-item');
    const tabSections = document.querySelectorAll('.tab-section');

    // Client Keys Elements
    const clientKeyList = document.getElementById('clientKeyList');
    const createKeyModal = document.getElementById('createKeyModal');
    const submitCreateKey = document.getElementById('submitCreateKey');
    const newKeyName = document.getElementById('newKeyName');

    // Channel Elements
    const channelList = document.getElementById('channelList');
    const addChannelKeyModal = document.getElementById('addChannelKeyModal');
    const submitAddChannelKey = document.getElementById('submitAddChannelKey');
    const newChannelKey = document.getElementById('newChannelKey');
    const newChannelLimit = document.getElementById('newChannelLimit');
    const newChannelDesc = document.getElementById('newChannelDesc');

    // Initialize Dashboard Time
    function updateTime() {
        const now = new Date();
        currentTimeEl.textContent = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    }
    setInterval(updateTime, 1000);
    updateTime();

    // --- Auth Logic ---
    function checkAuth() {
        const key = localStorage.getItem('adminKey');
        if (key) {
            verifyKey(key).then(isValid => {
                if (isValid) {
                    showApp();
                    loadData();
                } else {
                    showLogin();
                }
            });
        } else {
            showLogin();
        }
    }

    async function verifyKey(key) {
        try {
            const res = await fetch('/api/v1/admin/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: key })
            });
            return res.ok;
        } catch (e) {
            return false;
        }
    }

    function showLogin() {
        loginModal.style.display = 'flex';
        appContainer.style.display = 'none';
        document.body.style.overflow = 'hidden';
    }

    function showApp() {
        loginModal.style.display = 'none';
        appContainer.style.display = 'flex'; // Changed to flex for sidebar layout
        document.body.style.overflow = 'auto';
        lucide.createIcons();
    }

    loginBtn.addEventListener('click', async () => {
        const key = adminKeyInput.value.trim();
        if (!key) return;

        // Show loading state
        const originalBtnText = loginBtn.innerHTML;
        loginBtn.innerHTML = '<i data-lucide="loader-2" class="spin"></i>登录中...';
        lucide.createIcons();

        const isValid = await verifyKey(key);
        if (isValid) {
            localStorage.setItem('adminKey', key);
            showApp();
            loadData();
            loginError.textContent = '';
        } else {
            loginError.textContent = '密钥验证失败，请检查后重试';
            loginBtn.innerHTML = originalBtnText; // Reset button
            lucide.createIcons();
        }
    });

    logoutBtn.addEventListener('click', () => {
        if (confirm('确定要退出登录吗？')) {
            localStorage.removeItem('adminKey');
            location.reload();
        }
    });

    // --- API Helper ---
    async function apiCall(url, method = 'GET', body = null) {
        const key = localStorage.getItem('adminKey');
        const headers = {
            'X-Admin-Key': key,
            'Content-Type': 'application/json'
        };

        const options = { method, headers };
        if (body) options.body = JSON.stringify(body);

        try {
            const res = await fetch(url, options);
            if (res.status === 403) {
                alert('会话已过期，请重新登录');
                localStorage.removeItem('adminKey');
                location.reload();
                return null;
            }
            return res.json();
        } catch (error) {
            console.error('API Error:', error);
            showToast('请求失败，请检查网络', 'error');
            return null;
        }
    }

    // --- Data Loading ---
    function loadData() {
        loadClientKeys();
        loadChannels();
    }

    // --- Tabs Logic ---
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            if (item.id === 'logoutBtn') return;

            const tabId = item.getAttribute('data-tab');

            // Update Nav
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');

            // Show Section
            tabSections.forEach(section => {
                const shouldShow = section.id === `section-${tabId}`;
                section.style.display = shouldShow ? 'block' : 'none';
                section.classList.toggle('active-section', shouldShow);
            });

            // Update Header Title
            if (tabId === 'clients') {
                pageTitle.textContent = '客户端密钥';
                pageSubtitle.textContent = '管理 API 访问权限与统计';
            } else if (tabId === 'channels') {
                pageTitle.textContent = '数据渠道管理';
                pageSubtitle.textContent = '监控三方天气源状态与配额';
            }

            // Re-render icons for new content
            lucide.createIcons();
        });
    });

    // --- Toast Notification ---
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: ${type === 'success' ? 'var(--success)' : 'var(--danger)'};
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            animation: slideIn 0.3s ease;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
        `;

        // Add icon based on type
        const iconName = type === 'success' ? 'check-circle' : 'alert-circle';
        toast.innerHTML = `<i data-lucide="${iconName}"></i> ${message}`;

        document.body.appendChild(toast);
        lucide.createIcons();

        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // Add slide animations to document head
    const styleSheet = document.createElement("style");
    styleSheet.innerText = `
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        @keyframes slideOut { from { transform: translateX(0); opacity: 1; } to { transform: translateX(100%); opacity: 0; } }
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
    `;
    document.head.appendChild(styleSheet);


    // --- Client Keys ---
    async function loadClientKeys() {
        const keys = await apiCall('/api/v1/admin/keys');
        if (!keys) return;

        // Calculate Total Usage
        const totalToday = keys.reduce((sum, k) => {
            const todayVal = Object.values(k.stats)[0] || 0;
            return sum + todayVal;
        }, 0);
        document.getElementById('totalClientUsage').textContent = totalToday.toLocaleString();

        clientKeyList.innerHTML = keys.map(k => {
            const keyData = JSON.stringify(k).replace(/"/g, '&quot;');
            const todayUsage = Object.values(k.stats)[0] || 0;

            return `
            <div class="glass-card key-card">
                <div class="key-card-header">
                    <div>
                        <div class="key-title">${k.name}</div>
                        <div class="key-meta">
                            <span class="badge" style="background: rgba(255,255,255,0.1); color: var(--text-muted)">
                                ${new Date(k.created_at).toLocaleDateString()}
                            </span>
                            ${k.qpm_limit > 0 ? `<span class="badge badge-warning">QPM:${k.qpm_limit}</span>` : ''}
                            ${k.ip_whitelist_enabled ? `<span class="badge badge-success">IP限制</span>` : ''}
                        </div>
                    </div>
                </div>
                
                <div class="key-display">${k.key}</div>
                
                <div class="stats-container">
                    <div class="key-stats-row">
                        <div class="stat-item">
                            <div class="label">今日调用</div>
                            <div class="value">${todayUsage}</div>
                        </div>
                        <div class="stat-item">
                            <div class="label">7日总量</div>
                            <div class="value">${k.total_usage_7d}</div>
                        </div>
                        <div class="card-actions-overlay">
                            <button class="btn-icon-only" onclick="openEditClientKey('${keyData}')" title="编辑">
                                <i data-lucide="settings-2"></i>
                            </button>
                            <button class="btn-icon-only danger" onclick="deleteClientKey('${k.key}')" title="删除">
                                <i data-lucide="trash-2"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `}).join('');

        lucide.createIcons();
    }

    window.deleteClientKey = async (key) => {
        if (!confirm('确定要删除该密钥吗？此操作不可恢复。')) return;
        await apiCall(`/api/v1/admin/keys/${key}`, 'DELETE');
        showToast('密钥已删除');
        loadClientKeys();
    };

    window.openAddClientKey = () => {
        newKeyName.value = '';
        createKeyModal.style.display = 'flex';
    };

    // Edit Logic
    const editKeyModal = document.getElementById('editKeyModal');
    const editKeyId = document.getElementById('editKeyId');
    const editKeyQpm = document.getElementById('editKeyQpm');
    const editKeyIpList = document.getElementById('editKeyIpList');
    const editKeyIpEnabled = document.getElementById('editKeyIpEnabled');
    const submitEditKey = document.getElementById('submitEditKey');

    window.openEditClientKey = (keyDataStr) => {
        const k = JSON.parse(keyDataStr);
        editKeyId.value = k.key;
        editKeyQpm.value = k.qpm_limit || 0;
        editKeyIpList.value = (k.ip_whitelist || []).join('\n');
        editKeyIpEnabled.checked = k.ip_whitelist_enabled || false;
        editKeyModal.style.display = 'flex';
    };

    submitEditKey.onclick = async () => {
        const key = editKeyId.value;
        const qpm = parseInt(editKeyQpm.value) || 0;
        const ipList = editKeyIpList.value.split('\n').map(ip => ip.trim()).filter(ip => ip);
        const ipEnabled = editKeyIpEnabled.checked;

        await apiCall(`/api/v1/admin/keys/${key}`, 'PUT', {
            qpm_limit: qpm,
            ip_whitelist: ipList,
            ip_whitelist_enabled: ipEnabled
        });

        editKeyModal.style.display = 'none';
        showToast('配置已更新');
        loadClientKeys();
    };

    submitCreateKey.onclick = async () => {
        const name = newKeyName.value.trim();
        if (!name) return alert('请输入名称');

        await apiCall('/api/v1/admin/keys', 'POST', { name });
        createKeyModal.style.display = 'none';
        newKeyName.value = '';
        showToast('密钥创建成功');
        loadClientKeys();
    };

    // --- Channels ---
    let currentChannel = null;

    async function loadChannels() {
        const channels = await apiCall('/api/v1/admin/channels');
        if (!channels) return;

        // Calculate Channel Stats
        const channelOverviewHTML = channels.map(c => {
            const keys = c.keys_pool || [];
            const keyCount = keys.length;
            const todayStr = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Shanghai' });

            const channelTodayUsage = keys.reduce((sum, k) => {
                const stats = k.stats || {};
                return sum + (stats[todayStr] || 0);
            }, 0);

            return `
                <div class="stat-card glass-card">
                    <div class="stat-icon-bg" style="background: rgba(16, 185, 129, 0.1); color: var(--success)">
                        <i data-lucide="${c._id === 'hefeng' ? 'cloud-rain' : 'sun'}"></i>
                    </div>
                    <div class="stat-content">
                        <div class="stat-label">${c._id.toUpperCase()} (KEYS: ${keyCount})</div>
                        <div class="stat-value">${channelTodayUsage.toLocaleString()}</div>
                    </div>
                </div>
            `;
        }).join('');

        document.getElementById('channelOverview').innerHTML = channelOverviewHTML;

        channelList.innerHTML = channels.map(c => {
            const keys = c.keys_pool || [];
            const totalCalls = keys.reduce((sum, k) => sum + (k.total_3d || 0), 0);

            return `
            <div class="glass-card channel-card">
                <div class="card-header" style="padding: 1.5rem; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;">
                    <div class="card-title-group">
                        <div class="card-title" style="display: flex; align-items: center; gap: 8px;">
                            <span class="channel-status-dot ${c.is_active ? '' : 'inactive'}"></span>
                            ${c._id.toUpperCase()}
                        </div>
                        <div class="card-subtitle" style="color: var(--text-muted); font-size: 0.85rem;">3日总调用: ${totalCalls}</div>
                    </div>
                    <div class="card-actions" style="display: flex; gap: 10px;">
                         <button class="btn-primary" style="padding: 6px 12px; font-size: 0.85rem;" onclick="triggerChannelUpdate('${c._id}')">
                            <i data-lucide="refresh-cw" style="width: 14px;"></i> 一键更新
                        </button>
                        <button class="btn-primary" style="padding: 6px 12px; font-size: 0.85rem; background: transparent; border: 1px solid var(--border-color);" onclick="openAddChannelKey('${c._id}')">
                            <i data-lucide="plus" style="width: 14px;"></i> 添加 Key
                        </button>
                    </div>
                </div>
                
                <div class="key-table-wrapper" style="padding: 0 1.5rem 1.5rem;">
                    <table class="channel-key-table">
                        <thead>
                            <tr>
                                <th>Key / 备注</th>
                                <th>状态</th>
                                <th>限额</th>
                                <th>3日统计</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${keys.map(k => {
                const statsStr = Object.entries(k.stats || {})
                    .sort((a, b) => b[0].localeCompare(a[0]))
                    .slice(0, 3)
                    .map(([date, count]) => `
                        <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 4px;">
                            <span style="font-size: 0.8rem; color: var(--text-muted)">${date.slice(5)}</span>
                            <span style="font-family: 'JetBrains Mono'; font-weight: 700; color: ${count > 0 ? 'var(--success)' : 'var(--text-muted)'}; font-size: 0.95rem;">${count}</span>
                        </div>
                    `)
                    .join('');

                return `
                                <tr>
                                    <td>
                                        <div class="key-code" title="${k.key}" style="font-family: monospace; color: #e2e8f0;">${k.key.slice(0, 10)}...</div>
                                        <div class="key-desc" style="font-size: 0.8rem; color: var(--text-muted);">${k.desc || '-'}</div>
                                    </td>
                                    <td>
                                        <span class="badge ${k.status === 'active' ? 'badge-success' : 'badge-warning'}">${k.status}</span>
                                    </td>
                                    <td>${k.daily_limit}</td>
                                    <td>${statsStr || '-'}</td>
                                    <td>
                                        <button class="btn-icon-only danger" onclick="removeChannelKey('${c._id}', '${k.key}')" title="删除">
                                            <i data-lucide="trash-2" style="width: 16px;"></i>
                                        </button>
                                    </td>
                                </tr>
                                `;
            }).join('')}
                            ${keys.length === 0 ? '<tr><td colspan="5" style="text-align: center; padding: 2rem; color: var(--text-muted)">暂无 Key 配置</td></tr>' : ''}
                        </tbody>
                    </table>
                </div>
            </div>
        `}).join('');

        lucide.createIcons();
    }

    window.openAddChannelKey = (channel) => {
        currentChannel = channel;
        newChannelKey.value = '';
        newChannelLimit.value = '2000';
        newChannelDesc.value = '';
        addChannelKeyModal.style.display = 'flex';
    };

    window.removeChannelKey = async (channel, key) => {
        if (!confirm('确定要移除该 Key 吗？')) return;
        await apiCall(`/api/v1/admin/channels/${channel}/keys`, 'DELETE', { key });
        showToast('Key 已移除');
        loadChannels();
    };

    window.triggerChannelUpdate = async (channel) => {
        if (!confirm(`确定要立即触发 [${channel}] 的全量更新吗？\n这将在后台启动异步任务。`)) return;

        const res = await apiCall(`/api/v1/admin/channels/${channel}/update`, 'POST');
        if (res && res.status === 'triggered') {
            showToast('更新任务已触发');
        } else {
            showToast('触发失败，请查看日志', 'error');
        }
    };

    submitAddChannelKey.onclick = async () => {
        const key = newChannelKey.value.trim();
        const limit = parseInt(newChannelLimit.value);
        const desc = newChannelDesc.value.trim();

        if (!key) return alert('请输入 Key');

        await apiCall(`/api/v1/admin/channels/${currentChannel}/keys`, 'POST', {
            key,
            daily_limit: limit,
            desc
        });
        addChannelKeyModal.style.display = 'none';
        showToast('渠道 Key 添加成功');
        loadChannels();
    };

    // --- Common Modal Logic ---
    // Handle close button click
    document.querySelectorAll('.close-btn').forEach(btn => {
        btn.onclick = function () {
            const modal = this.closest('.modal');
            modal.style.display = 'none';
        }
    });

    window.onclick = (event) => {
        if (event.target.classList.contains('modal') && event.target.id !== 'loginModal') {
            event.target.style.display = 'none';
        }
    };

    // Init
    checkAuth();
});
