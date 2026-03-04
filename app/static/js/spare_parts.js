(function () {
  const token = window.ACCESS_TOKEN;
  const pollingMs = 60000;

  const machineInput = document.getElementById('sp-machine-id');
  const refreshBtn = document.getElementById('sp-refresh');
  const tableBody = document.querySelector('#sp-demand-table tbody');
  const summaryDiv = document.getElementById('sp-summary');
  const lastUpdated = document.getElementById('sp-last-updated');

  let riskChart;

  async function fetchJson(url) {
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
      credentials: 'omit',
    });
    if (!res.ok) throw new Error(`Request failed ${res.status}`);
    return res.json();
  }

  function renderTable(parts = []) {
    tableBody.innerHTML = '';
    parts.forEach((p) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${p.part_name}</td>
        <td>${p.part_code}</td>
        <td>${p.recommended_quantity || 0}</td>
        <td>${p.current_stock || 0} / ${p.minimum_required_stock || 0}</td>
        <td><span class="badge bg-${p.stock_out_risk > 60 ? 'danger' : p.stock_out_risk > 30 ? 'warning' : 'success'}">${p.stock_out_risk}%</span></td>
        <td>$${(p.estimated_cost || 0).toFixed(2)}</td>`;
      tableBody.appendChild(tr);
    });
  }

  function renderSummary(summary) {
    summaryDiv.innerHTML = `
      <div class="d-flex justify-content-between"><span>Total Items</span><span class="fw-bold">${summary.total_items}</span></div>
      <div class="d-flex justify-content-between"><span>At Risk</span><span class="fw-bold text-danger">${summary.at_risk}</span></div>
      <div class="d-flex justify-content-between"><span>Avg Lead Time (days)</span><span class="fw-bold">${summary.avg_lead_time_days}</span></div>
    `;
  }

  function renderRiskChart(parts = []) {
    const ctx = document.getElementById('sp-risk-chart');
    const labels = parts.map((p) => p.part_code || p.part_name);
    const data = parts.map((p) => p.stock_out_risk || 0);
    if (riskChart) riskChart.destroy();
    riskChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Stock-out risk %',
            data,
            backgroundColor: data.map((v) => (v > 60 ? 'rgba(220,53,69,0.7)' : v > 30 ? 'rgba(255,193,7,0.7)' : 'rgba(25,135,84,0.7)')),
          },
        ],
      },
      options: {
        responsive: true,
        scales: { y: { beginAtZero: true, max: 100 } },
        plugins: { legend: { display: false } },
      },
    });
  }

  async function refresh() {
    const machineId = machineInput.value || new URLSearchParams(window.location.search).get('machine_id') || window.DEFAULT_MACHINE_ID;
    if (!machineId) return;
    try {
      const [prediction, summary] = await Promise.all([
        fetchJson(`/api/spare-parts/predict/${machineId}`),
        fetchJson(`/api/spare-parts/recommendation-summary`),
      ]);
      const parts = prediction.recommended_parts || [];
      renderTable(parts);
      renderRiskChart(parts);
      renderSummary(summary || {});
      lastUpdated.textContent = `Updated: ${new Date().toLocaleTimeString()}`;
    } catch (err) {
      console.error(err);
    }
  }

  refreshBtn?.addEventListener('click', refresh);
  setInterval(refresh, pollingMs);
  refresh();
})();
