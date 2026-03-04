(function () {
  const token = window.ACCESS_TOKEN;
  const machineInput = document.getElementById('esg-machine-id');
  const refreshBtn = document.getElementById('esg-refresh');
  const scoreEl = document.getElementById('esg-score');
  const confEl = document.getElementById('esg-confidence');
  const suggEl = document.getElementById('esg-suggestions');
  const lastUpdated = document.getElementById('esg-last-updated');
  let energyChart;

  async function fetchJson(url) {
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` }, credentials: 'include' });
    if (!res.ok) throw new Error(`Request failed ${res.status}`);
    return res.json();
  }

  function renderEnergy(series = []) {
    const ctx = document.getElementById('esg-energy-chart');
    const labels = series.map((p) => p.date);
    const values = series.map((p) => p.energy_kwh);
    if (energyChart) energyChart.destroy();
    energyChart = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets: [{ label: 'Energy (kWh)', data: values, tension: 0.3, borderColor: '#0d6efd', fill: false }] },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
    });
  }

  function renderSuggestions(ai = {}) {
    const list = ai.energy_optimization_suggestions || [];
    suggEl.innerHTML = '';
    if (list.length === 0) {
      suggEl.innerHTML = '<p class="text-muted mb-0">No suggestions yet.</p>';
      return;
    }
    const ul = document.createElement('ul');
    ul.className = 'mb-0';
    list.forEach((item) => {
      const li = document.createElement('li');
      li.textContent = item;
      ul.appendChild(li);
    });
    if (ai.efficiency_gap_analysis) {
      const p = document.createElement('p');
      p.className = 'text-muted small mt-2';
      p.textContent = ai.efficiency_gap_analysis;
      suggEl.appendChild(p);
    }
    suggEl.appendChild(ul);
  }

  async function refresh() {
    const machineId = machineInput.value || new URLSearchParams(window.location.search).get('machine_id');
    if (!machineId) return;
    try {
      const data = await fetchJson(`/api/esg/metrics/${machineId}`);
      renderEnergy(data.energy_trend?.series || []);
      scoreEl.textContent = data.sustainability_score ?? '--';
      confEl.textContent = data.confidence ?? '--';
      renderSuggestions(data.ai || {});
      lastUpdated.textContent = `Updated: ${new Date().toLocaleTimeString()}`;
    } catch (err) {
      console.error(err);
    }
  }

  refreshBtn?.addEventListener('click', refresh);
  setInterval(refresh, 60000);
})();
