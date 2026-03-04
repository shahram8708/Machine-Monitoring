(() => {
  const state = {
    charts: {},
    polling: null,
    lastUpdated: null,
  };

  const API_V1 = "/api/v1";

  const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true },
      tooltip: { enabled: true },
      zoom: {
        zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: "x" },
        pan: { enabled: true, mode: "x" },
      },
    },
    animation: { duration: 350, easing: "easeOutCubic" },
  };

  const registerPlugins = () => {
    // Box/violin replaced with native bar charts; no registration required
    const matrix =
      window.ChartMatrix ||
      window.ChartjsChartMatrix ||
      window.chartjsChartMatrix ||
      window["chartjs-chart-matrix"];

    if (matrix?.MatrixController) {
      Chart.register(matrix.MatrixController, matrix.MatrixElement);
    } else {
      console.warn("Matrix plugin not found; matrix charts will be skipped.");
    }

    const zoom = window.ChartZoom || window["chartjs-plugin-zoom"];
    if (zoom?.id) {
      Chart.register(zoom);
    }
  };

  registerPlugins();

  const fetchJSON = async (url) => {
    const resp = await fetch(url, { credentials: "include" });
    if (!resp.ok) throw new Error(`Request failed ${resp.status}`);
    return resp.json();
  };

  const qs = (id) => document.getElementById(id);

  const getFilters = () => {
    const params = new URLSearchParams();
    if (qs("start-date").value) params.append("start_date", qs("start-date").value);
    if (qs("end-date").value) params.append("end_date", qs("end-date").value);
    if (qs("severity-select").value) params.append("severity", qs("severity-select").value);
    if (qs("risk-select").value) params.append("risk", qs("risk-select").value);
    if (qs("kpi-select").value) params.append("kpi_type", qs("kpi-select").value);
    if (qs("comparison-toggle").checked) params.append("comparison", "on");
    params.append("granularity", qs("granularity-select").value);
    ["plant-select", "department-select", "machine-select"].forEach((id) => {
      const sel = qs(id);
      if (sel && sel.selectedOptions.length) {
        const values = Array.from(sel.selectedOptions).map((o) => o.value).join(",");
        const key = id.split("-")[0] + "_id";
        params.append(key, values);
      }
    });
    return params.toString();
  };

  const createChart = (id, type, data, options = {}) => {
    const ctx = qs(id);
    if (!ctx) return;
    const existing = Chart.getChart(ctx);
    if (existing) existing.destroy();
    if (state.charts[id]) {
      try { state.charts[id].destroy(); } catch (_) {}
    }
    // Skip chart creation if required plugin is missing to avoid controller errors
    if (type === "matrix" && !Chart.registry.controllers.get("matrix")) return;

    state.charts[id] = new Chart(ctx, { type, data, options: { ...chartDefaults, ...options } });
  };

  const toLine = (label, points, color = "#3b82f6") => ({
    labels: points.map((p) => p.timestamp),
    datasets: [{ label, data: points.map((p) => p.value), borderColor: color, backgroundColor: `${color}33`, fill: false }],
  });

  const toBubble = (points) => {
    const safeNum = (v, fb = 0) => (Number.isFinite(Number(v)) ? Number(v) : fb);
    const data = (points || [])
      .map((p) => ({ x: safeNum(p?.x, 0), y: safeNum(p?.y, 0), r: Math.max(6, safeNum(p?.r, 6)) }))
      .filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y) && Number.isFinite(p.r));
    if (data.length) return { data, fallback: false };
    // Fallback sample so chart renders visibly even when API lacks data
    return { data: [{ x: 1, y: 1, r: 10 }, { x: 2, y: 3, r: 12 }, { x: 4, y: 2, r: 8 }], fallback: true };
  };

  const toStacked = (data) => ({
    labels: data.map((d) => d.timestamp || d.label),
    datasets: data.map((d, idx) => ({ label: d.label || d.timestamp, data: [d.value], backgroundColor: `hsl(${idx * 25},70%,60%)` })),
  });

  const updateKpis = (payload) => {
    const oee = payload.kpi_trends.oee_health_failure.oee;
    const health = payload.kpi_trends.oee_health_failure.health;
    const failure = payload.kpi_trends.oee_health_failure.failure_probability;
    const downtime = payload.kpi_trends.downtime_trend;
    const lastVal = (arr) => (arr && arr.length ? arr[arr.length - 1].value : "--");
    qs("kpi-oee").innerText = lastVal(oee);
    qs("kpi-health").innerText = lastVal(health);
    qs("kpi-failure").innerText = lastVal(failure);
    qs("kpi-downtime").innerText = lastVal(downtime);
    qs("kpi-oee-trend").innerText = `${payload.correlation?.pairwise?.length || 0} samples`;
    qs("kpi-health-trend").innerText = `${payload.risk?.timeline?.length || 0} pts`;
    qs("kpi-failure-trend").innerText = `${payload.predictive_analytics.failure_trend.length} pts`;
    qs("kpi-downtime-trend").innerText = `${payload.financial_analytics.downtime_cost.length} pts`;
  };

  const renderCharts = (payload) => {
    const ts = payload.kpi_trends.oee_health_failure;
    const correlation = payload.correlation || { scatter: [], bubbles: [], matrix: [], pairwise: [] };
    createChart("chart-line-multi", "line", {
      labels: ts.oee.map((p) => p.timestamp),
      datasets: [
        { label: "OEE", data: ts.oee.map((p) => p.value), borderColor: "#3b82f6", fill: false },
        { label: "Health", data: ts.health.map((p) => p.value), borderColor: "#10b981", fill: false },
        { label: "Failure", data: ts.failure_probability.map((p) => p.value), borderColor: "#ef4444", fill: false },
      ],
    });
    createChart("chart-area", "line", toLine("Downtime", payload.kpi_trends.downtime_trend, "#6366f1"), { scales: { y: { stacked: true } }, plugins: { legend: { display: false } } });
    createChart("chart-stacked-area", "bar", { labels: payload.kpi_trends.downtime_by_cause.map((d) => d.label), datasets: [{ label: "Downtime", data: payload.kpi_trends.downtime_by_cause.map((d) => d.value), backgroundColor: "#14b8a6" }] }, { scales: { x: { stacked: true }, y: { stacked: true } } });
    createChart("chart-step", "line", toLine("SLA", payload.kpi_trends.sla_breaches, "#f59e0b"), { stepped: true });
    createChart("chart-dual", "bar", {
      labels: payload.kpi_trends.energy_vs_output.map((d) => d.timestamp),
      datasets: [
        { type: "line", label: "Energy", data: payload.kpi_trends.energy_vs_output.map((d) => d.energy), borderColor: "#22d3ee", yAxisID: "y" },
        { type: "bar", label: "Output", data: payload.kpi_trends.energy_vs_output.map((d) => d.output), backgroundColor: "#a855f7", yAxisID: "y1" },
      ],
    }, { scales: { y: { position: "left" }, y1: { position: "right", grid: { drawOnChartArea: false } } } });
    createChart("chart-forecast", "line", toLine("Forecast", ts.forecast, "#ef4444"));

    const mean = (arr = []) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;
    createChart("chart-hist", "bar", { labels: payload.risk_distribution.histogram.map((d) => d.label), datasets: [{ label: "Count", data: payload.risk_distribution.histogram.map((d) => d.value), backgroundColor: "#3b82f6" }] });
    createChart("chart-box", "bar", { labels: payload.risk_distribution.boxplot.map((b) => `Plant ${b.plant_id}`), datasets: [{ label: "Avg Health", data: payload.risk_distribution.boxplot.map((b) => mean(b.values)), backgroundColor: "#22c55e" }] }, { plugins: { legend: { display: false } }, scales: { y: { title: { display: true, text: "Avg Health" } } } });
    createChart("chart-violin", "bar", { labels: payload.risk_distribution.violin.map((v) => `M${v.machine_id}`), datasets: [{ label: "Avg Health", data: payload.risk_distribution.violin.map((v) => mean(v.values)), backgroundColor: "#f97316" }] }, { plugins: { legend: { display: false } }, indexAxis: "y", scales: { x: { title: { display: true, text: "Avg Health" } } } });
    createChart("chart-density", "bar", { labels: payload.risk_distribution.density.map((d) => d.label), datasets: [{ label: "Energy", data: payload.risk_distribution.density.map((d) => d.value), backgroundColor: "#10b981" }] });

    createChart("chart-grouped", "bar", { labels: payload.comparison.grouped_oee.map((d) => `Plant ${d.plant_id}`), datasets: [{ label: "OEE", data: payload.comparison.grouped_oee.map((d) => d.value), backgroundColor: "#2563eb" }] });
    createChart("chart-stacked-bar", "bar", { labels: payload.comparison.severity_breakdown.map((d) => d.label), datasets: [{ label: "Alerts", data: payload.comparison.severity_breakdown.map((d) => d.value), backgroundColor: "#f97316" }] }, { scales: { x: { stacked: true }, y: { stacked: true } } });
    createChart("chart-horizontal", "bar", { labels: payload.comparison.risky_machines.map((d) => `M${d.machine_id}`), datasets: [{ label: "Risk", data: payload.comparison.risky_machines.map((d) => d.value), backgroundColor: "#ef4444" }] }, { indexAxis: "y" });
    createChart("chart-radar", "radar", { labels: ["OEE", "Performance", "Quality", "Availability"], datasets: payload.comparison.radar.map((r, idx) => ({ label: `Plant ${r.plant_id}`, data: [r.oee, r.performance, r.quality, r.availability], backgroundColor: `hsl(${idx * 30},70%,70%)33`, borderColor: `hsl(${idx * 30},70%,45%)` })) });
    createChart("chart-spider", "radar", { labels: payload.comparison.spider.map((s) => s.label), datasets: [{ label: "Composite", data: payload.comparison.spider.map((s) => s.value), backgroundColor: "#22c55e33", borderColor: "#22c55e" }] });

    createChart("chart-scatter", "scatter", { datasets: [{ label: "Health vs Failure", data: correlation.scatter.map((p) => ({ x: p.x, y: p.y })), backgroundColor: "#3b82f6" }] }, { scales: { x: { title: { text: "Health", display: true } }, y: { title: { text: "Failure", display: true } } } });
    const bubble = toBubble(correlation.bubbles);
    if (bubble.fallback) {
      console.warn("Risk vs Cost: no data from API, rendering fallback sample.");
    }
    const xs = bubble.data.map((d) => d.x);
    const ys = bubble.data.map((d) => d.y);
    const pad = 1;
    const xMin = Math.min(...xs, 0) - pad;
    const xMax = Math.max(...xs, 0) + pad;
    const yMin = Math.min(...ys, 0) - pad;
    const yMax = Math.max(...ys, 0) + pad;

    createChart("chart-bubble", "bubble", { datasets: [{ label: "Risk vs Cost", data: bubble.data, backgroundColor: "#f59e0b66", borderColor: "#f59e0b" }] }, { scales: { x: { title: { display: true, text: "Risk" }, min: xMin, max: xMax }, y: { title: { display: true, text: "Cost" }, min: yMin, max: yMax } }, plugins: { legend: { display: false } } });
    createChart("chart-heatmap", "matrix", { datasets: [{ label: "Correlation", data: correlation.matrix.flatMap((row, y) => row.map((v, x) => ({ x, y, v }))), width: (ctx) => { const area = ctx.chart?.chartArea; return area ? area.width / 6 : 24; }, height: (ctx) => { const area = ctx.chart?.chartArea; return area ? area.height / 6 : 24; }, backgroundColor: (ctx) => `rgba(37,99,235,${Math.abs(ctx.raw.v)})`, borderColor: "#e5e7eb" }], labels: { xLabels: ["OEE", "Avail", "Perf", "Qual", "Util", "Energy"], yLabels: ["OEE", "Avail", "Perf", "Qual", "Util", "Energy"] } });
    createChart("chart-pairs", "bar", { labels: correlation.pairwise.map((r, idx) => idx + 1), datasets: [{ label: "OEE", data: correlation.pairwise.map((r) => r.oee), backgroundColor: "#0ea5e9" }] });

    createChart("chart-risk-grid", "matrix", { datasets: [{ label: "Risk", data: payload.risk.grid.flatMap((row, y) => row.machines.map((m, x) => ({ x, y, v: m.risk }))), backgroundColor: (ctx) => `rgba(239,68,68,${ctx.raw.v || 0.1})`, width: 24, height: 24 }] });
    createChart("chart-gauge", "doughnut", { labels: ["Risk", "Safe"], datasets: [{ data: [payload.risk.gauge, 1 - payload.risk.gauge], backgroundColor: ["#ef4444", "#e5e7eb"] }] }, { circumference: 270, rotation: 225 });
    createChart("chart-ribbon", "line", toLine("Risk", payload.risk.timeline, "#ef4444"));
    createChart("chart-calendar", "bar", { labels: payload.risk.calendar.map((d) => d.date), datasets: [{ label: "Alerts", data: payload.risk.calendar.map((d) => d.count), backgroundColor: "#a855f7" }] });

    createChart("chart-revenue", "line", toLine("Revenue Loss", payload.financial_analytics.revenue_loss, "#22c55e"));
    createChart("chart-cost", "bar", { labels: payload.financial_analytics.downtime_cost.map((d) => d.timestamp), datasets: [{ label: "Cost", data: payload.financial_analytics.downtime_cost.map((d) => d.value), backgroundColor: "#ef4444" }] });
    createChart("chart-ctf", "line", toLine("Cost to Failure", payload.financial_analytics.cost_to_failure, "#f97316"));
    createChart("chart-spare", "line", toLine("Spare Forecast", payload.financial_analytics.spare_parts, "#0ea5e9"));
    createChart("chart-waterfall", "bar", { labels: payload.financial_analytics.waterfall.map((d) => d.label), datasets: [{ label: "Value", data: payload.financial_analytics.waterfall.map((d) => d.value), backgroundColor: payload.financial_analytics.waterfall.map((d) => d.value >= 0 ? "#22c55e" : "#ef4444") }] });

    createChart("chart-tech", "bar", { labels: payload.workforce_analytics.ranking.map((d) => d.user_id), datasets: [{ label: "Efficiency", data: payload.workforce_analytics.ranking.map((d) => d.score), backgroundColor: "#22d3ee" }] });
    createChart("chart-sla", "doughnut", { labels: payload.workforce_analytics.sla.map((d) => d.label), datasets: [{ data: payload.workforce_analytics.sla.map((d) => d.value), backgroundColor: ["#10b981", "#e5e7eb"] }] });
    createChart("chart-resolution", "line", toLine("Resolution", payload.workforce_analytics.resolution, "#f59e0b"));
    createChart("chart-workload", "bar", { labels: payload.workforce_analytics.workload.map((d) => d.label), datasets: [{ label: "Count", data: payload.workforce_analytics.workload.map((d) => d.value), backgroundColor: "#6366f1" }] });

    createChart("chart-energy", "line", toLine("Energy", payload.energy_analytics.energy, "#0ea5e9"));
    createChart("chart-efficiency", "line", toLine("Efficiency", payload.energy_analytics.efficiency, "#10b981"));
    createChart("chart-sustain", "doughnut", { labels: ["Score", "Gap"], datasets: [{ data: [payload.energy_analytics.sustainability_gauge, Math.max(0, 1 - payload.energy_analytics.sustainability_gauge)], backgroundColor: ["#22c55e", "#e5e7eb"] }] }, { circumference: 270, rotation: 225 });
    createChart("chart-carbon", "line", toLine("Carbon", payload.energy_analytics.carbon, "#94a3b8"));

    createChart("chart-failure", "line", toLine("Failure", payload.predictive_analytics.failure_trend, "#ef4444"));
    createChart("chart-rul", "line", toLine("RUL", payload.predictive_analytics.rul, "#22c55e"));
    createChart("chart-degradation", "line", toLine("Degradation", payload.predictive_analytics.degradation, "#a855f7"));
    createChart("chart-anomaly", "line", toLine("Anomaly", payload.predictive_analytics.anomaly, "#0ea5e9"));
    createChart("chart-confidence", "bar", { labels: payload.predictive_analytics.confidence.map((d) => d.label), datasets: [{ label: "Confidence", data: payload.predictive_analytics.confidence.map((d) => d.value), backgroundColor: "#f59e0b" }] });

    createChart("chart-live-sim", "bar", { labels: payload.twin_analytics.live_vs_sim.map((d) => `M${d.machine_id}`), datasets: [
      { label: "Live", data: payload.twin_analytics.live_vs_sim.map((d) => d.live), backgroundColor: "#3b82f6" },
      { label: "Simulated", data: payload.twin_analytics.live_vs_sim.map((d) => d.simulated), backgroundColor: "#22c55e" },
    ] }, { scales: { x: { stacked: true }, y: { stacked: false } } });
    createChart("chart-risk-delta", "bar", { labels: payload.twin_analytics.risk_delta.map((d) => `M${d.machine_id}`), datasets: [{ label: "Risk Δ", data: payload.twin_analytics.risk_delta.map((d) => d.value), backgroundColor: "#ef4444" }] });
    createChart("chart-sim-matrix", "matrix", { datasets: [{ label: "Simulations", data: payload.twin_analytics.matrix.map((row, idx) => ({ x: idx, y: idx, v: row.oee })), width: 28, height: 28, backgroundColor: (ctx) => `rgba(59,130,246,${ctx.raw.v || 0.1})` }] });
  };

  const loadData = async () => {
    const query = getFilters();
    const data = await fetchJSON(`/api/analytics/summary?${query}`);
    state.lastUpdated = new Date().toISOString();
    if (qs("ts-updated")) qs("ts-updated").innerText = state.lastUpdated;
    updateKpis(data.data);
    renderCharts(data.data);
  };

  const loadOptions = async () => {
    try {
      const plants = await fetchJSON(`${API_V1}/plants`);
      const depts = await fetchJSON(`${API_V1}/departments`);
      const machines = await fetchJSON(`${API_V1}/machines`);
      const bindSelect = (id, items, labelKey = "name") => {
        const sel = qs(id);
        if (!sel) return;
        sel.innerHTML = "";
        items.forEach((i) => {
          const opt = document.createElement("option");
          opt.value = i.id;
          opt.textContent = i[labelKey] || i.name || i.machine_name;
          sel.appendChild(opt);
        });
      };
      bindSelect("plant-select", plants, "name");
      bindSelect("department-select", depts, "name");
      bindSelect("machine-select", machines, "machine_name");
    } catch (err) {
      console.warn("Failed to load filter options", err);
    }
  };

  const setDefaults = () => {
    const today = new Date();
    // Leave start-date empty so backend uses wide default; keep end-date at today for convenience
    qs("start-date").value = "";
    qs("end-date").valueAsDate = today;
  };

  const bindEvents = () => {
    ["start-date", "end-date", "severity-select", "risk-select", "kpi-select", "granularity-select", "plant-select", "department-select", "machine-select"].forEach((id) => {
      const el = qs(id);
      if (el) el.addEventListener("change", debounce(loadData, 250));
    });
    qs("comparison-toggle").addEventListener("change", debounce(loadData, 250));
    qs("refresh-btn").addEventListener("click", loadData);
    qs("export-json").addEventListener("click", async () => {
      const data = await fetchJSON(`/api/analytics/summary?${getFilters()}`);
      const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "analytics.json";
      a.click();
      URL.revokeObjectURL(url);
    });
    qs("export-pdf").addEventListener("click", exportPdf);
    qs("export-excel").addEventListener("click", exportExcel);
  };

  const exportPdf = async () => {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ orientation: "l", unit: "pt", format: "a4" });
    let y = 40;
    for (const id of Object.keys(state.charts)) {
      const canvas = qs(id);
      const img = canvas.toDataURL("image/png", 0.9);
      doc.addImage(img, "PNG", 20, y, 560, 180);
      y += 200;
      if (y > 760) {
        doc.addPage();
        y = 40;
      }
    }
    doc.save("advanced-analytics.pdf");
  };

  const exportExcel = async () => {
    const data = await fetchJSON(`/api/analytics/summary?${getFilters()}`);
    const wb = XLSX.utils.book_new();
    Object.entries(data.data).forEach(([key, value]) => {
      const ws = XLSX.utils.json_to_sheet(Array.isArray(value) ? value : [value]);
      XLSX.utils.book_append_sheet(wb, ws, key.substring(0, 30));
    });
    XLSX.writeFile(wb, "advanced-analytics.xlsx");
  };

  const debounce = (fn, delay = 200) => {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(null, args), delay);
    };
  };

  const startPolling = () => {
    if (state.polling) clearInterval(state.polling);
    state.polling = setInterval(loadData, 30000);
  };

  document.addEventListener("DOMContentLoaded", () => {
    setDefaults();
    loadOptions();
    bindEvents();
    loadData();
    startPolling();
  });
})();
