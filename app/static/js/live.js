(function () {
    const machineId = window.liveMachineId;
    if (!machineId) return;

    const statusBadge = document.getElementById("machine-status-badge");
    const lastSeenLabel = document.getElementById("last-seen-label");
    const runningBadge = document.getElementById("running-status-badge");

    const statusClassMap = {
        running: "bg-success",
        idle: "bg-secondary",
        offline: "bg-danger",
        maintenance: "bg-info",
    };

    const formatNumber = (value, decimals = 1, suffix = "") => {
        if (value === null || value === undefined || Number.isNaN(value)) return "—";
        return `${Number(value).toFixed(decimals)}${suffix}`;
    };

    const updateField = (id, text) => {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = text;
        }
    };

    const updateStatus = (status, lastSeen) => {
        const cls = statusClassMap[status] || "bg-secondary";
        statusBadge.className = `badge px-3 py-2 ${cls}`;
        statusBadge.textContent = status ? status.charAt(0).toUpperCase() + status.slice(1) : "Unknown";
        if (lastSeenLabel) {
            lastSeenLabel.textContent = `Last seen: ${lastSeen || "—"}`;
        }
    };

    const updateRunningBadge = (isRunning) => {
        runningBadge.textContent = isRunning ? "Running" : "Idle";
        runningBadge.className = isRunning ? "badge bg-success-subtle text-success" : "badge bg-secondary-subtle text-secondary";
    };

    const applyLatest = (data) => {
        const latest = data.latest || null;
        updateStatus(data.status, data.last_seen);

        if (!latest) {
            updateField("temp-value", "—");
            updateField("vibration-value", "—");
            updateField("current-value", "—");
            updateField("voltage-value", "—");
            updateField("speed-value", "—");
            updateField("humidity-value", "—");
            updateField("timestamp-value", "Waiting for data…");
            updateRunningBadge(false);
            return;
        }

        updateField("temp-value", formatNumber(latest.temperature, 1, "°C"));
        updateField("vibration-value", formatNumber(latest.vibration, 2, " mm/s"));
        updateField("current-value", formatNumber(latest.current, 2, " A"));
        updateField("voltage-value", formatNumber(latest.voltage, 0, " V"));
        updateField("speed-value", formatNumber(latest.speed, 0, " rpm"));
        updateField("humidity-value", formatNumber(latest.humidity, 0, " %"));
        updateField("timestamp-value", latest.timestamp || "—");
        updateRunningBadge(Boolean(latest.running_status));
    };

    const poll = () => {
        fetch(`/machines/${machineId}/live-data`, { cache: "no-store" })
            .then((res) => res.json())
            .then(applyLatest)
            .catch(() => {
                updateStatus("offline", null);
            });
    };

    poll();
    setInterval(poll, 5000);
})();
