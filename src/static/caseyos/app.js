/**
 * CaseyOS Dashboard Application
 * GTM Command Center for proactive work prioritization
 */

// Configuration
const CONFIG = {
    API_BASE: window.location.origin,
    REFRESH_INTERVAL: 30000, // 30 seconds
    ENDPOINTS: {
        HEALTH: '/health',
        COMMAND_QUEUE: '/api/command-queue',
        TODAY: '/api/command-queue/today',
        SIGNALS: '/api/signals',
        OUTCOMES: '/api/outcomes/stats',
        ACTIONS: '/api/actions/execute',
    }
};

// CSRF Token (fetched from server response header)
let csrfToken = null;

// State
let state = {
    moves: [],
    signals: [],
    history: [],
    stats: {},
    selectedMoveId: null,
    selectedMoveIndex: 0,
    domain: 'all',
    isHealthy: false,
    isLoading: true,
    refreshTimer: null,
};

// DOM References
const elements = {};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', init);

// Fetch CSRF token on page load
async function fetchCsrfToken() {
    try {
        const response = await fetch('/health');
        csrfToken = response.headers.get('X-CSRF-Token');
        console.log('[CaseyOS] CSRF token loaded');
    } catch (err) {
        console.error('[CaseyOS] Failed to fetch CSRF token:', err);
    }
}

// Helper for POST/PUT/DELETE requests with CSRF
async function apiCall(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    // Add CSRF token for state-changing requests
    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method.toUpperCase())) {
        if (csrfToken) {
            options.headers['X-CSRF-Token'] = csrfToken;
        }
    }
    
    if (body) {
        options.body = JSON.stringify(body);
    }
    
    const response = await fetch(endpoint, options);
    
    // Update CSRF token from response if present
    const newToken = response.headers.get('X-CSRF-Token');
    if (newToken) {
        csrfToken = newToken;
    }
    
    return response;
}

async function init() {
    cacheElements();
    setupEventListeners();
    setupKeyboardShortcuts();
    loadTheme();
    
    // Fetch CSRF token first
    await fetchCsrfToken();

    // Initial data fetch
    await Promise.all([
        checkHealth(),
        fetchTodaysMoves(),
        fetchSignals(),
        fetchOutcomeStats(),
        fetchExecutionHistory(),
    ]);

    // Start refresh loop
    startRefreshLoop();

    console.log('🚀 CaseyOS Dashboard initialized');
}

function cacheElements() {
    elements.healthIndicator = document.querySelector('.health-indicator');
    elements.healthDot = document.querySelector('.health-dot');
    elements.healthText = document.querySelector('.health-text');
    elements.navTabs = document.querySelectorAll('.nav-tab');
    elements.movesList = document.getElementById('moves-list');
    elements.signalsList = document.getElementById('signals-list');
    elements.historyList = document.getElementById('history-list');
    elements.funnelChart = document.getElementById('funnel-chart');
    elements.quickActions = document.getElementById('quick-actions');
    elements.modal = document.getElementById('execute-modal');
    elements.modalTitle = document.querySelector('.modal-header h3');
    elements.modalBody = document.querySelector('.modal-body');
    elements.toastContainer = document.getElementById('toast-container');
    elements.themeToggle = document.getElementById('dark-mode-toggle');
    elements.refreshBtn = document.getElementById('btn-refresh');

    // Stats
    elements.statPending = document.getElementById('stat-pending');
    elements.statCompleted = document.getElementById('stat-completed');
    elements.statReplyRate = document.getElementById('stat-reply-rate');
    elements.statNetImpact = document.getElementById('stat-net-impact');
    elements.statSignals = document.getElementById('stat-signals');
}

