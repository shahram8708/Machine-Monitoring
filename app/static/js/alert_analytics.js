(() => {
  const cfg = window.ALERT_ANALYTICS_CONFIG || {};
  const headers = cfg.accessToken ? { Authorization: `Bearer ${cfg.accessToken}` } : {};
  const charts = {};
  const qs = (id) => document.getElementById(id);

  const fetchJson = async (url) => {
    // Avoid cookie-based CSRF issues; rely on Authorization header.
    const resp = await fetch(url, { credentials: 'omit', headers });
    if (!resp.ok) throw new Error(`Request failed ${resp.status}`);
    return resp.json();
  };

  const showError = (msg) => {
    const el = qs('alert-error');
    if (!el) return;
    el.textContent = msg;
    el.classList.remove('d-none');
  };

  const setText = (id, val) => { const el = qs(id); if (el) el.textContent = val; };
  const hideSpinner = (id) => { const el = qs(id); if (el) el.classList.add('d-none'); };

  const buildChart = (id, config) => {
    const ctx = qs(id);
    if (!ctx) return;
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(ctx, config);
  };

  const buildUrl = () => {
    const params = new URLSearchParams();
    const start = qs('start-date')?.value;
    const end = qs('end-date')?.value;
    const plant = qs('plant-filter')?.value;
    if (start) params.append('start_date', start);
    if (end) params.append('end_date', end);
    if (plant) params.append('plant_id', plant);
    return `${cfg.endpoints.analytics}?${params.toString()}`;
  };

  const renderKpis = (data) => {
    setText('kpi-total', data.total_alerts ?? '--');
    setText('kpi-open', data.open_alerts ?? '--');
    setText('kpi-sla', data.sla_breach_count ?? '--');
    const avgRes = data.average_resolution_minutes;
    setText('kpi-resolution', Number.isFinite(avgRes) ? `${avgRes.toFixed(1)} min` : '--');
  };

  const renderDaily = (items) => {
    hideSpinner('daily-spinner');
    const labels = items.map((i) => i.date);
    const values = items.map((i) => i.count);
    buildChart('alerts-daily', {
      type: 'line',
      data: { labels, datasets: [{ label: 'Alerts', data: values, borderColor: '#0d6efd', backgroundColor: '#0d6efd33', tension: 0.3 }] },
      options: { responsive: true, maintainAspectRatio: false },
    });
  };

  const renderSeverity = (dist) => {
    hideSpinner('severity-spinner');
    const entries = Object.entries(dist || {});
    const labels = entries.map(([k]) => k);
    const values = entries.map(([, v]) => v);
    buildChart('severity-chart', {
      type: 'bar',
      data: { labels, datasets: [{ label: 'Count', data: values, backgroundColor: ['#dc3545', '#fd7e14', '#ffc107', '#0d6efd'] }] },
      options: { responsive: true, maintainAspectRatio: false },
    });
  };

  const renderSla = (sla) => {
    hideSpinner('sla-spinner');
    const labels = ['Resolved', 'Breached', 'Open'];
    const values = [sla?.resolved || 0, sla?.breached || 0, sla?.open || 0];
    buildChart('sla-chart', {
      type: 'doughnut',
      data: { labels, datasets: [{ data: values, backgroundColor: ['#198754', '#dc3545', '#6c757d'] }] },
      options: { responsive: true, maintainAspectRatio: false },
    });
  };

  const renderTech = (perf) => {
    hideSpinner('tech-spinner');
    const labels = Object.keys(perf || {});
    const values = Object.values(perf || {});
    buildChart('tech-chart', {
      type: 'bar',
      data: { labels, datasets: [{ label: 'Resolved', data: values, backgroundColor: '#0dcaf0' }] },
      options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y' },
    });
  };

  const renderEscalation = (freq) => {
    hideSpinner('escalation-spinner');
    const labels = Object.keys(freq || {}).map((k) => `L${k}`);
    const values = Object.values(freq || {});
    buildChart('escalation-chart', {
      type: 'bar',
      data: { labels, datasets: [{ label: 'Escalations', data: values, backgroundColor: '#6f42c1' }] },
      options: { responsive: true, maintainAspectRatio: false },
    });
  };

  const renderHeatmap = (rows) => {
    const container = qs('heatmap-grid');
    if (!container) return;
    container.innerHTML = '';
    const map = rows.reduce((acc, r) => {
      const key = `${r.date || 'unknown'}-${r.hour ?? 0}`;
      acc[key] = (acc[key] || 0) + (r.count || 0);
      return acc;
    }, {});
    const days = Array.from(new Set(rows.map((r) => r.date))).sort();
    const hours = Array.from({ length: 24 }).map((_, i) => i);
    days.forEach((day) => {
      hours.forEach((hour) => {
        const val = map[`${day}-${hour}`] || 0;
        const cell = document.createElement('div');
        cell.className = 'col text-center py-2 rounded shadow-sm';
        cell.style.background = `rgba(13,110,253,${Math.min(0.05 + val * 0.1, 0.85)})`;
        cell.innerHTML = `<div class="fw-bold">${val}</div><div class="small text-muted">${day.slice(5)} ${hour}:00</div>`;
        container.appendChild(cell);
      });
    });
  };

  const renderAll = (data) => {
    renderKpis(data);
    renderDaily(data.alerts_per_day || []);
    renderSeverity(data.severity_distribution || {});
    renderSla(data.sla_compliance || {});
    renderTech(data.technician_performance || {});
    renderEscalation(data.escalation_frequency || {});
    renderHeatmap(data.heatmap || []);
    setText('updated-at', new Date().toLocaleTimeString());
  };

  const loadAnalytics = async () => {
    try {
      const data = await fetchJson(buildUrl());
      renderAll(data || {});
    } catch (err) {
      showError(err.message);
    }
  };

  const setDefaultDates = () => {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 30);
    if (qs('start-date')) qs('start-date').valueAsDate = start;
    if (qs('end-date')) qs('end-date').valueAsDate = end;
  };

  const bindEvents = () => {
    qs('apply-filters')?.addEventListener('click', () => loadAnalytics());
  };

  document.addEventListener('DOMContentLoaded', () => {
    setDefaultDates();
    bindEvents();
    loadAnalytics();
  });
})();
