(function () {
    const cfg = window.aiDashboardConfig || {};
    const picker = document.getElementById("machine-picker");
    const runBtn = document.getElementById("run-prediction-btn");
    const refreshBtn = document.getElementById("refresh-btn");
    const riskGaugeCtx = document.getElementById("risk-gauge");
    const riskScore = document.getElementById("risk-score");
    const riskLevel = document.getElementById("risk-level");
    const confidenceLabel = document.getElementById("confidence-label");
    const earlyWarning = document.getElementById("early-warning");
    const lastUpdated = document.getElementById("last-updated");
    const rulHours = document.getElementById("rul-hours");
    const rulDays = document.getElementById("rul-days");
    const degradationStage = document.getElementById("degradation-stage");
    const aiExplanation = document.getElementById("ai-explanation");
    const anomalyNote = document.getElementById("anomaly-note");
    const actionList = document.getElementById("action-list");
    const strategyText = document.getElementById("strategy-text");
    const trendCtx = document.getElementById("failure-trend");

    let gaugeChart = null;
    let trendChart = null;

    if (!picker || !cfg.predictionUrl) return;

    let accessToken = cfg.accessToken;

    const authHeaders = (extra = {}) => {
        const headers = { ...extra };
        if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
        return headers;
    };

    const refreshAccessToken = async () => {
        const res = await fetch("/auth/api/refresh", { method: "POST", credentials: "include" });
        if (!res.ok) throw new Error("refresh failed");
        const data = await res.json();
        if (!data.access_token) throw new Error("no token returned");
        accessToken = data.access_token;
        cfg.accessToken = data.access_token;
        return accessToken;
    };

    const apiFetch = async (url, options = {}, allowRetry = true) => {
        const res = await fetch(url, {
            credentials: "include",
            ...options,
            headers: authHeaders(options.headers || {}),
        });
        if (res.status === 401 && allowRetry) {
            try {
                await refreshAccessToken();
                return apiFetch(url, options, false);
            } catch (err) {
                console.warn("Token refresh failed", err);
            }
        }
        return res;
    };

    const clamp = (val, min, max) => Math.max(min, Math.min(max, val));

    const riskColor = (prob) => {
        if (prob >= 80) return "#dc3545";
        if (prob >= 60) return "#fd7e14";
        if (prob >= 30) return "#ffc107";
        return "#198754";
    };

    const setRiskBadge = (level) => {
        const map = {
            LOW: "bg-success",
            MEDIUM: "bg-warning text-dark",
            HIGH: "bg-danger",
            CRITICAL: "bg-danger",
        };
        riskLevel.className = `badge ${map[level] || "bg-secondary"}`;
        riskLevel.textContent = level || "--";
    };

    const renderGauge = (prob) => {
        const score = clamp(prob || 0, 0, 100);
        if (gaugeChart) gaugeChart.destroy();
        gaugeChart = new Chart(riskGaugeCtx, {
            type: "doughnut",
            data: {
                datasets: [
                    {
                        data: [score, 100 - score],
                        backgroundColor: [riskColor(score), "#e9ecef"],
                        borderWidth: 0,
                        cutout: "70%",
                    },
                ],
            },
            options: {
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
                responsive: true,
            },
        });
        riskScore.textContent = `${score.toFixed(1)}%`;
    };

    const renderTrend = (series) => {
        const labels = series.map((p) => p.timestamp?.slice(0, 10));
        const values = series.map((p) => p.failure_probability);
        if (trendChart) trendChart.destroy();
        trendChart = new Chart(trendCtx, {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        label: "Failure Probability",
                        data: values,
                        borderColor: "#0d6efd",
                        backgroundColor: "rgba(13, 110, 253, 0.15)",
                        tension: 0.25,
                        fill: true,
                    },
                ],
            },
            options: {
                plugins: { legend: { display: false } },
                scales: { y: { min: 0, max: 100 } },
            },
        });
    };

    const setActions = (actions) => {
        actionList.innerHTML = "";
        if (!actions || !actions.length) {
            actionList.innerHTML = "<li class='text-muted small'>No actions available.</li>";
            return;
        }
        actions.forEach((a) => {
            const li = document.createElement("li");
            li.textContent = a;
            actionList.appendChild(li);
        });
    };

    const populateCards = (data) => {
        renderGauge(data.failure_probability || 0);
        setRiskBadge(data.risk_level);
        confidenceLabel.textContent = data.confidence_score != null ? data.confidence_score.toFixed(2) : "--";
        earlyWarning.innerHTML = data.early_warning_flag
            ? '<span class="badge bg-danger">EARLY WARNING</span>'
            : '<span class="badge bg-success-subtle text-success">Stable</span>';
        lastUpdated.textContent = data.created_at || "--";

        const rulRaw = data.ai_explanation?.rul || {};
        const fallbackHours = data.remaining_useful_life_hours;
        const hoursVal = rulRaw.remaining_hours ?? fallbackHours;
        const daysVal = rulRaw.remaining_days ?? (hoursVal != null ? hoursVal / 24 : null);
        const stageVal = rulRaw.degradation_stage || data.ai_explanation?.degradation_stage || data.risk_level || "MID";

        rulHours.textContent = hoursVal != null ? hoursVal.toFixed(1) : "--";
        rulDays.textContent = daysVal != null ? `${daysVal.toFixed(1)} days` : "--";
        degradationStage.textContent = `Stage ${stageVal}`;

        const failure = data.ai_explanation?.failure || {};
        const degradation = data.ai_explanation?.degradation || {};
        const actionsInfo = data.ai_explanation?.actions || {};
        aiExplanation.textContent = failure.explanation || degradation.explanation || actionsInfo.explanation || "AI explanation unavailable.";

        const anomaly = data.ai_explanation?.anomaly || {};
        if (anomaly.anomaly_detected) {
            anomalyNote.textContent = `Anomaly score ${anomaly.anomaly_score || 0}: ${anomaly.root_pattern || "Detected"}`;
            anomalyNote.className = "text-danger";
        } else {
            anomalyNote.textContent = "No active anomalies detected.";
            anomalyNote.className = "text-muted";
        }

        const actions = data.ai_explanation?.actions || {};
        setActions(actions.actions || []);
        strategyText.textContent = actions.strategy || "--";
    };

    const fetchLatest = (machineId) => {
        const url = cfg.predictionUrl.replace("0", machineId);
        return apiFetch(url)
            .then((r) => r.json())
            .then((data) => {
                populateCards(data);
                return data;
            })
            .catch(() => {});
    };

    const fetchHistory = (machineId) => {
        const url = cfg.historyUrl.replace("0", machineId);
        return apiFetch(url)
            .then((r) => r.json())
            .then((data) => {
                renderTrend(data.history || []);
            })
            .catch(() => {});
    };

    const runPrediction = (machineId) => {
        const url = cfg.predictionUrl.replace("0", machineId);
        runBtn.disabled = true;
        runBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Running';
        apiFetch(url, { method: "POST" })
            .then((r) => r.json())
            .then((data) => {
                populateCards(data);
                return fetchHistory(machineId);
            })
            .catch(() => {})
            .finally(() => {
                runBtn.disabled = false;
                runBtn.textContent = "Run Prediction";
            });
    };

    const refresh = () => {
        const machineId = picker.value;
        if (!machineId) return;
        fetchLatest(machineId).then(() => fetchHistory(machineId));
    };

    picker.addEventListener("change", refresh);
    refreshBtn.addEventListener("click", refresh);
    runBtn.addEventListener("click", () => runPrediction(picker.value));

    refresh();
    setInterval(refresh, 45000);
})();