function setupEventListeners() {
    // Domain tabs
    elements.navTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const domain = tab.dataset.domain;
            setActiveDomain(domain);
        });
    });

    // Theme toggle
    elements.themeToggle?.addEventListener('click', toggleTheme);

    // Refresh button
    elements.refreshBtn?.addEventListener('click', loadMoves);

    // Modal close
    document.querySelector('.modal-backdrop')?.addEventListener('click', closeModal);
    document.querySelector('.btn-close')?.addEventListener('click', closeModal);

    // Modal buttons
    document.getElementById('btn-preview')?.addEventListener('click', handlePreview);
    document.getElementById('btn-execute')?.addEventListener('click', handleExecute);

    // Quick action buttons
    document.querySelectorAll('.quick-actions .btn-action').forEach(btn => {
        btn.addEventListener('click', handleQuickAction);
    });
}

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ignore if modal is open or in input
        if (elements.modal.classList.contains('active')) {
            if (e.key === 'Escape') closeModal();
            return;
        }
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        switch (e.key.toLowerCase()) {
            case 'a':
                e.preventDefault();
                handleAcceptCurrent();
                break;
            case 'd':
                e.preventDefault();
                handleDismissCurrent();
                break;
            case 'e':
                e.preventDefault();
                handleExecuteCurrent();
                break;
            case 'r':
                e.preventDefault();
                refreshAll();
                showToast('Refreshed', 'success');
                break;
            case 'arrowdown':
            case 'j':
                e.preventDefault();
                selectNextMove();
                break;
            case 'arrowup':
            case 'k':
                e.preventDefault();
                selectPrevMove();
                break;
        }
    });
}

// === API Functions ===

async function checkHealth() {
    try {
        const res = await fetch(CONFIG.ENDPOINTS.HEALTH);
        const data = await res.json();
        state.isHealthy = data.status === 'ok';
        updateHealthIndicator();
    } catch (err) {
        state.isHealthy = false;
        updateHealthIndicator();
        console.error('Health check failed:', err);
    }
}

async function fetchTodaysMoves() {
    try {
        const url = state.domain === 'all'
            ? CONFIG.ENDPOINTS.TODAY
            : `${CONFIG.ENDPOINTS.TODAY}?domain=${state.domain}`;

        const res = await fetch(url);
        if (!res.ok) throw new Error('Failed to fetch moves');

        const data = await res.json();
        state.moves = data.items || data.today_moves || [];
        state.stats.pending = data.total || state.moves.length;

        renderMovesList();
        updateStats();

        // Select first move if none selected
        if (state.moves.length > 0 && !state.selectedMoveId) {
            selectMove(state.moves[0].id, 0);
        }
    } catch (err) {
        console.error('Failed to fetch moves:', err);
        renderEmptyState(elements.movesList, 'Unable to load Today\'s Moves');
    }
}

async function fetchSignals() {
    try {
        const res = await fetch(`${CONFIG.ENDPOINTS.SIGNALS}?limit=10`);
        if (!res.ok) throw new Error('Failed to fetch signals');

        const data = await res.json();
        state.signals = data.signals || data.items || [];
        state.stats.signalsToday = data.total || state.signals.length;

        renderSignalsList();
        updateStats();
    } catch (err) {
        console.error('Failed to fetch signals:', err);
        renderEmptyState(elements.signalsList, 'No signals yet');
    }
}

async function fetchOutcomeStats() {
    try {
        const res = await fetch(CONFIG.ENDPOINTS.OUTCOMES);
        if (!res.ok) throw new Error('Failed to fetch outcomes');

        const data = await res.json();
        state.stats.replyRate = data.reply_rate || 0;
        state.stats.netImpact = data.net_impact || 0;
        state.stats.completed = data.total_outcomes || 0;
        state.stats.funnel = {
            sent: data.by_type?.email_sent || 0,
            opened: data.by_type?.email_opened || 0,
            replied: data.by_type?.email_replied || 0,
            booked: data.by_type?.meeting_booked || 0,
        };

        updateStats();
        renderFunnelChart();
    } catch (err) {
        console.error('Failed to fetch outcomes:', err);
    }
}

async function fetchExecutionHistory() {
    try {
        const res = await fetch(`${CONFIG.ENDPOINTS.COMMAND_QUEUE}?status=completed&limit=10`);
        if (!res.ok) throw new Error('Failed to fetch history');

        const data = await res.json();
        state.history = data.items || [];

        renderHistoryList();
    } catch (err) {
        console.error('Failed to fetch history:', err);
        renderEmptyState(elements.historyList, 'No history yet');
    }
}

async function acceptMove(id, buttonElement = null) {
    setButtonLoading(buttonElement, true);
    try {
        const res = await apiCall(`${CONFIG.ENDPOINTS.COMMAND_QUEUE}/${id}/accept`, 'POST');
        if (!res.ok) throw new Error('Failed to accept');

        showToast('Move accepted', 'success');
        await fetchTodaysMoves();
    } catch (err) {
        console.error('Failed to accept move:', err);
        showToast('Failed to accept', 'error');
        setButtonLoading(buttonElement, false);
    }
}

