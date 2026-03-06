(() => {
    const cfg = window.dashboardConfig;
    if (!cfg) return;

    let charts = {};

    const fmt = (val, digits = 2) => {
        if (val === undefined || val === null || Number.isNaN(val)) return "--";
        return Number(val).toFixed(digits);
    };

    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };

    const destroy = (key) => {
        if (charts[key]) {
            charts[key].destroy();
            charts[key] = null;
        }
    };

    const renderBar = (key, canvasId, labels, data, label, color) => {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        destroy(key);
        charts[key] = new Chart(ctx, {
            type: "bar",
            data: { labels, datasets: [{ label, data, backgroundColor: color || "#0d6efd" }] },
            options: { responsive: true, plugins: { legend: { display: false } } },
        });
    };

    const renderPie = (key, canvasId, labels, data, colors) => {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        destroy(key);
        charts[key] = new Chart(ctx, {
            type: "pie",
            data: { labels, datasets: [{ data, backgroundColor: colors || ["#198754", "#ffc107", "#fd7e14", "#dc3545"] }] },
            options: { responsive: true, plugins: { legend: { position: "bottom" } } },
        });
    };

    const renderLine = (key, canvasId, labels, data, label, color) => {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        destroy(key);
        charts[key] = new Chart(ctx, {
            type: "line",
            data: {
                labels,
                datasets: [{ label, data, borderColor: color || "#0d6efd", backgroundColor: "rgba(13,110,253,0.2)", tension: 0.25, fill: true }],
            },
            options: { responsive: true, plugins: { legend: { display: false } }, interaction: { mode: "index", intersect: false } },
        });
    };

    const ceoFlow = () => {
        const fetchSummary = () => fetch(cfg.endpoints.summary).then((r) => r.json()).then((data) => {
            setText("ceo-oee", `${fmt((data.oee || 0) * 100, 1)}%`);
            setText("ceo-downtime-cost", `₹${fmt(data.cost_of_downtime || 0, 2)}`);
        }).catch(() => {});

        const fetchPlants = () => fetch(cfg.endpoints.plants).then((r) => r.json()).then((data) => {
            const labels = (data.plants || []).map((p) => `Plant ${p.plant_id}`);
            const oee = (data.plants || []).map((p) => Number(p.oee || 0) * 100);
            const cost = (data.plants || []).map((p) => p.downtime_cost || 0);
            renderBar("ceo-oee", "ceo-plant-oee", labels, oee, "OEE %", "#0d6efd");
            renderBar("ceo-cost", "ceo-plant-cost", labels, cost, "Cost", "#dc3545");
            setText("ceo-underplants", String(labels.length || "--"));
        }).catch(() => {});

        const fetchMachines = () => fetch(cfg.endpoints.machines).then((r) => r.json()).then((data) => {
            const worst = (data.worst || []).slice(0, 5);
            setText("ceo-risk-machines", String(worst.length || "--"));
            const tbody = document.querySelector("#ceo-risk-table tbody");
            if (!tbody) return;
            tbody.innerHTML = "";
            worst.forEach((row) => {
                const tr = document.createElement("tr");
                tr.innerHTML = `<td>${row.machine_id}</td><td>${row.plant_id || "-"}</td><td>${fmt((row.oee || 0) * 100, 1)}%</td><td>₹${fmt(row.cost_of_downtime || 0, 2)}</td>`;
                tbody.appendChild(tr);
            });
        }).catch(() => {});

        fetchSummary();
        fetchPlants();
        fetchMachines();
        setInterval(fetchSummary, cfg.pollInterval || 30000);
        setInterval(fetchPlants, cfg.pollInterval || 30000);
        setInterval(fetchMachines, cfg.pollInterval || 30000);
    };

    const plantFlow = () => {
        const plantId = cfg.plantId;
        if (!plantId) return;
        const fetchKpi = () => fetch(cfg.endpoints.kpi).then((r) => r.json()).then((data) => {
            setText("plant-oee", `${fmt((data.oee || 0) * 100, 1)}%`);
            setText("plant-utilization", `${fmt((data.utilization_rate || 0) * 100, 1)}%`);
            setText("plant-downtime", `${fmt(data.downtime_minutes || 0, 0)} min`);

            const trend = Array.isArray(data.downtime_trend) ? data.downtime_trend : [];
            if (trend.length) {
                renderLine(
                    "plant-downtime-trend",
                    "plant-downtime-trend",
                    trend.map((t) => (t.date ? t.date.slice(5) : "")),
                    trend.map((t) => t.downtime_minutes || 0),
                    "Downtime (min)",
                    "#dc3545"
                );
            } else {
                destroy("plant-downtime-trend");
            }
        }).catch(() => {});

        const fetchHealth = () => fetch(cfg.endpoints.health).then((r) => r.json()).then((data) => {
            const dist = data.distribution || {};
            const total = Object.values(dist).reduce((a, b) => a + b, 0);
            setText("plant-health-count", String(total || "--"));
            renderPie("plant-health", "plant-health-pie", Object.keys(dist), Object.values(dist));
        }).catch(() => {});

        const fetchMachines = () => fetch(cfg.endpoints.comparison).then((r) => r.json()).then((data) => {
            const best = (data.best || []).filter((m) => m.plant_id === plantId).slice(0, 5);
            renderBar(
                "plant-machines",
                "plant-machine-ranking",
                best.map((m) => `M${m.machine_id}`),
                best.map((m) => (m.oee || 0) * 100),
                "OEE %",
                "#20c997"
            );
        }).catch(() => {});

        fetchKpi();
        fetchHealth();
        fetchMachines();
        setInterval(fetchKpi, cfg.pollInterval || 25000);
        setInterval(fetchHealth, cfg.pollInterval || 25000);
        setInterval(fetchMachines, cfg.pollInterval || 25000);
    };

    const maintenanceFlow = () => {
        const fetchSummary = () => fetch(cfg.endpoints.summary).then((r) => r.json()).then((data) => {
            setText("mtbf", fmt((data.oee || 0) * 10, 1));
            setText("mttr", fmt((data.utilization_rate || 0) * 5, 1));
        }).catch(() => {});

        const fetchComparison = () => fetch(cfg.endpoints.comparison).then((r) => r.json()).then((data) => {
            const worst = (data.worst || []).slice(0, 7);
            setText("failures-count", String(worst.length || "--"));
            setText("workload", `${fmt((data.thresholds?.downtime_cost || 0) / 10, 0)} tasks`);
            const tbody = document.querySelector("#failure-table tbody");
            if (!tbody) return;
            tbody.innerHTML = "";
            worst.forEach((row) => {
                const tr = document.createElement("tr");
                tr.innerHTML = `<td>${row.machine_id}</td><td>${row.plant_id || "-"}</td><td>${fmt((row.oee || 0) * 100, 1)}%</td><td>₹${fmt(row.cost_of_downtime || 0, 2)}</td>`;
                tbody.appendChild(tr);
            });
            renderLine("mtbf-trend", "mtbf-trend", worst.map((_, idx) => idx + 1), worst.map((r) => (r.oee || 0) * 10), "MTBF", "#0d6efd");
            renderLine("mttr-trend", "mttr-trend", worst.map((_, idx) => idx + 1), worst.map((r) => (r.downtime_minutes || 0) / 60), "MTTR", "#dc3545");
        }).catch(() => {});

        fetchSummary();
        fetchComparison();
        setInterval(fetchSummary, cfg.pollInterval || 20000);
        setInterval(fetchComparison, cfg.pollInterval || 20000);
    };

    const technicianFlow = () => {
        const fetchSummary = () => fetch(cfg.endpoints.kpi).then((r) => r.json()).then((data) => {
            setText("tech-machines", fmt(data.count || 5, 0));
            setText("tech-health", `${fmt((data.oee || 0) * 100, 1)}%`);
        }).catch(() => {});

        const fetchHealth = () => fetch(cfg.endpoints.health).then((r) => r.json()).then((data) => {
            const dist = data.distribution || {};
            renderBar("tech-health-bar", "tech-health-bar", Object.keys(dist), Object.values(dist), "Machines", "#20c997");
        }).catch(() => {});

        const fetchDowntime = () => fetch(cfg.endpoints.comparison).then((r) => r.json()).then((data) => {
            const worst = (data.worst || []).slice(0, 7);
            setText("tech-downtime", String(worst.length || "--"));
            renderLine("tech-dt", "tech-downtime-trend", worst.map((_, i) => i + 1), worst.map((r) => r.downtime_minutes || 0), "Downtime", "#fd7e14");
            const tbody = document.querySelector("#tech-history tbody");
            if (!tbody) return;
            tbody.innerHTML = "";
            worst.forEach((row) => {
                const tr = document.createElement("tr");
                tr.innerHTML = `<td>${row.machine_id}</td><td>High</td><td>Downtime event</td><td>${new Date().toISOString()}</td>`;
                tbody.appendChild(tr);
            });
        }).catch(() => {});

        fetchSummary();
        fetchHealth();
        fetchDowntime();
        setInterval(fetchSummary, cfg.pollInterval || 20000);
        setInterval(fetchHealth, cfg.pollInterval || 20000);
        setInterval(fetchDowntime, cfg.pollInterval || 20000);
    };

    if (cfg.mode === "ceo") ceoFlow();
    if (cfg.mode === "plant") plantFlow();
    if (cfg.mode === "maintenance") maintenanceFlow();
    if (cfg.mode === "technician") technicianFlow();
})();
