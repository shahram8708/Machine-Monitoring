(function () {
  const token = window.ACCESS_TOKEN;
  const refreshBtn = document.getElementById('fin-refresh');
  const machineInput = document.getElementById('fin-machine-id');
  const chartCanvas = document.getElementById('fin-chart');
  const summary = document.getElementById('fin-summary');
  const lastUpdated = document.getElementById('fin-last-updated');
  let chart;

  async function fetchJson(url) {
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` }, credentials: 'include' });
    if (!res.ok) throw new Error(`Request failed ${res.status}`);
    return res.json();
  }

  function renderChart(data) {
    const labels = ['Downtime Cost', 'Revenue Loss', 'Risk Exposure'];
    const values = [data.projected_downtime_cost || 0, data.projected_revenue_loss || 0, data.total_risk_exposure || 0];
    if (chart) chart.destroy();
    chart = new Chart(chartCanvas, {
      type: 'bar',
      data: { labels, datasets: [{ label: 'USD', data: values, backgroundColor: ['#0d6efd', '#6610f2', '#dc3545'] }] },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
    });
  }

  function renderSummary(data) {
    summary.innerHTML = `
      <div class="d-flex justify-content-between"><span>Projected Downtime Cost</span><span class="fw-bold">$${(data.projected_downtime_cost || 0).toFixed(2)}</span></div>
      <div class="d-flex justify-content-between"><span>Projected Revenue Loss</span><span class="fw-bold">$${(data.projected_revenue_loss || 0).toFixed(2)}</span></div>
      <div class="d-flex justify-content-between"><span>Total Risk Exposure</span><span class="fw-bold text-danger">$${(data.total_risk_exposure || 0).toFixed(2)}</span></div>
      <div class="text-muted small">Confidence: ${(data.confidence ?? 0)}</div>
    `;
    document.getElementById('fin-risk').textContent = `$${(data.total_risk_exposure || 0).toFixed(2)}`;
  }

  async function refresh() {
    const machineId = machineInput.value || new URLSearchParams(window.location.search).get('machine_id');
    if (!machineId) return;
    try {
      const data = await fetchJson(`/api/financial/forecast/${machineId}`);
      renderChart(data);
      renderSummary(data);
      lastUpdated.textContent = `Updated: ${new Date().toLocaleTimeString()}`;
    } catch (err) {
      console.error(err);
    }
  }

  refreshBtn?.addEventListener('click', refresh);
  setInterval(refresh, 60000);
})();
