(() => {
  const cfg = window.ADV_REPORTS_CONFIG || {};
  const headers = cfg.accessToken ? { Authorization: `Bearer ${cfg.accessToken}` } : {};
  const qs = (id) => document.getElementById(id);
  const charts = {};

  const fetchJson = async (url, opts = {}) => {
    const resp = await fetch(url, { credentials: 'include', headers: { ...headers, ...(opts.headers || {}), 'Content-Type': 'application/json' }, ...opts });
    if (!resp.ok) throw new Error(`Request failed ${resp.status}`);
    return resp.json();
  };

  const parseFilename = (resp, fallback) => {
    const dispo = resp.headers.get('Content-Disposition') || '';
    const match = dispo.match(/filename="?([^";]+)"?/i);
    return match && match[1] ? match[1] : fallback;
  };

  const downloadBlob = (blob, filename) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const showError = (msg) => {
    const el = qs('reports-error');
    if (!el) return;
    el.textContent = msg;
    el.classList.remove('d-none');
  };

  const setStatus = (text, variant = 'secondary') => {
    const el = qs('report-status');
    if (el) {
      el.textContent = text;
      el.className = `badge bg-${variant}`;
    }
  };

  const buildChart = (id, config) => {
    const ctx = qs(id);
    if (!ctx) return;
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(ctx, config);
  };

  const renderTable = (items) => {
    const tbody = qs('report-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!items.length) {
      const tr = document.createElement('tr');
      tr.innerHTML = '<td colspan="5" class="text-center text-muted">No reports yet.</td>';
      tbody.appendChild(tr);
      return;
    }
    items.forEach((r) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${r.id}</td>
        <td>${r.report_type}</td>
        <td>${r.format}</td>
        <td>${r.generated_at ? new Date(r.generated_at).toLocaleString() : '--'}</td>
        <td class="text-end">
          <div class="btn-group btn-group-sm">
            <button class="btn btn-outline-primary" data-action="download" data-id="${r.id}" data-type="${r.report_type}" data-format="${r.format}">Download</button>
            <button class="btn btn-outline-secondary" data-action="preview" data-id="${r.id}" data-type="${r.report_type}" data-format="${r.format}">Preview</button>
            <button class="btn btn-outline-danger" data-action="delete" data-id="${r.id}">Delete</button>
          </div>
        </td>`;
      tbody.appendChild(tr);
    });
    tbody.querySelectorAll('button[data-action]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const id = e.currentTarget.dataset.id;
        const action = e.currentTarget.dataset.action;
        const type = e.currentTarget.dataset.type;
        const format = e.currentTarget.dataset.format;
        if (action === 'download') {
          downloadReport(id, type, format);
        } else if (action === 'preview') {
          previewReport(id, type, format);
        } else if (action === 'delete') {
          deleteReport(id);
        }
      });
    });
  };

  const renderCharts = (items) => {
    hideSpinner('freq-spinner');
    hideSpinner('type-spinner');
    if (!items.length) return;
    const freqMap = items.reduce((acc, r) => {
      const day = (r.generated_at || '').slice(0, 10);
      if (!day) return acc;
      acc[day] = (acc[day] || 0) + 1;
      return acc;
    }, {});
    const typeMap = items.reduce((acc, r) => {
      acc[r.report_type] = (acc[r.report_type] || 0) + 1;
      return acc;
    }, {});
    const freqLabels = Object.keys(freqMap).sort();
    buildChart('frequency-chart', {
      type: 'line',
      data: { labels: freqLabels, datasets: [{ label: 'Reports', data: freqLabels.map((k) => freqMap[k]), borderColor: '#0d6efd', backgroundColor: '#0d6efd33', tension: 0.3 }] },
      options: { responsive: true, maintainAspectRatio: false },
    });
    const typeLabels = Object.keys(typeMap);
    buildChart('type-chart', {
      type: 'pie',
      data: { labels: typeLabels, datasets: [{ data: typeLabels.map((k) => typeMap[k]), backgroundColor: ['#0d6efd', '#6f42c1', '#198754', '#fd7e14', '#20c997'] }] },
      options: { responsive: true, maintainAspectRatio: false },
    });
  };

  const regenerateAndDownload = async (reportType, format, alsoPreview = false) => {
    const payload = {
      report_type: reportType || 'predictive_maintenance',
      format: format || 'PDF',
      download_now: true,
    };
    const resp = await fetch(cfg.endpoints.generate, { method: 'POST', body: JSON.stringify(payload), headers: { ...headers, 'Content-Type': 'application/json' }, credentials: 'include' });
    if (!resp.ok) throw new Error(`Regenerate failed ${resp.status}`);
    const blob = await resp.blob();
    const ext = (payload.format || 'pdf').toLowerCase() === 'excel' ? 'xlsx' : (payload.format || 'pdf').toLowerCase();
    const fallbackName = `advanced-report-${payload.report_type || 'report'}.${ext}`;
    const filename = parseFilename(resp, fallbackName);
    if (alsoPreview) {
      const url = URL.createObjectURL(blob);
      const frame = qs('report-preview-frame');
      if (frame) frame.src = url;
      const modal = new bootstrap.Modal(document.getElementById('reportPreviewModal'));
      modal.show();
      downloadBlob(blob, filename);
      return;
    }
    downloadBlob(blob, filename);
  };

  const downloadReport = async (id, reportType, format) => {
    try {
      setStatus('Downloading…', 'info');
      const resp = await fetch(cfg.endpoints.downloadBase.replace('/0', `/${id}`), { headers, credentials: 'include' });
      if (!resp.ok) {
        await regenerateAndDownload(reportType, format, false);
      } else {
        const blob = await resp.blob();
        const filename = parseFilename(resp, `advanced-report-${id}.pdf`);
        downloadBlob(blob, filename);
      }
      setStatus('Ready', 'success');
    } catch (err) {
      showError(err.message);
      setStatus('Error', 'danger');
    }
  };

  const previewReport = async (id, reportType, format) => {
    try {
      const resp = await fetch(cfg.endpoints.downloadBase.replace('/0', `/${id}`), { headers, credentials: 'include' });
      if (!resp.ok) {
        await regenerateAndDownload(reportType, format, true);
      } else {
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const frame = qs('report-preview-frame');
        if (frame) frame.src = url;
        const modal = new bootstrap.Modal(document.getElementById('reportPreviewModal'));
        modal.show();
        downloadBlob(blob, parseFilename(resp, `advanced-report-${id}.pdf`));
      }
    } catch (err) {
      showError(err.message);
    }
  };

  const deleteReport = async (id) => {
    const confirmDelete = window.confirm('Delete this report? This cannot be undone.');
    if (!confirmDelete) return;
    try {
      setStatus('Deleting…', 'warning');
      const resp = await fetch(cfg.endpoints.deleteBase.replace('/0', `/${id}`), { method: 'DELETE', headers, credentials: 'include' });
      if (!resp.ok) throw new Error(`Delete failed ${resp.status}`);
      await loadReports();
      setStatus('Deleted', 'success');
    } catch (err) {
      showError(err.message);
      setStatus('Error', 'danger');
    }
  };

  const hideSpinner = (id) => { const el = qs(id); if (el) el.classList.add('d-none'); };

  const loadReports = async () => {
    const data = await fetchJson(cfg.endpoints.list);
    const items = data?.items || [];
    renderTable(items);
    renderCharts(items);
    setText('reports-updated', new Date().toLocaleTimeString());
  };

  const setText = (id, value) => { const el = qs(id); if (el) el.textContent = value; };

  const generateReport = async (evt) => {
    evt.preventDefault();
    try {
      setStatus('Generating…', 'info');
      const payload = {
        report_type: qs('report-type').value,
        format: qs('report-format').value,
        start_date: qs('start-date').value || undefined,
        end_date: qs('end-date').value || undefined,
        download_now: true,
      };
      const resp = await fetch(cfg.endpoints.generate, { method: 'POST', body: JSON.stringify(payload), headers: { ...headers, 'Content-Type': 'application/json' }, credentials: 'include' });
      if (!resp.ok) throw new Error(`Generate failed ${resp.status}`);
      const blob = await resp.blob();
      const ext = (payload.format || 'pdf').toLowerCase() === 'excel' ? 'xlsx' : (payload.format || 'pdf').toLowerCase();
      const fallbackName = `advanced-report-${payload.report_type || 'report'}.${ext}`;
      const filename = parseFilename(resp, fallbackName);
      downloadBlob(blob, filename);
      setStatus('Downloaded', 'success');
    } catch (err) {
      showError(err.message);
      setStatus('Error', 'danger');
    }
  };

  const bindEvents = () => {
    qs('report-form')?.addEventListener('submit', generateReport);
    qs('refresh-reports')?.addEventListener('click', () => loadReports().catch((e) => showError(e.message)));
  };

  const init = async () => {
    try {
      bindEvents();
      await loadReports();
    } catch (err) {
      showError(err.message);
    }
  };

  document.addEventListener('DOMContentLoaded', init);
})();
