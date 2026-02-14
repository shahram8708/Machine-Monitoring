(function () {
    const config = window.analyticsConfig || {};
    const machineId = config.machineId;
    if (!machineId) return;

    let tempChart = null;
    let vibChart = null;
    let energyChart = null;
    let runtimeChart = null;

    const startInput = document.getElementById("start_date");
    const endInput = document.getElementById("end_date");
    const applyBtn = document.getElementById("apply-range");
    const rangeLabel = document.getElementById("range-label");
    const loading = document.getElementById("loading-overlay");

    const setLoading = (isLoading) => {
        if (!loading) return;
        loading.classList.toggle("d-none", !isLoading);
    };

    const formatDateLabel = (dateStr) => {
        if (!dateStr) return "";
        const d = new Date(dateStr);
        return d.toISOString().slice(0, 10);
    };

    const destroyIfExists = (chartRef) => {
        if (chartRef) {
            chartRef.destroy();
        }
    };

    const lineOptions = (title) => ({
        type: "line",
        data: { labels: [], datasets: [] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { display: true, labels: { usePointStyle: true } },
                title: { display: false },
            },
            scales: {
                x: { display: true, title: { display: true, text: "Time" } },
                y: { display: true, title: { display: true, text: title } },
            },
        },
    });

    const barOptions = {
        type: "bar",
        data: { labels: [], datasets: [] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: { display: true, title: { display: true, text: "Period" } },
                y: { display: true, title: { display: true, text: "kWh" } },
            },
        },
    };

    const pieOptions = {
        type: "pie",
        data: { labels: ["Running", "Idle"], datasets: [] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "bottom" },
            },
        },
    };

    const renderTemperature = (series) => {
        destroyIfExists(tempChart);
        const labels = series.map((p) => formatDateLabel(p.timestamp));
        const values = series.map((p) => p.value);
        const ctx = document.getElementById("temp-chart");
        if (!ctx) return;
        const opts = lineOptions("Temperature (°C)");
        opts.data.labels = labels;
        opts.data.datasets = [
            {
                label: "Temperature (°C)",
                data: values,
                borderColor: "#0d6efd",
                backgroundColor: "rgba(13,110,253,0.15)",
                tension: 0.25,
                fill: true,
            },
        ];
        tempChart = new Chart(ctx, opts);
        const badge = document.getElementById("temp-points");
        if (badge) badge.textContent = `${series.length} pts`;
    };

    const renderVibration = (series) => {
        destroyIfExists(vibChart);
        const labels = series.map((p) => formatDateLabel(p.timestamp));
        const values = series.map((p) => p.value);
        const ctx = document.getElementById("vibration-chart");
        if (!ctx) return;
        const opts = lineOptions("Vibration (mm/s)");
        opts.data.labels = labels;
        opts.data.datasets = [
            {
                label: "Vibration (mm/s)",
                data: values,
                borderColor: "#fd7e14",
                backgroundColor: "rgba(253,126,20,0.15)",
                tension: 0.25,
                fill: true,
            },
        ];
        vibChart = new Chart(ctx, opts);
        const badge = document.getElementById("vib-points");
        if (badge) badge.textContent = `${series.length} pts`;
    };

    const renderEnergy = (series) => {
        destroyIfExists(energyChart);
        const labels = series.map((p) => formatDateLabel(p.timestamp));
        const values = series.map((p) => p.value);
        const ctx = document.getElementById("energy-chart");
        if (!ctx) return;
        const opts = JSON.parse(JSON.stringify(barOptions));
        opts.data.labels = labels;
        opts.data.datasets = [
            {
                label: "Energy (kWh)",
                data: values,
                backgroundColor: "rgba(25,135,84,0.6)",
                borderColor: "#198754",
                borderWidth: 1,
            },
        ];
        energyChart = new Chart(ctx, opts);
        const badge = document.getElementById("energy-points");
        if (badge) badge.textContent = `${series.length} bars`;
    };

    const renderRuntime = (runtime) => {
        destroyIfExists(runtimeChart);
        const ctx = document.getElementById("runtime-chart");
        if (!ctx) return;
        const running = runtime?.running_hours || 0;
        const idle = runtime?.idle_hours || 0;
        const opts = JSON.parse(JSON.stringify(pieOptions));
        opts.data.datasets = [
            {
                data: [running, idle],
                backgroundColor: ["#20c997", "#adb5bd"],
                borderWidth: 1,
            },
        ];
        runtimeChart = new Chart(ctx, opts);
        const badge = document.getElementById("runtime-label");
        if (badge) badge.textContent = `${running.toFixed(1)}h / ${idle.toFixed(1)}h`;
    };

    const applyRangeLabel = (start, end) => {
        if (!rangeLabel) return;
        rangeLabel.textContent = `${formatDateLabel(start)} → ${formatDateLabel(end)}`;
    };

    const fetchData = () => {
        const start = startInput?.value;
        const end = endInput?.value;
        setLoading(true);
        fetch(`/analytics/${machineId}/data?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`)
            .then((res) => res.json())
            .then((data) => {
                renderTemperature(data.temperature || []);
                renderVibration(data.vibration || []);
                renderEnergy(data.energy || []);
                renderRuntime(data.runtime || {});
                applyRangeLabel(data.start_date, data.end_date);
            })
            .catch(() => {
                applyRangeLabel(start, end);
            })
            .finally(() => setLoading(false));
    };

    if (applyBtn) {
        applyBtn.addEventListener("click", fetchData);
    }

    // Initial load
    if (startInput && !startInput.value && config.startDate) startInput.value = config.startDate;
    if (endInput && !endInput.value && config.endDate) endInput.value = config.endDate;
    fetchData();
})();
