(function () {
    const config = window.aiInsightsConfig || {};
    const latestUrl = config.latestUrl;
    if (!latestUrl) return;

    const gaugeCtx = document.getElementById("health-gauge");
    const scoreLabel = document.getElementById("health-score-label");
    const riskBadge = document.getElementById("risk-badge");
    const anomalyBanner = document.getElementById("anomaly-banner");
    const maintenanceText = document.getElementById("maintenance-text");
    const explanationText = document.getElementById("explanation-text");
    const updatedAt = document.getElementById("updated-at");
    const statusBadge = document.getElementById("analysis-status");

    const setMarkdown = (el, html, fallback) => {
        if (!el) return;
        if (html && html.trim()) {
            el.innerHTML = html;
        } else {
            el.textContent = fallback;
        }
    };

    let gaugeChart = null;

    const colorForScore = (score) => {
        if (score < 40) return "#dc3545";
        if (score < 70) return "#ffc107";
        return "#198754";
    };

    const renderGauge = (score) => {
        const primary = colorForScore(score);
        const secondary = "#e9ecef";
        const data = [score, Math.max(0, 100 - score)];
        if (gaugeChart) gaugeChart.destroy();
        gaugeChart = new Chart(gaugeCtx, {
            type: "doughnut",
            data: {
                labels: ["Health", "Remaining"],
                datasets: [
                    {
                        data,
                        backgroundColor: [primary, secondary],
                        borderWidth: 0,
                        cutout: "70%",
                    },
                ],
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
            },
        });
    };

    const setRiskBadge = (risk) => {
        const map = {
            low: "bg-success",
            medium: "bg-warning text-dark",
            high: "bg-danger",
        };
        riskBadge.className = `badge px-3 py-2 ${map[risk] || "bg-secondary"}`;
        riskBadge.textContent = risk ? risk.charAt(0).toUpperCase() + risk.slice(1) : "--";
    };

    const setAnomaly = (anomaly) => {
        if (anomaly) {
            anomalyBanner.className = "alert alert-danger d-block";
            anomalyBanner.textContent = "Anomaly detected by AI. Investigate immediately.";
        } else {
            anomalyBanner.className = "alert alert-success d-block";
            anomalyBanner.textContent = "No anomalies detected.";
        }
    };

    const setStatus = (status) => {
        const cls = {
            completed: "bg-success-subtle text-success",
            pending: "bg-warning-subtle text-warning",
            failed: "bg-danger-subtle text-danger",
        }[status] || "bg-secondary-subtle text-secondary";
        statusBadge.className = `badge ${cls}`;
        statusBadge.textContent = status ? status.charAt(0).toUpperCase() + status.slice(1) : "Unknown";
    };

    const applyData = (data) => {
        setStatus(data.status);

        if (data.status === "pending") {
            setMarkdown(maintenanceText, null, "AI is processing the latest telemetry...");
            setMarkdown(explanationText, null, "Awaiting results.");
            scoreLabel.textContent = "--";
            setRiskBadge(null);
            anomalyBanner.className = "alert alert-info d-block";
            anomalyBanner.textContent = "AI is running...";
            return;
        }

        if (data.status === "failed") {
            setMarkdown(
                maintenanceText,
                data.maintenance_suggestion_html,
                data.maintenance_suggestion || "AI failed to provide guidance."
            );
            setMarkdown(explanationText, data.explanation_html, data.explanation || "AI processing failed.");
            scoreLabel.textContent = "--";
            setRiskBadge(null);
            anomalyBanner.className = "alert alert-danger d-block";
            anomalyBanner.textContent = "AI analysis failed. Will retry on next ingestion.";
            return;
        }

        const score = Number(data.health_score || 0);
        renderGauge(score);
        scoreLabel.textContent = `${score.toFixed(1)}`;
        setRiskBadge(data.risk_level);
        setAnomaly(Boolean(data.anomaly));
        setMarkdown(
            maintenanceText,
            data.maintenance_suggestion_html,
            data.maintenance_suggestion || "No recommendation provided."
        );
        setMarkdown(explanationText, data.explanation_html, data.explanation || "No explanation provided.");
        updatedAt.textContent = `Analysis timestamp: ${data.timestamp || "—"}`;
    };

    const fetchLatest = () => {
        fetch(latestUrl, { cache: "no-store" })
            .then((res) => res.json())
            .then(applyData)
            .catch(() => {
                statusBadge.className = "badge bg-danger-subtle text-danger";
                statusBadge.textContent = "Error";
            });
    };

    fetchLatest();
    setInterval(fetchLatest, 8000);
})();
