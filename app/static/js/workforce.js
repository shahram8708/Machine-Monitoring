(function () {
  const token = window.ACCESS_TOKEN;
  const pollingMs = 60000;

  const rankingBody = document.querySelector('#wf-ranking tbody');
  const openTasks = document.getElementById('wf-open-tasks');
  const delayed = document.getElementById('wf-delayed');
  const lastUpdated = document.getElementById('wf-last-updated');
  let workloadChart;

  async function fetchJson(url) {
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` }, credentials: 'include' });
    if (!res.ok) throw new Error(`Request failed ${res.status}`);
    return res.json();
  }

  function renderRanking(rows = []) {
    rankingBody.innerHTML = '';
    rows.forEach((r) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${r.technician_name || 'Tech ' + r.user_id}</td><td>${r.efficiency_score ?? '--'}</td><td>${r.tasks_completed ?? 0}</td><td>${r.sla_compliance ?? '--'}%</td>`;
      rankingBody.appendChild(tr);
    });
  }

  function renderWorkload(data) {
    const ctx = document.getElementById('wf-workload-chart');
    const labels = ['Overloaded', 'Underloaded'];
    const values = [data.overloaded?.length || 0, data.underloaded?.length || 0];
    if (workloadChart) workloadChart.destroy();
    workloadChart = new Chart(ctx, {
      type: 'bar',
      data: { labels, datasets: [{ label: 'Technicians', data: values, backgroundColor: ['#dc3545', '#20c997'] }] },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
    });
  }

  async function refresh() {
    try {
      const [analytics, balance] = await Promise.all([
        fetchJson('/api/workforce/analytics'),
        fetchJson('/api/workforce/workload-balance'),
      ]);
      renderRanking(analytics.ranking || []);
      openTasks.textContent = analytics.open_tasks ?? '--';
      delayed.textContent = analytics.delayed_tasks ?? '--';
      renderWorkload(balance || {});
      lastUpdated.textContent = `Updated: ${new Date().toLocaleTimeString()}`;
    } catch (err) {
      console.error(err);
    }
  }

  setInterval(refresh, pollingMs);
  refresh();
})();