async function dismissMove(id, buttonElement = null) {
    setButtonLoading(buttonElement, true);
    try {
        const res = await apiCall(`${CONFIG.ENDPOINTS.COMMAND_QUEUE}/${id}/dismiss`, 'POST');
        if (!res.ok) throw new Error('Failed to dismiss');

        showToast('Move dismissed', 'warning');
        await fetchTodaysMoves();
    } catch (err) {
        console.error('Failed to dismiss move:', err);
        showToast('Failed to dismiss', 'error');
        setButtonLoading(buttonElement, false);
    }
}

async function executeMove(id, dryRun = false, buttonElement = null) {
    setButtonLoading(buttonElement, true);
    try {
        const res = await apiCall(CONFIG.ENDPOINTS.ACTIONS, 'POST', {
            queue_item_id: id,
            dry_run: dryRun,
        });

        const data = await res.json();

        if (dryRun) {
            // Show preview
            setButtonLoading(buttonElement, false);
            showPreview(data);
        } else {
            if (!res.ok) throw new Error(data.detail || 'Execution failed');
            showToast('Action executed!', 'success');
            await Promise.all([fetchTodaysMoves(), fetchExecutionHistory()]);
        }
    } catch (err) {
        console.error('Failed to execute:', err);
        showToast(err.message || 'Execution failed', 'error');
        setButtonLoading(buttonElement, false);
    }
}

// === Render Functions ===

function renderMovesList() {
    if (!elements.movesList) return;

    if (state.moves.length === 0) {
        renderEmptyState(elements.movesList, 'All caught up! No moves pending.');
        return;
    }

    const html = state.moves.map((move, idx) => {
        const priorityClass = move.aps_score >= 70 ? 'high' : move.aps_score >= 40 ? 'medium' : 'low';
        const isSelected = move.id === state.selectedMoveId;
        const domain = move.domain || 'sales';

        return `
      <div class="move-item ${isSelected ? 'selected' : ''}" 
           data-id="${move.id}" 
           data-index="${idx}"
           onclick="selectMove('${move.id}', ${idx})">
        <div class="move-priority ${priorityClass}">${Math.round(move.aps_score)}</div>
        <div class="move-content">
          <div class="move-title">
            ${escapeHtml(move.action_type?.replace(/_/g, ' '))}
            ${move.action_context?.recipient ? ` → ${escapeHtml(move.action_context.recipient)}` : ''}
            <span class="domain-badge ${domain}">${domain}</span>
          </div>
          <div class="move-meta">
            <span>${move.owner || 'casey'}</span>
            ${move.due_by ? `<span>Due: ${formatDate(move.due_by)}</span>` : ''}
          </div>
          ${move.reasoning ? `<div class="move-reasoning">${escapeHtml(move.reasoning)}</div>` : ''}
        </div>
        <div class="move-actions">
          <button class="btn-sm btn-success" onclick="event.stopPropagation(); acceptMove('${move.id}')" title="Accept (A)">✓</button>
          <button class="btn-sm btn-secondary" onclick="event.stopPropagation(); dismissMove('${move.id}')" title="Dismiss (D)">✕</button>
          <button class="btn-sm btn-primary" onclick="event.stopPropagation(); openExecuteModal('${move.id}')" title="Execute (E)">▶</button>
        </div>
      </div>
    `;
    }).join('');

    elements.movesList.innerHTML = html;
}

function renderSignalsList() {
    if (!elements.signalsList) return;

    if (state.signals.length === 0) {
        renderEmptyState(elements.signalsList, 'No recent signals');
        return;
    }

    const icons = {
        form: '📝',
        hubspot: '🔶',
        gmail: '✉️',
        deal: '💰',
        meeting: '📅',
        default: '📡',
    };

    const html = state.signals.map(signal => `
    <div class="signal-item">
      <span class="signal-icon">${icons[signal.source] || icons.default}</span>
      <span class="signal-text">${escapeHtml(signal.signal_type?.replace(/_/g, ' ') || 'Signal')}</span>
      <span class="signal-time">${timeAgo(signal.created_at)}</span>
    </div>
  `).join('');

    elements.signalsList.innerHTML = html;
}

