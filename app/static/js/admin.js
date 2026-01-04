document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const loginModal = document.getElementById('loginModal');
    const appContainer = document.getElementById('appContainer');
    const adminKeyInput = document.getElementById('adminKeyInput');
    const loginBtn = document.getElementById('loginBtn');
    const loginError = document.getElementById('loginError');
    const logoutBtn = document.getElementById('logoutBtn');

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
    }

    function showApp() {
        loginModal.style.display = 'none';
        appContainer.style.display = 'block';
    }

    loginBtn.addEventListener('click', async () => {
        const key = adminKeyInput.value.trim();
        if (!key) return;

        const isValid = await verifyKey(key);
        if (isValid) {
            localStorage.setItem('adminKey', key);
            showApp();
            loadData();
            loginError.textContent = '';
        } else {
            loginError.textContent = '密钥无效，请重试';
        }
    });

    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('adminKey');
        location.reload();
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

        const res = await fetch(url, options);
        if (res.status === 403) {
            alert('会话已过期，请重新登录');
            localStorage.removeItem('adminKey');
            location.reload();
            return null;
        }
        return res.json();
    }

    // --- Data Loading ---
    function loadData() {
        loadClientKeys();
        loadChannels();
    }

    // --- Tabs Logic ---
    console.log('Found nav items:', navItems.length);
    console.log('Found tab sections:', tabSections.length);

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const tabId = item.getAttribute('data-tab');
            console.log('Tab clicked:', tabId);

            // Update Nav
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');

            // Show Section
            tabSections.forEach(section => {
                const shouldShow = section.id === `section-${tabId}`;
                section.style.display = shouldShow ? 'block' : 'none';
                console.log(`Section ${section.id} display: ${shouldShow ? 'block' : 'none'}`);
            });
        });
    });

    // --- Client Keys ---
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
            // Prepare data for edit (escape quotes)
            const keyData = JSON.stringify(k).replace(/"/g, '&quot;');

            return `
            return `
                < div class="card" >
                <div class="card-header">
                    <div>
                        <div class="card-title">
                            <span style="width:6px; height:6px; background:var(--accent-color); border-radius:50%; display:inline-block;"></span>
                            ${k.name}
                        </div>
                        <div class="card-subtitle">
                            CREATED: ${new Date(k.created_at).toLocaleDateString()}
                            ${k.qpm_limit > 0 ? `<span class="badge badge-warning" style="margin-left:6px">QPM: ${k.qpm_limit}</span>` : ''}
                            ${k.ip_whitelist_enabled ? `<span class="badge badge-success" style="margin-left:4px">IP: ON</span>` : ''}
                        </div>
                    </div>
                </div>
                
                <div class="client-key-display" title="Click to copy" onclick="navigator.clipboard.writeText('${k.key}')">${k.key}</div>
                
                <div class="stats-container">
                    <div class="stat-box">
                        <div class="stat-label">TODAY</div>
                        <div class="stat-value">${Object.values(k.stats)[0] || 0}</div>
                    </div>
                    <div class="stat-divider"></div>
                    <div class="stat-box">
                        <div class="stat-label">7 DAYS</div>
                        <div class="stat-value">${k.total_usage_7d}</div>
                    </div>
                </div>

                <div class="delete-btn-wrapper" style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1rem; border-top: 1px solid var(--card-border); padding-top: 1rem;">
                    <button class="btn-text" onclick="openEditClientKey('${keyData}')">EDIT</button>
                    <button class="btn-danger-text" onclick="deleteClientKey('${k.key}')">REVOKE</button>
                </div>
            </div >
                `}).join('');
        `}).join('');
    }

    window.deleteClientKey = async (key) => {
        if (!confirm('确定要删除该密钥吗？此操作不可恢复。')) return;
        await apiCall(`/api/v1/admin/keys/${key}`, 'DELETE');
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
        loadClientKeys();
    };

    submitCreateKey.onclick = async () => {
        const name = newKeyName.value.trim();
        if (!name) return alert('请输入名称');

        await apiCall('/api/v1/admin/keys', 'POST', { name });
        createKeyModal.style.display = 'none';
        newKeyName.value = '';
        loadClientKeys();
    };

    // --- Channels ---
    let currentChannel = null;

    async function loadChannels() {
        const channels = await apiCall('/api/v1/admin/channels');
        console.log('Loaded channels:', channels);
        if (!channels) return;

        // Calculate Channel Stats
        const channelOverviewHTML = channels.map(c => {
            const keys = c.keys_pool || [];
            const keyCount = keys.length;
            // Calculate today's usage for this channel
            // Use Asia/Shanghai timezone to match backend
            const todayStr = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Shanghai' });

            const channelTodayUsage = keys.reduce((sum, k) => {
                const stats = k.stats || {};
                return sum + (stats[todayStr] || 0);
            }, 0);

            return `
                <div class="overview-card">
                    <div class="overview-label">${c._id.toUpperCase()} (${keyCount} KEYS)</div>
                    <div class="overview-value">${channelTodayUsage.toLocaleString()}</div>
                </div>
            `;
        }).join('<div class="overview-divider"></div>');

        document.getElementById('channelOverview').innerHTML = channelOverviewHTML;

        channelList.innerHTML = channels.map(c => {
            const keys = c.keys_pool || [];
            const totalCalls = keys.reduce((sum, k) => sum + (k.total_3d || 0), 0);

            return `
            <div class="card channel-card">
                <div class="card-header">
                    <div class="card-title-group">
                        <div class="card-title">
                            <span class="status-dot ${c.is_active ? '' : 'status-inactive'}"></span>
                            ${c._id.toUpperCase()}
                        </div>
                        <div class="card-subtitle">3日总调用: ${totalCalls}</div>
                    </div>
                    <div class="card-actions">
                        <button class="btn-sm btn-outline" onclick="triggerChannelUpdate('${c._id}')" style="margin-right: 8px;">⟳ 一键更新</button>
                        <button class="btn-sm btn-outline" onclick="openAddChannelKey('${c._id}')">+ 添加 Key</button>
                    </div>
                </div>
                
                <div class="key-table-wrapper">
                    <table class="key-table">
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
                    .sort((a, b) => b[0].localeCompare(a[0])) // 按日期降序
                    .map(([date, count]) => `<div class="stat-mini"><span class="stat-date">${date.slice(5)}</span>: <span class="stat-val">${count}</span></div>`)
                    .join('');

                return `
                                <tr>
                                    <td>
                                        <div class="key-code" title="${k.key}">${k.key.slice(0, 12)}...</div>
                                        <div class="key-desc">${k.desc || '-'}</div>
                                    </td>
                                    <td>
                                        <span class="badge ${k.status === 'active' ? 'badge-success' : 'badge-warning'}">${k.status}</span>
                                    </td>
                                    <td>${k.daily_limit}</td>
                                    <td>
                                        <div class="stats-mini-grid">
                                            ${statsStr || '<span class="text-muted">无数据</span>'}
                                        </div>
                                    </td>
                                    <td>
                                        <button class="btn-icon" onclick="removeChannelKey('${c._id}', '${k.key}')" title="删除">&times;</button>
                                    </td>
                                </tr>
                                `;
            }).join('')}
                            ${keys.length === 0 ? '<tr><td colspan="5" class="text-center text-muted">暂无 Key 配置</td></tr>' : ''}
                        </tbody>
                    </table>
                </div>
            </div>
        `}).join('');
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
        loadChannels();
    };

    window.triggerChannelUpdate = async (channel) => {
        if (!confirm(`确定要立即触发 [${channel}] 的全量更新吗？\n这将在后台启动异步任务。`)) return;

        const res = await apiCall(`/api/v1/admin/channels/${channel}/update`, 'POST');
        if (res && res.status === 'triggered') {
            alert(`更新任务已触发！\n${res.message}`);
        } else {
            alert('触发失败，请查看控制台日志');
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
        loadChannels();
    };

    // --- Common Modal Logic ---
    document.querySelectorAll('.close').forEach(span => {
        span.onclick = function () {
            this.closest('.modal').style.display = 'none';
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
