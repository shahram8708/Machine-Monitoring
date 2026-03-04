(() => {
  const cfg = window.RCA_CONFIG || {};
  const headers = cfg.accessToken ? { Authorization: `Bearer ${cfg.accessToken}` } : {};
  const charts = {};
  const qs = (id) => document.getElementById(id);

  const fetchJson = async (url) => {
    // Avoid sending cookies to prevent JWT CSRF 422s; rely on Authorization header instead.
    const resp = await fetch(url, { credentials: 'omit', headers });
    if (!resp.ok) throw new Error(`Request failed ${resp.status}`);
    return resp.json();
  };

  const showError = (msg) => {
    const el = qs('rca-error');
    if (!el) return;
    el.textContent = msg;
    el.classList.remove('d-none');
  };

  const buildChart = (id, config) => {
    const ctx = qs(id);
    if (!ctx) return;
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(ctx, config);
  };

  const normalizeItems = (items) => {
    if (Array.isArray(items)) return items;
    if (items && typeof items === 'object') {
      return Object.entries(items).map(([label, value]) => ({ label, value }));
    }
    return [];
  };

  const toPercentScale = (values) => {
    const nums = values.map((v) => Number(v) || 0);
    const finite = nums.filter((v) => Number.isFinite(v));
    if (!finite.length) return nums;
    const maxVal = Math.max(...finite);
    return maxVal <= 1 ? nums.map((v) => v * 100) : nums;
  };

  const renderProbability = (items) => {
    const normalized = normalizeItems(items);
    const labels = normalized.map((i) => i.cause || i.label || 'Cause');
    const values = toPercentScale(normalized.map((i) => i.probability ?? i.value ?? 0));
    const palette = ['#0d6efd', '#6610f2', '#198754', '#fd7e14', '#dc3545', '#20c997'];
    buildChart('probability-chart', {
      type: 'bar',
      data: { labels, datasets: [{ label: 'Probability %', data: values, backgroundColor: values.map((_, idx) => palette[idx % palette.length]) }] },
      options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, suggestedMax: Math.max(100, ...values) } } },
    });
  };

  const renderDistribution = (items) => {
    const normalized = normalizeItems(items);
    const labels = normalized.map((i) => i.cause || i.label || 'Cause');
    const values = toPercentScale(normalized.map((i) => i.probability ?? i.value ?? 0));
    const palette = ['#0d6efd', '#6f42c1', '#20c997', '#ffc107', '#dc3545'];
    buildChart('rca-pie', {
      type: 'pie',
      data: { labels, datasets: [{ data: values, backgroundColor: labels.map((_, idx) => palette[idx % palette.length]) }] },
      options: { responsive: true, maintainAspectRatio: false },
    });
    document.getElementById('rca-dist-spinner')?.classList.add('d-none');
  };

  const renderFactors = (list) => {
    const ul = qs('factors-list');
    if (!ul) return;
    ul.innerHTML = '';
    if (!list || !list.length) {
      ul.innerHTML = '<li class="list-group-item text-muted">No contributing factors.</li>';
      return;
    }
    list.forEach((f) => {
      const li = document.createElement('li');
      li.className = 'list-group-item';
      li.textContent = f;
      ul.appendChild(li);
    });
  };

  const renderSummary = (rca) => {
    qs('primary-root-cause').textContent = rca.primary_root_cause || '--';
    qs('confidence-score').textContent = rca.confidence_score ? `${(rca.confidence_score * 100).toFixed(1)}%` : '--';
    qs('escalation-status').textContent = 'Based on alerts';
    qs('rca-updated').textContent = rca.created_at ? new Date(rca.created_at).toLocaleString() : '--';
  };

  const renderTimeline = (alerts) => {
    const container = qs('timeline-view');
    if (!container) return;
    container.innerHTML = '';
    if (!alerts.length) {
      container.innerHTML = '<div class="text-muted">No alert timeline available.</div>';
      return;
    }
    alerts
      .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
      .forEach((a) => {
        const div = document.createElement('div');
        div.className = 'mb-3 border-start ps-3';
        div.innerHTML = `
          <div class="fw-semibold">${a.alert_type || 'Alert'} • ${a.severity || 'NA'}</div>
          <div class="small text-muted">${a.created_at ? new Date(a.created_at).toLocaleString() : '--'}</div>
          <div class="small">Status: ${a.status}</div>`;
        container.appendChild(div);
      });
  };

  const renderTable = (rca) => {
    const tbody = qs('rca-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!rca) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No RCA records.</td></tr>';
      return;
    }
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${rca.id}</td>
      <td>${rca.machine_id}</td>
      <td>${rca.primary_root_cause || '--'}</td>
      <td>${rca.confidence_score ? (rca.confidence_score * 100).toFixed(1) + '%' : '--'}</td>
      <td>${rca.created_at ? new Date(rca.created_at).toLocaleString() : '--'}</td>`;
    tbody.appendChild(tr);
  };

  const loadAlerts = async (machineId, groupId) => {
    const url = cfg.endpoints.alerts;
    const params = [];
    if (groupId) params.push(`group_id=${groupId}`);
    const fullUrl = params.length ? `${url}?${params.join('&')}` : url;
    const alerts = await fetchJson(fullUrl);
    return (alerts || []).filter((a) => !machineId || a.machine_id === Number(machineId));
  };

  const loadRca = async () => {
    try {
      const machineId = qs('machine-select')?.value;
      const groupId = qs('group-id')?.value;
      if (!machineId && !groupId) return showError('Select a machine or provide an alert group ID.');
      document.getElementById('rca-prob-spinner')?.classList.remove('d-none');
      const rcaUrl = groupId ? cfg.endpoints.group.replace('/0', `/${groupId}`) : cfg.endpoints.machine.replace('/0', `/${machineId}`);
      const rca = await fetchJson(rcaUrl);
      renderSummary(rca);
      renderFactors(rca.contributing_factors || []);
      renderProbability(rca.probability_breakdown || []);
      renderDistribution(rca.probability_breakdown || []);
      renderTable(rca);

      const alerts = await loadAlerts(rca.machine_id, groupId);
      renderTimeline(alerts || []);
      if (alerts && alerts.length) {
        qs('escalation-status').textContent = alerts[0].status || 'Open';
      }
    } catch (err) {
      showError(err.message);
    } finally {
      document.getElementById('rca-prob-spinner')?.classList.add('d-none');
    }
  };

  const bindEvents = () => {
    qs('rca-apply')?.addEventListener('click', () => loadRca());
  };

  document.addEventListener('DOMContentLoaded', () => {
    bindEvents();
  });
})();