function renderHistoryList() {
    if (!elements.historyList) return;

    if (state.history.length === 0) {
        renderEmptyState(elements.historyList, 'No executed actions yet');
        return;
    }

    const html = state.history.slice(0, 5).map(item => {
        const status = item.status === 'completed' ? 'success' : item.status === 'failed' ? 'failed' : 'pending';

        return `
      <div class="history-item">
        <span class="history-status ${status}"></span>
        <span class="history-text">${escapeHtml(item.action_type?.replace(/_/g, ' '))}</span>
        <span class="history-time">${timeAgo(item.executed_at || item.updated_at)}</span>
      </div>
    `;
    }).join('');

    elements.historyList.innerHTML = html;
}

function renderFunnelChart() {
    if (!elements.funnelChart) return;

    const funnel = state.stats.funnel || { sent: 0, opened: 0, replied: 0, booked: 0 };
    const max = Math.max(funnel.sent, 1);

    const stages = [
        { label: 'Sent', value: funnel.sent },
        { label: 'Opened', value: funnel.opened },
        { label: 'Replied', value: funnel.replied },
        { label: 'Booked', value: funnel.booked },
    ];

    const html = stages.map(stage => {
        const width = (stage.value / max) * 100;
        return `
      <div class="funnel-stage">
        <span class="funnel-label">${stage.label}</span>
        <div class="funnel-bar ${stage.label === 'Booked' ? 'positive' : ''}" style="width: ${width}%"></div>
        <span class="funnel-value">${stage.value}</span>
      </div>
    `;
    }).join('');

    elements.funnelChart.innerHTML = html;
}

function updateStats() {
    if (elements.statPending) elements.statPending.textContent = state.stats.pending || 0;
    if (elements.statCompleted) elements.statCompleted.textContent = state.stats.completed || 0;
    if (elements.statReplyRate) {
        const rate = (state.stats.replyRate * 100) || 0;
        elements.statReplyRate.textContent = rate.toFixed(0) + '%';
    }
    if (elements.statNetImpact) {
        const impact = state.stats.netImpact || 0;
        elements.statNetImpact.textContent = (impact >= 0 ? '+' : '') + impact;
        elements.statNetImpact.className = `stat-value ${impact >= 0 ? 'positive' : 'negative'}`;
    }
    if (elements.statSignals) elements.statSignals.textContent = state.stats.signalsToday || 0;
}

function updateHealthIndicator() {
    if (!elements.healthDot) return;

    elements.healthDot.className = `health-dot ${state.isHealthy ? 'healthy' : 'error'}`;
    if (elements.healthText) {
        elements.healthText.textContent = state.isHealthy ? 'Healthy' : 'Error';
    }
}

function renderEmptyState(container, message) {
    if (!container) return;

    container.innerHTML = `
    <div class="empty-state">
      <div class="empty-state-icon">📭</div>
      <div class="empty-state-text">${escapeHtml(message)}</div>
    </div>
  `;
}

function renderLoading(container) {
    if (!container) return;

    container.innerHTML = `
    <div class="skeleton-loader">
      <div class="skeleton-item"></div>
      <div class="skeleton-item"></div>
      <div class="skeleton-item"></div>
    </div>
  `;
}

// === Action Handlers ===

function selectMove(id, index) {
    state.selectedMoveId = id;
    state.selectedMoveIndex = index;

    // Update UI selection
    document.querySelectorAll('.move-item').forEach((el, i) => {
        el.classList.toggle('selected', el.dataset.id === id);
    });
}

function selectNextMove() {
    if (state.moves.length === 0) return;
    const newIndex = Math.min(state.selectedMoveIndex + 1, state.moves.length - 1);
    selectMove(state.moves[newIndex].id, newIndex);
    scrollToSelected();
}

function selectPrevMove() {
    if (state.moves.length === 0) return;
    const newIndex = Math.max(state.selectedMoveIndex - 1, 0);
    selectMove(state.moves[newIndex].id, newIndex);
    scrollToSelected();
}

function scrollToSelected() {
    const selected = document.querySelector('.move-item.selected');
    if (selected) {
        selected.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function handleAcceptCurrent() {
    if (state.selectedMoveId) {
        acceptMove(state.selectedMoveId);
    }
}

function handleDismissCurrent() {
    if (state.selectedMoveId) {
        dismissMove(state.selectedMoveId);
    }
}

function handleExecuteCurrent() {
    if (state.selectedMoveId) {
        openExecuteModal(state.selectedMoveId);
    }
}

function setActiveDomain(domain) {
    state.domain = domain;

    elements.navTabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.domain === domain);
    });

    fetchTodaysMoves();
}

