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
        loginModal.classList.add('active');
        loginModal.style.display = 'flex';
        appContainer.classList.add('hidden');
    }

    function showApp() {
        loginModal.classList.remove('active');
        loginModal.style.display = 'none';
        appContainer.classList.remove('hidden');
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
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const tabId = item.getAttribute('data-tab');
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');

            tabSections.forEach(section => {
                const shouldShow = section.id === `section-${tabId}`;
                if (shouldShow) {
                    section.classList.remove('hidden');
                } else {
                    section.classList.add('hidden');
                }
            });
        });
    });

    // --- Client Keys ---
    async function loadClientKeys() {
        const keys = await apiCall('/api/v1/admin/keys');
        if (!keys) return;

        const totalToday = keys.reduce((sum, k) => {
            const todayVal = Object.values(k.stats)[0] || 0;
            return sum + todayVal;
        }, 0);
        document.getElementById('totalClientUsage').textContent = totalToday.toLocaleString();

        clientKeyList.innerHTML = keys.map(k => {
            const keyData = JSON.stringify(k).replace(/"/g, '&quot;');
            const todayUsage = Object.values(k.stats)[0] || 0;

            return `
            <div class="glass-card p-6 flex flex-col group hover:border-blue-500/30 hover:bg-slate-900/80 transition-all duration-300">
                <div class="flex justify-between items-start mb-6">
                    <div class="space-y-1">
                        <div class="text-lg font-medium text-white">${k.name}</div>
                        <div class="flex items-center gap-2 text-xs text-slate-500">
                            <span class="flex items-center gap-1"><i data-lucide="clock" class="w-3 h-3"></i> ${new Date(k.created_at).toLocaleDateString()}</span>
                            ${k.qpm_limit > 0 ? `<span class="px-1.5 py-0.5 bg-amber-500/10 text-amber-500 rounded border border-amber-500/20 uppercase tracking-tighter">QPM ${k.qpm_limit}</span>` : ''}
                            ${k.ip_whitelist_enabled ? `<span class="px-1.5 py-0.5 bg-emerald-500/10 text-emerald-500 rounded border border-emerald-500/20 uppercase tracking-tighter text-[9px]">IP LOCKED</span>` : ''}
                        </div>
                    </div>
                </div>
                
                <div class="bg-black/40 rounded-xl p-4 mb-6 font-mono text-sm text-blue-400 break-all border border-slate-800/50 flex items-center justify-between group-hover:border-blue-500/20">
                    <span class="truncate">${k.key}</span>
                </div>
                
                <div class="grid grid-cols-2 gap-4 mb-6">
                    <div class="bg-slate-950/50 rounded-xl p-3 border border-slate-800/50">
                        <div class="text-[10px] uppercase tracking-widest text-slate-500 mb-1">今日消耗</div>
                        <div class="text-xl font-display text-white">${todayUsage}</div>
                    </div>
                    <div class="bg-slate-950/50 rounded-xl p-3 border border-slate-800/50">
                        <div class="text-[10px] uppercase tracking-widest text-slate-500 mb-1">7日消耗</div>
                        <div class="text-xl font-display text-white">${k.total_usage_7d}</div>
                    </div>
                </div>

                <div class="mt-auto flex justify-end gap-3 pt-4 border-t border-slate-800/50">
                    <button class="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors flex items-center gap-2" onclick="openEditClientKey('${keyData}')">
                        <i data-lucide="settings" class="w-3.5 h-3.5"></i> 权限
                    </button>
                    <button class="px-4 py-2 rounded-lg text-xs font-medium text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition-colors flex items-center gap-2" onclick="deleteClientKey('${k.key}')">
                        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i> 删除
                    </button>
                </div>
            </div>
        `}).join('');
        lucide.createIcons();
    }

    window.deleteClientKey = async (key) => {
        if (!confirm('确定要删除该密钥吗？此操作不可恢复。')) return;
        await apiCall(`/api/v1/admin/keys/${key}`, 'DELETE');
        loadClientKeys();
    };

    window.openAddClientKey = () => {
        newKeyName.value = '';
        createKeyModal.classList.add('active');
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
        editKeyModal.classList.add('active');
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

        editKeyModal.classList.remove('active');
        loadClientKeys();
    };

    submitCreateKey.onclick = async () => {
        const name = newKeyName.value.trim();
        if (!name) return alert('请输入名称');

        await apiCall('/api/v1/admin/keys', 'POST', { name });
        createKeyModal.classList.remove('active');
        newKeyName.value = '';
        loadClientKeys();
    };

    // --- Channels ---
    let currentChannel = null;

    async function loadChannels() {
        const channels = await apiCall('/api/v1/admin/channels');
        if (!channels) return;

        const channelOverviewHTML = channels.map(c => {
            const keys = c.keys_pool || [];
            const keyCount = keys.length;
            const todayStr = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Shanghai' });

            const channelTodayUsage = keys.reduce((sum, k) => {
                const stats = k.stats || {};
                return sum + (stats[todayStr] || 0);
            }, 0);

            return `
                <div class="glass-card p-6">
                    <div class="flex justify-between items-start mb-4">
                        <div class="p-2 bg-emerald-500/10 rounded-lg text-emerald-400">
                            <i data-lucide="server" class="w-5 h-5"></i>
                        </div>
                        <span class="text-[10px] font-bold tracking-wider text-slate-500 uppercase">${c._id} API</span>
                    </div>
                    <div class="text-3xl font-display mb-1">${channelTodayUsage.toLocaleString()}</div>
                    <div class="text-xs text-slate-500">${keyCount} 个可用密钥</div>
                </div>
            `;
        }).join('');

        document.getElementById('channelOverview').innerHTML = channelOverviewHTML;

        channelList.innerHTML = channels.map(c => {
            const keys = c.keys_pool || [];
            const activeKeys = keys.filter(k => k.status === 'active').length;
            const totalCalls = keys.reduce((sum, k) => sum + (k.total_3d || 0), 0);

            return `
            <div class="glass-card overflow-hidden">
                <div class="p-6 border-b border-slate-800 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div class="space-y-1">
                        <div class="flex items-center gap-3">
                            <h3 class="text-xl font-display uppercase tracking-tight">${c._id}</h3>
                            <span class="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 text-[10px] font-bold uppercase border border-blue-500/20">${activeKeys}/${keys.length} 密钥在线</span>
                        </div>
                        <p class="text-sm text-slate-500 italic">3日累计调度: ${totalCalls.toLocaleString()} 次有效请求</p>
                    </div>
                    <div class="flex items-center gap-2">
                        <button class="btn-outline text-xs px-3 py-1.5" onclick="triggerChannelUpdate('${c._id}')">
                            <i data-lucide="refresh-cw" class="w-3 h-3"></i> 同步数据
                        </button>
                        <button class="btn-primary text-xs px-3 py-1.5" onclick="openAddChannelKey('${c._id}')">
                            <i data-lucide="plus" class="w-3 h-3"></i> 添加 Key
                        </button>
                    </div>
                </div>
                
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm">
                        <thead class="bg-slate-900/40 text-slate-500 uppercase text-[10px] font-bold tracking-widest">
                            <tr>
                                <th class="px-6 py-3 border-b border-slate-800">Key 凭证 / 备注</th>
                                <th class="px-6 py-3 border-b border-slate-800 text-center">状态</th>
                                <th class="px-6 py-3 border-b border-slate-800 text-center">限额</th>
                                <th class="px-6 py-3 border-b border-slate-800">近3日流水</th>
                                <th class="px-6 py-3 border-b border-slate-800">操作</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800">
                            ${keys.map(k => {
                const statsEntries = Object.entries(k.stats || {})
                    .sort((a, b) => b[0].localeCompare(a[0]))
                    .slice(0, 3);

                return `
                                <tr class="hover:bg-white/[0.02] transition-colors">
                                    <td class="px-6 py-4">
                                        <div class="font-mono text-xs text-slate-300 w-48 truncate" title="${k.key}">${k.key}</div>
                                        <div class="text-[11px] text-slate-500 mt-0.5">${k.desc || '默认备注'}</div>
                                    </td>
                                    <td class="px-6 py-4 text-center">
                                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${k.status === 'active' ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-500 border border-rose-500/20'}">
                                            ${k.status.toUpperCase()}
                                        </span>
                                    </td>
                                    <td class="px-6 py-4 text-center font-mono text-slate-400">${k.daily_limit}</td>
                                    <td class="px-6 py-4">
                                        <div class="flex gap-2">
                                            ${statsEntries.map(([date, count]) => `
                                                <div class="px-1.5 py-1 bg-slate-950 rounded flex flex-col items-center min-w-[40px] border border-slate-800">
                                                    <span class="text-[8px] text-slate-600">${date.slice(5)}</span>
                                                    <span class="text-[10px] font-bold ${count > 0 ? 'text-blue-400' : 'text-slate-500'}">${count}</span>
                                                </div>
                                            `).join('') || '<span class="text-slate-600 italic text-xs">无数据</span>'}
                                        </div>
                                    </td>
                                    <td class="px-6 py-4 text-center">
                                        <button class="p-2 text-slate-500 hover:text-rose-400 transition-colors" onclick="removeChannelKey('${c._id}', '${k.key}')">
                                            <i data-lucide="trash-2" class="w-4 h-4"></i>
                                        </button>
                                    </td>
                                </tr>
                                `;
            }).join('')}
                            ${keys.length === 0 ? '<tr><td colspan="5" class="px-6 py-10 text-center text-slate-600 italic">尚未配置 API 密钥池</td></tr>' : ''}
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
        addChannelKeyModal.classList.add('active');
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
        }
    };

    submitAddChannelKey.onclick = async () => {
        const key = newChannelKey.value.trim();
        const limit = parseInt(newChannelLimit.value);
        const desc = newChannelDesc.value.trim();
        if (!key) return alert('请输入 Key');

        await apiCall(`/api/v1/admin/channels/${currentChannel}/keys`, 'POST', {
            key, daily_limit: limit, desc
        });
        addChannelKeyModal.classList.remove('active');
        loadChannels();
    };

    // --- Common Modal Logic ---
    document.querySelectorAll('.close').forEach(span => {
        span.onclick = function () {
            this.closest('.modal-overlay').classList.remove('active');
        }
    });

    window.onclick = (event) => {
        if (event.target.classList.contains('modal-overlay') && event.target.id !== 'loginModal') {
            event.target.classList.remove('active');
        }
    };

    // Init
    checkAuth();
});

