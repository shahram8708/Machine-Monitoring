(() => {
  const cfg = window.digitalTwinConfig || {};
  const endpoints = cfg.endpoints || {};
  const machineId = cfg.machineId;
  const token = window.ACCESS_TOKEN;
  const pollMs = 45000;
  let riskChart;
  const state = {
    baseline: null,
    live: null,
    latestSimulation: null,
    aiAnalysis: null,
  };

  const el = (id) => document.getElementById(id);

  const authHeaders = (extra = {}) => {
    const headers = { ...extra };
    if (token) headers.Authorization = `Bearer ${token}`;
    return headers;
  };

  async function fetchJson(url, options = {}) {
    const res = await fetch(url, { credentials: 'include', ...options, headers: authHeaders(options.headers || {}) });
    if (!res.ok) throw new Error(`Request failed ${res.status}`);
    return res.json();
  }

  function fmtPct(v, digits = 1) {
    if (v === null || v === undefined || Number.isNaN(v)) return '--';
    return `${(Number(v) * 100).toFixed(digits)}%`;
  }

  function fmtNumber(v, digits = 2) {
    if (v === null || v === undefined || Number.isNaN(v)) return '--';
    return Number(v).toFixed(digits);
  }

  function setText(id, value) {
    const node = el(id);
    if (node) node.textContent = value;
  }

  function renderBaseline(data) {
    if (!data) return;
    setText('baseline-oee', fmtPct(data.baseline_oee, 1));
    setText('baseline-health', fmtNumber(data.baseline_health_score, 1));
    setText('baseline-failure', `${fmtNumber(data.baseline_failure_probability, 1)}%`);
    setText('baseline-energy', fmtNumber(data.baseline_energy_efficiency, 3));
    setText('baseline-updated', `Last updated: ${data.last_updated || '—'}`);
  }

  function renderComparison(live, simulated) {
    const tbody = el('comparison-table');
    if (!tbody) return;
    tbody.innerHTML = '';
    const metrics = [
      { key: 'oee', label: 'OEE', live: fmtPct(live?.oee || 0), sim: fmtPct(simulated?.simulated_oee || 0) },
      { key: 'health_score', label: 'Health Score', live: fmtNumber(live?.health_score, 1), sim: fmtNumber(simulated?.simulated_health_score, 1) },
      { key: 'failure_probability', label: 'Failure Probability', live: `${fmtNumber(live?.failure_probability, 1)}%`, sim: `${fmtNumber(simulated?.simulated_failure_probability, 1)}%` },
      { key: 'energy_efficiency', label: 'Energy Efficiency', live: fmtNumber(live?.energy_efficiency, 3), sim: fmtNumber(simulated?.simulated_energy_efficiency, 3) },
    ];
    metrics.forEach((m) => {
      const diff = (() => {
        const liveNum = Number(String(m.live).replace('%', ''));
        const simNum = Number(String(m.sim).replace('%', ''));
        if (Number.isNaN(liveNum) || Number.isNaN(simNum)) return '--';
        const delta = simNum - liveNum;
        const sign = delta > 0 ? '+' : '';
        return `${sign}${delta.toFixed(2)}`;
      })();
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${m.label}</td><td>${m.live}</td><td>${m.sim}</td><td>${diff}</td>`;
      tbody.appendChild(tr);
    });
    setText('last-refresh', new Date().toLocaleString());
  }

  function renderHistory(items) {
    const tbody = el('history-table');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!items || !items.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No history</td></tr>';
      return;
    }
    items.forEach((row) => {
      const aiStatus = row.ai_analysis && Object.keys(row.ai_analysis).length ? 'Ready' : 'Pending';
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${new Date(row.created_at).toLocaleString()}</td>
        <td>${row.simulation_type}</td>
        <td>${fmtNumber(row.risk_delta, 2)}</td>
        <td><span class="badge bg-${row.impact_level === 'HIGH' ? 'danger' : row.impact_level === 'MEDIUM' ? 'warning text-dark' : 'success'}">${row.impact_level}</span></td>
        <td>${aiStatus}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderChart(simulated) {
    const ctx = el('risk-chart');
    if (!ctx) return;
    const labels = ['Failure Probability', 'Risk Delta'];
    const baselineVal = state.baseline ? Number(state.baseline.baseline_failure_probability || 0) : 0;
    const simFailure = simulated ? Number(simulated.simulated_failure_probability || 0) : 0;
    const riskDelta = simulated ? Number(simulated.risk_delta || 0) : 0;
    const datasets = [
      {
        label: 'Baseline',
        data: [baselineVal, 0],
        backgroundColor: '#6c757d55',
        borderColor: '#6c757d',
      },
      {
        label: 'Simulated',
        data: [simFailure, riskDelta],
        backgroundColor: '#0d6efd55',
        borderColor: '#0d6efd',
      },
    ];
    if (riskChart) riskChart.destroy();
    riskChart = new Chart(ctx, {
      type: 'bar',
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { y: { suggestedMax: Math.max(100, simFailure + 5) } },
        plugins: { legend: { position: 'bottom' } },
      },
    });
  }

  function renderWhatIf(analysis) {
    setText('ai-risk', analysis?.strategic_risk_assessment || '--');
    setText('ai-long-term', analysis?.long_term_impact || '--');
    setText('ai-cost', analysis?.cost_impact_estimation || '--');
    setText('ai-action', analysis?.recommended_action || '--');
    setText('ai-confidence', `Confidence: ${fmtNumber(analysis?.confidence ?? 0, 2)}`);
  }

  async function loadBaseline() {
    if (!endpoints.twin) return;
    const data = await fetchJson(endpoints.twin);
    state.baseline = data;
    state.latestSimulation = data.latest_simulation;
    renderBaseline(data);
    renderComparison(state.live, state.latestSimulation);
    if (state.latestSimulation) renderChart(state.latestSimulation);
  }

  async function loadLive() {
    if (!endpoints.kpi || !endpoints.health || !endpoints.prediction) return;
    try {
      const [kpi, health, prediction] = await Promise.all([
        fetchJson(endpoints.kpi),
        fetchJson(endpoints.health),
        fetchJson(endpoints.prediction),
      ]);
      state.live = {
        oee: Number(kpi.oee || 0),
        health_score: Number(health.score || 0),
        failure_probability: Number(prediction.failure_probability || 0),
        energy_efficiency: Number(kpi.energy_efficiency || 0),
      };
      renderComparison(state.live, state.latestSimulation);
    } catch (err) {
      console.error('Live fetch failed', err);
    }
  }

  async function loadHistory() {
    if (!endpoints.history) return;
    try {
      const data = await fetchJson(endpoints.history);
      renderHistory(data.items || []);
    } catch (err) {
      console.error('History fetch failed', err);
    }
  }

  async function generateBaseline() {
    if (!endpoints.baseline) return;
    const btn = el('generate-baseline');
    if (btn) btn.disabled = true;
    try {
      const data = await fetchJson(endpoints.baseline, { method: 'POST' });
      state.baseline = data;
      renderBaseline(data);
    } catch (err) {
      console.error('Baseline generation failed', err);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function simulate(payload) {
    if (!endpoints.simulate) return;
    setText('simulation-status', 'Running simulation...');
    try {
      const res = await fetch(endpoints.simulate, {
        method: 'POST',
        credentials: 'include',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || 'Simulation failed');
      state.baseline = data.twin;
      state.latestSimulation = data.simulation;
      renderBaseline(data.twin);
      renderComparison(state.live, state.latestSimulation);
      renderChart(state.latestSimulation);
      setText('simulation-status', 'Simulation complete');
      await loadHistory();
    } catch (err) {
      console.error(err);
      setText('simulation-status', 'Simulation failed');
    }
  }

  async function runWhatIf(historyId) {
    if (!endpoints.whatif) return;
    const btn = el('run-whatif');
    if (btn) btn.disabled = true;
    try {
      const res = await fetch(endpoints.whatif, {
        method: 'POST',
        credentials: 'include',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ history_id: historyId }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || 'What-if failed');
      state.aiAnalysis = data.ai_analysis;
      renderWhatIf(state.aiAnalysis);
      await loadHistory();
    } catch (err) {
      console.error(err);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function bindEvents() {
    const baselineBtn = el('generate-baseline');
    if (baselineBtn) baselineBtn.addEventListener('click', (e) => { e.preventDefault(); generateBaseline(); });

    const form = el('simulation-form');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const payload = Object.fromEntries(new FormData(form).entries());
        ['load_pct', 'production_pct', 'sensor_drift_pct', 'manual_risk_adjustment'].forEach((key) => {
          payload[key] = Number(payload[key] || 0);
        });
        simulate(payload);
      });
    }

    const whatIfBtn = el('run-whatif');
    if (whatIfBtn) whatIfBtn.addEventListener('click', () => runWhatIf(state.latestSimulation?.id));
  }

  async function init() {
    if (!machineId) return;
    bindEvents();
    await Promise.all([loadBaseline(), loadLive(), loadHistory()]);
    if (state.latestSimulation) renderChart(state.latestSimulation);
    setInterval(() => {
      loadBaseline();
      loadLive();
      loadHistory();
    }, pollMs);
  }

  init();
})();