function handleQuickAction(e) {
    const action = e.currentTarget.dataset.action;

    switch (action) {
        case 'refresh':
            refreshAll();
            showToast('Refreshed', 'success');
            break;
        case 'pause':
            pauseRefresh();
            showToast('Auto-refresh paused', 'warning');
            break;
        case 'dismiss-all':
            if (confirm('Dismiss all pending moves?')) {
                dismissAllMoves();
            }
            break;
    }
}

async function dismissAllMoves() {
    try {
        await Promise.all(state.moves.map(m => dismissMove(m.id)));
        await fetchTodaysMoves();
        showToast('All moves dismissed', 'warning');
    } catch (err) {
        showToast('Failed to dismiss all', 'error');
    }
}

// === Modal Functions ===

function openExecuteModal(id) {
    state.selectedMoveId = id;
    const move = state.moves.find(m => m.id === id);

    if (!move) return;

    if (elements.modalTitle) {
        elements.modalTitle.textContent = `Execute: ${move.action_type?.replace(/_/g, ' ')}`;
    }

    if (elements.modalBody) {
        elements.modalBody.innerHTML = `
      <p><strong>Action:</strong> ${escapeHtml(move.action_type)}</p>
      ${move.action_context?.recipient ? `<p><strong>Recipient:</strong> ${escapeHtml(move.action_context.recipient)}</p>` : ''}
      ${move.reasoning ? `<p><strong>Reasoning:</strong> ${escapeHtml(move.reasoning)}</p>` : ''}
      <p><strong>APS Score:</strong> ${Math.round(move.aps_score)}</p>
      <div id="preview-content" style="margin-top: 1rem;"></div>
    `;
    }

    elements.modal.classList.add('active');
}

function closeModal() {
    elements.modal.classList.remove('active');
}

function handlePreview() {
    if (state.selectedMoveId) {
        executeMove(state.selectedMoveId, true);
    }
}

function handleExecute() {
    if (state.selectedMoveId) {
        executeMove(state.selectedMoveId, false);
        closeModal();
    }
}

function showPreview(data) {
    const container = document.getElementById('preview-content');
    if (!container) return;

    container.innerHTML = `
    <div style="background: var(--gray-100); padding: 1rem; border-radius: var(--border-radius);">
      <h4 style="margin-bottom: 0.5rem;">Preview:</h4>
      <pre style="white-space: pre-wrap; font-size: 0.875rem;">${escapeHtml(JSON.stringify(data.preview || data, null, 2))}</pre>
    </div>
  `;
}

// === Toast Functions ===

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// === Theme Functions ===

function loadTheme() {
    const theme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', theme);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';

    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
}

// === Refresh Loop ===

function startRefreshLoop() {
    state.refreshTimer = setInterval(refreshAll, CONFIG.REFRESH_INTERVAL);
}

function pauseRefresh() {
    if (state.refreshTimer) {
        clearInterval(state.refreshTimer);
        state.refreshTimer = null;
    }
}

function refreshAll() {
    checkHealth();
    fetchTodaysMoves();
    fetchSignals();
    fetchOutcomeStats();
}

// === Utility Functions ===

// Loading state helper for buttons
function setButtonLoading(buttonElement, isLoading, originalText = null) {
    if (!buttonElement) return;
    
    if (isLoading) {
        buttonElement.dataset.originalText = buttonElement.textContent;
        buttonElement.textContent = 'Loading...';
        buttonElement.disabled = true;
        buttonElement.classList.add('loading');
    } else {
        buttonElement.textContent = originalText || buttonElement.dataset.originalText || 'Done';
        buttonElement.disabled = false;
        buttonElement.classList.remove('loading');
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function formatDate(dateStr) {
    if (!dateStr) return '';

    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = date - now;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffHours < 0) {
        return 'Overdue';
    } else if (diffHours < 1) {
        return 'Soon';
    } else if (diffHours < 24) {
        return `${diffHours}h`;
    } else {
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}d`;
    }
}

function timeAgo(dateStr) {
    if (!dateStr) return '';

    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMinutes = Math.floor(diffMs / (1000 * 60));

    if (diffMinutes < 1) return 'now';
    if (diffMinutes < 60) return `${diffMinutes}m`;

    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h`;

    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d`;
}

// Global function exports for onclick handlers
window.selectMove = selectMove;
window.acceptMove = acceptMove;
window.dismissMove = dismissMove;
window.openExecuteModal = openExecuteModal;
