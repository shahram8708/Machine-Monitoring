(() => {
  const cfg = window.SUBSCRIPTION_PAGE || {};
  const headers = cfg.accessToken ? { Authorization: `Bearer ${cfg.accessToken}` } : {};
  const charts = {};
  const state = { plans: [], currentPlan: null, usage: {}, history: [] };
  const qs = (id) => document.getElementById(id);

  const hide = (el) => el && el.classList.add('d-none');
  const show = (el) => el && el.classList.remove('d-none');
  const setText = (id, value) => { const el = qs(id); if (el) el.textContent = value; };

  const fetchJson = async (url, opts = {}) => {
    const resp = await fetch(url, { credentials: 'include', headers: { ...headers, ...(opts.headers || {}), 'Content-Type': 'application/json' }, ...opts });
    if (!resp.ok) throw new Error(`Request failed ${resp.status}`);
    return resp.json();
  };

  const showError = (msg) => {
    const box = qs('subscription-error');
    if (!box) return;
    box.textContent = msg;
    show(box);
  };

  const formatDate = (iso) => {
    if (!iso) return '--';
    const d = new Date(iso);
    return isNaN(d.getTime()) ? '--' : d.toLocaleDateString();
  };

  const renderStatus = (data) => {
    state.currentPlan = data?.plan || null;
    setText('plan-name', data?.plan || 'Not subscribed');
    setText('billing-cycle', data?.status || 'Inactive');
    setText('plan-ends', formatDate(data?.ends_at));
    const countdown = data?.ends_at ? Math.max(0, Math.ceil((new Date(data.ends_at) - new Date()) / (1000 * 60 * 60 * 24))) : null;
    setText('expiry-countdown', countdown !== null ? `${countdown} days` : '--');
    const badge = qs('plan-status');
    if (badge) {
      badge.className = 'badge bg-' + (data?.active ? 'success' : 'secondary');
      badge.textContent = data?.status || 'INACTIVE';
    }
    setText('last-payment', `Last payment: ${formatDate(data?.last_payment)}`);
    const razor = qs('razorpay-status');
    if (razor) {
      razor.className = 'badge bg-' + (data?.active ? 'success' : 'secondary');
      razor.textContent = data?.status || 'Unknown';
    }
  };

  const progress = (used, limit) => {
    if (!limit || limit <= 0) return 0;
    return Math.min(100, Math.round((used / limit) * 100));
  };

  const renderUsage = () => {
    const plan = state.plans.find((p) => p.name === state.currentPlan);
    const usage = state.usage || {};
    const machineUsed = cfg.machineCount || 0;
    const aiUsed = usage.ai_predictions || 0;
    const apiUsed = usage.api_calls || 0;
    const reportsUsed = usage.report_generation || 0;

    const machinesLimit = plan?.max_machines || 0;
    const aiLimit = plan?.ai_prediction_limit || 0;

    setText('machines-usage', `${machineUsed} used`);
    setText('machines-limit', machinesLimit ? `${machinesLimit} limit` : 'Unlimited');
    setText('ai-usage', `${aiUsed} used`);
    setText('ai-limit', aiLimit ? `${aiLimit} limit` : 'Unlimited');
    setText('api-usage', `${apiUsed} calls`);
    setText('reports-usage', `${reportsUsed} generated`);
    setText('reports-limit', plan ? 'Per plan rules' : '--');

    const setBar = (id, used, limit, colorId) => {
      const el = qs(id);
      if (!el) return;
      el.style.width = `${progress(used, limit || used || 1)}%`;
      el.classList.toggle('bg-danger', limit && used > limit);
    };
    setBar('machines-progress', machineUsed, machinesLimit);
    setBar('ai-progress', aiUsed, aiLimit);
    setBar('api-progress', apiUsed, apiUsed || 1);
    setBar('reports-progress', reportsUsed, reportsUsed || 1);

    setText('usage-updated', `Updated ${new Date().toLocaleTimeString()}`);
  };

  const renderPlans = () => {
    const tbody = qs('plan-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    state.plans.forEach((p) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${p.name}</td>
        <td>${p.max_machines ?? '—'}</td>
        <td>${p.ai_prediction_limit ?? '—'}</td>
        <td><span class="badge bg-${p.advanced_reports_enabled ? 'success' : 'secondary'}">${p.advanced_reports_enabled ? 'On' : 'Off'}</span></td>
        <td><span class="badge bg-${p.digital_twin_enabled ? 'success' : 'secondary'}">${p.digital_twin_enabled ? 'On' : 'Off'}</span></td>
        <td><span class="badge bg-${p.workforce_analytics_enabled ? 'success' : 'secondary'}">${p.workforce_analytics_enabled ? 'On' : 'Off'}</span></td>
        <td>$${(p.price_monthly || 0).toFixed(2)}</td>
        <td>$${(p.price_yearly || 0).toFixed(2)}</td>
        <td><button class="btn btn-sm btn-outline-primary" data-plan="${p.name}">Select</button></td>`;
      tbody.appendChild(tr);
    });
    tbody.querySelectorAll('button[data-plan]').forEach((btn) => {
      btn.addEventListener('click', () => startPlan(btn.dataset.plan));
    });
  };

  const updateFeatures = () => {
    const plan = state.plans.find((p) => p.name === state.currentPlan);
    const setBadge = (id, enabled) => {
      const el = qs(id);
      if (!el) return;
      el.className = `badge bg-${enabled ? 'success' : 'secondary'}`;
      el.textContent = enabled ? 'Enabled' : 'Disabled';
    };
    setBadge('feature-advanced-reports', !!plan?.advanced_reports_enabled);
    setBadge('feature-digital-twin', !!plan?.digital_twin_enabled);
    setBadge('feature-workforce', !!plan?.workforce_analytics_enabled);
  };

  const buildChart = (id, config) => {
    const ctx = qs(id);
    if (!ctx) return;
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(ctx, config);
  };

  const renderHistory = () => {
    const hist = state.history || [];
    hide(qs('usage-spinner'));
    hide(qs('api-spinner'));
    if (!hist.length) return;
    const dates = Array.from(new Set(hist.map((h) => h.date))).sort();
    const aggregate = (metric) => dates.map((d) => hist.filter((h) => h.date === d && h.metric === metric).reduce((sum, h) => sum + h.count, 0));

    buildChart('usage-trend-chart', {
      type: 'line',
      data: {
        labels: dates,
        datasets: [
          { label: 'AI Predictions', data: aggregate('ai_predictions'), borderColor: '#0d6efd', backgroundColor: '#0d6efd33', tension: 0.3 },
          { label: 'Reports', data: aggregate('report_generation'), borderColor: '#ffc107', backgroundColor: '#ffc10733', tension: 0.3 },
          { label: 'Digital Twin', data: aggregate('digital_twin_simulation'), borderColor: '#6610f2', backgroundColor: '#6610f233', tension: 0.3 },
        ],
      },
      options: { responsive: true, maintainAspectRatio: false },
    });

    buildChart('api-usage-chart', {
      type: 'bar',
      data: { labels: dates, datasets: [{ label: 'API Calls', data: aggregate('api_calls'), backgroundColor: '#0dcaf0' }] },
      options: { responsive: true, maintainAspectRatio: false },
    });
  };

  const loadStatus = async () => {
    const data = await fetchJson(cfg.endpoints.status);
    renderStatus(data || {});
  };

  const loadPlans = async () => {
    const data = await fetchJson(cfg.endpoints.plans);
    state.plans = Array.isArray(data) ? data : [];
    renderPlans();
    updateFeatures();
    renderUsage();
  };

  const loadUsage = async () => {
    const usage = await fetchJson(cfg.endpoints.usage);
    state.usage = usage || {};
    renderUsage();
  };

  const loadHistory = async () => {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 30);
    const url = `${cfg.endpoints.usageHistory}?start_date=${start.toISOString().slice(0, 10)}&end_date=${end.toISOString().slice(0, 10)}`;
    const history = await fetchJson(url);
    state.history = Array.isArray(history) ? history : [];
    renderHistory();
  };

  const startPlan = async (planName) => {
    if (!planName) return;
    try {
      qs('upgrade-btn').disabled = true;
      await fetchJson(cfg.endpoints.start, { method: 'POST', body: JSON.stringify({ plan_name: planName }) });
      await Promise.all([loadStatus(), loadPlans()]);
    } catch (err) {
      showError(err.message);
    } finally {
      qs('upgrade-btn').disabled = false;
    }
  };

  const bindEvents = () => {
    const refresh = () => Promise.all([loadStatus(), loadUsage(), loadHistory(), loadPlans()]).catch((e) => showError(e.message));
    qs('refresh-subscription')?.addEventListener('click', refresh);
    qs('upgrade-btn')?.addEventListener('click', () => startPlan(state.plans[1]?.name || state.currentPlan));
    qs('cancel-btn')?.addEventListener('click', () => showError('Cancel flow is handled via billing gateway. Contact support.'));
  };

  const init = async () => {
    try {
      bindEvents();
      await Promise.all([loadStatus(), loadUsage(), loadHistory(), loadPlans()]);
    } catch (err) {
      showError(err.message);
    }
  };

  document.addEventListener('DOMContentLoaded', init);
})();
