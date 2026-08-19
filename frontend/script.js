/**
 * script.js — DataOps Monitor Dashboard
 * ----------------------------------------
 * Vanilla JavaScript frontend for the DataOps Monitor dashboard.
 * Uses fetch() to communicate with the FastAPI backend.
 * No external libraries required.
 */

const API_BASE = "http://127.0.0.1:8000";

// ID of the incident currently open in the modal
let activeIncidentId = null;

// Auto-refresh interval (30 seconds)
let autoRefreshInterval = null;

// ============================================================
// INIT — runs on page load
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
  loadDashboard();
  startAutoRefresh();
});

function startAutoRefresh() {
  if (autoRefreshInterval) clearInterval(autoRefreshInterval);
  autoRefreshInterval = setInterval(() => {
    loadDashboard();
  }, 30000);
}

// ============================================================
// MAIN DASHBOARD LOADER
// ============================================================
async function loadDashboard() {
  await Promise.all([
    loadStats(),
    loadPipelineRuns(),
    loadValidationResults(),
    loadIncidents(),
    checkApiHealth(),
  ]);
}

// ============================================================
// API HEALTH CHECK
// ============================================================
async function checkApiHealth() {
  const pill = document.getElementById("api-status");
  try {
    const res = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      pill.className = "status-pill online";
      pill.innerHTML = '<span class="status-dot"></span><span>API Online</span>';
    } else {
      throw new Error("non-ok");
    }
  } catch {
    pill.className = "status-pill offline";
    pill.innerHTML = '<span class="status-dot"></span><span>API Offline</span>';
  }
}

// ============================================================
// SUMMARY CARDS
// ============================================================
async function loadStats() {
  try {
    const data = await apiFetch("/api/stats");
    setText("stat-total",      data.total_runs);
    setText("stat-success",    data.successful);
    setText("stat-failed",     data.failed);
    setText("stat-incidents",  data.open_incidents);
    setText("stat-validation", data.validation_issues);
    setText("stat-records",    (data.total_records_processed || 0).toLocaleString());
  } catch (e) {
    console.error("Failed to load stats:", e);
  }
}

// ============================================================
// PIPELINE RUNS TABLE
// ============================================================
async function loadPipelineRuns() {
  const tbody = document.getElementById("runs-tbody");
  const countEl = document.getElementById("runs-count");
  try {
    const runs = await apiFetch("/api/pipeline-runs");
    countEl.textContent = `${runs.length} run${runs.length !== 1 ? "s" : ""}`;

    if (!runs.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No pipeline runs yet. Run a pipeline to get started.</td></tr>`;
      return;
    }

    tbody.innerHTML = runs.map(r => `
      <tr>
        <td class="mono">#${r.run_id}</td>
        <td>${escHtml(r.pipeline_name)}</td>
        <td class="mono">${formatDateTime(r.start_time)}</td>
        <td class="mono">${r.end_time ? formatDateTime(r.end_time) : "—"}</td>
        <td class="mono">${(r.records_processed || 0).toLocaleString()}</td>
        <td><span class="status-badge status-${r.status}">${r.status}</span></td>
        <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--danger);font-size:12px;"
            title="${escHtml(r.error_message || '')}">
          ${r.error_message ? truncate(r.error_message, 55) : '<span style="color:var(--text-muted)">—</span>'}
        </td>
      </tr>
    `).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-state">Could not load pipeline runs.</td></tr>`;
  }
}

// ============================================================
// VALIDATION RESULTS
// ============================================================
async function loadValidationResults() {
  const panel = document.getElementById("validation-panel");
  try {
    const results = await apiFetch("/api/validation-results");

    if (!results.length) {
      panel.innerHTML = `<p class="empty-state">Run a pipeline to see validation results.</p>`;
      return;
    }

    // Group by run_id (show most recent run at top)
    const grouped = {};
    results.forEach(r => {
      if (!grouped[r.run_id]) grouped[r.run_id] = [];
      grouped[r.run_id].push(r);
    });

    // Show only the last 3 runs to keep the panel clean
    const runIds = Object.keys(grouped).sort((a, b) => b - a).slice(0, 3);

    panel.innerHTML = runIds.map(runId => {
      const checks = grouped[runId];
      const passCount = checks.filter(c => c.status === "PASS").length;
      const failCount = checks.filter(c => c.status === "FAIL").length;

      return `
        <div class="validation-group">
          <div class="validation-group-title">
            Run #${runId} &nbsp;|&nbsp;
            <span style="color:var(--success)">✓ ${passCount} passed</span>
            &nbsp;
            ${failCount > 0 ? `<span style="color:var(--danger)">✗ ${failCount} failed</span>` : ""}
          </div>
          <div class="validation-grid">
            ${checks.map(c => `
              <div class="validation-card ${c.status === "PASS" ? "pass" : "fail"}">
                <div class="validation-card-header">
                  <span class="validation-check-name">${escHtml(c.check_name)}</span>
                  <span class="status-${c.status}">${c.status === "PASS" ? "✓ PASS" : "✗ FAIL"}</span>
                </div>
                <div class="validation-meta">
                  Expected: ${escHtml(c.expected_value || "—")}
                </div>
                <div class="validation-meta">
                  Actual: ${escHtml(c.actual_value || "—")}
                </div>
                <div class="validation-message">${escHtml(c.message || "")}</div>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }).join("");

  } catch (e) {
    panel.innerHTML = `<p class="empty-state">Could not load validation results.</p>`;
  }
}

// ============================================================
// INCIDENTS TABLE
// ============================================================
async function loadIncidents() {
  const tbody = document.getElementById("incidents-tbody");
  const countEl = document.getElementById("incidents-count");
  try {
    const incs = await apiFetch("/api/incidents");
    const open = incs.filter(i => i.status !== "RESOLVED").length;

    countEl.textContent = `${open} open`;
    countEl.className = open > 0 ? "badge badge-alert" : "badge badge-success";

    if (!incs.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No incidents. All pipelines are healthy.</td></tr>`;
      return;
    }

    tbody.innerHTML = incs.map(i => `
      <tr>
        <td><span style="font-family:'JetBrains Mono',monospace;font-weight:600;color:var(--accent-blue)">${escHtml(i.incident_id)}</span></td>
        <td>${escHtml(i.pipeline_name)}</td>
        <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escHtml(i.issue)}">
          ${escHtml(truncate(i.issue, 50))}
        </td>
        <td><span class="severity-${i.severity}">${i.severity}</span></td>
        <td><span class="status-badge status-${i.status}">${i.status}</span></td>
        <td class="mono" style="font-size:11px;">${formatDateTime(i.created_at)}</td>
        <td>
          <button class="btn-link" onclick="openIncidentModal('${i.incident_id}')">
            View / Update
          </button>
        </td>
      </tr>
    `).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-state">Could not load incidents.</td></tr>`;
  }
}

// ============================================================
// RUN PIPELINE
// ============================================================
async function runPipeline() {
  const select = document.getElementById("pipeline-select");
  const [pipelineName, filePath] = select.value.split("|");
  const btn = document.getElementById("btn-run-pipeline");
  const resultDiv = document.getElementById("run-result");

  // Show loading state
  btn.classList.add("loading");
  btn.innerHTML = '<span class="spinner"></span> Running...';
  resultDiv.style.display = "none";

  try {
    const result = await apiFetch("/api/run-pipeline", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pipeline_name: pipelineName, file_path: filePath }),
    });

    const status = result.status;
    const cssClass = status === "SUCCESS" ? "success" : status === "WARNING" ? "warning" : "failed";
    const icon = status === "SUCCESS" ? "✓" : status === "WARNING" ? "⚠" : "✗";

    let msg = `${icon} Pipeline: ${pipelineName}\n`;
    msg += `Status: ${status}\n`;
    msg += `Records Processed: ${(result.records_processed || 0).toLocaleString()}\n`;
    if (result.incident_id) msg += `Incident Created: ${result.incident_id}\n`;
    if (result.error_message) msg += `\nError: ${result.error_message}`;

    resultDiv.className = `run-result ${cssClass}`;
    resultDiv.textContent = msg;
    resultDiv.style.display = "block";

    showToast(
      status === "SUCCESS"
        ? `✓ ${pipelineName} completed successfully!`
        : status === "WARNING"
        ? `⚠ ${pipelineName} completed with warnings.`
        : `✗ ${pipelineName} failed. Incident created.`,
      cssClass
    );

    // Refresh all panels
    await loadDashboard();

  } catch (e) {
    resultDiv.className = "run-result failed";
    resultDiv.textContent = `✗ Could not connect to the API.\nMake sure the backend is running:\n  uvicorn backend.main:app --reload`;
    resultDiv.style.display = "block";
    showToast("Could not reach the API. Is the backend running?", "error");
  } finally {
    btn.classList.remove("loading");
    btn.innerHTML = "▶ Run Pipeline";
  }
}

// ============================================================
// INCIDENT MODAL
// ============================================================
async function openIncidentModal(incidentId) {
  activeIncidentId = incidentId;
  const modal  = document.getElementById("incident-modal");
  const overlay = document.getElementById("modal-overlay");

  try {
    const inc = await apiFetch(`/api/incidents/${incidentId}`);

    document.getElementById("modal-incident-id").textContent = inc.incident_id;

    // Populate meta info
    document.getElementById("modal-meta").innerHTML = `
      <div class="incident-meta-item">
        <span class="meta-label">Pipeline</span>
        <span class="meta-value">${escHtml(inc.pipeline_name)}</span>
      </div>
      <div class="incident-meta-item">
        <span class="meta-label">Severity</span>
        <span class="meta-value severity-${inc.severity}">${inc.severity}</span>
      </div>
      <div class="incident-meta-item" style="grid-column:1/-1">
        <span class="meta-label">Issue</span>
        <span class="meta-value" style="word-break:break-word;">${escHtml(inc.issue)}</span>
      </div>
      <div class="incident-meta-item">
        <span class="meta-label">Created</span>
        <span class="meta-value">${formatDateTime(inc.created_at)}</span>
      </div>
      <div class="incident-meta-item">
        <span class="meta-label">Last Updated</span>
        <span class="meta-value">${formatDateTime(inc.updated_at)}</span>
      </div>
      ${inc.resolution ? `
      <div class="incident-meta-item" style="grid-column:1/-1">
        <span class="meta-label">Resolution</span>
        <span class="meta-value" style="color:var(--success);word-break:break-word;">${escHtml(inc.resolution)}</span>
      </div>` : ""}
    `;

    // Pre-select current values
    document.getElementById("modal-status").value   = inc.status;
    document.getElementById("modal-severity").value = inc.severity;
    document.getElementById("modal-notes").value    = "";
    document.getElementById("modal-resolution").value = inc.resolution || "";

    // Show existing work notes
    const notesHistory = document.getElementById("modal-notes-history");
    if (inc.work_notes) {
      notesHistory.style.display = "block";
      notesHistory.textContent = inc.work_notes;
    } else {
      notesHistory.style.display = "none";
    }

    modal.classList.add("active");
    overlay.classList.add("active");

  } catch (e) {
    showToast("Could not load incident details.", "error");
  }
}

function closeModal() {
  document.getElementById("incident-modal").classList.remove("active");
  document.getElementById("modal-overlay").classList.remove("active");
  activeIncidentId = null;
}

async function submitIncidentUpdate() {
  if (!activeIncidentId) return;

  const status     = document.getElementById("modal-status").value;
  const severity   = document.getElementById("modal-severity").value;
  const work_notes = document.getElementById("modal-notes").value.trim();
  const resolution = document.getElementById("modal-resolution").value.trim();
  const btn        = document.getElementById("btn-update-incident");

  btn.classList.add("loading");
  btn.textContent = "Updating...";

  try {
    await apiFetch(`/api/incidents/${activeIncidentId}/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status:      status || null,
        severity:    severity || null,
        work_notes:  work_notes || null,
        resolution:  resolution || null,
      }),
    });

    showToast(`✓ Incident ${activeIncidentId} updated to ${status}.`, "success");
    closeModal();
    await loadDashboard();

  } catch (e) {
    showToast("Failed to update incident.", "error");
  } finally {
    btn.classList.remove("loading");
    btn.textContent = "Update Incident";
  }
}

// ============================================================
// OPERATIONAL REPORT
// ============================================================
async function generateReport() {
  const panel = document.getElementById("report-panel");
  const btn   = document.getElementById("btn-report");

  btn.textContent = "Generating...";
  btn.disabled = true;

  try {
    const report = await apiFetch("/api/report");
    panel.innerHTML = `<pre class="report-text">${escHtml(report.text_report)}</pre>`;
    showToast("Daily report generated.", "success");
  } catch (e) {
    panel.innerHTML = `<p class="empty-state">Could not generate report. Is the backend running?</p>`;
    showToast("Failed to generate report.", "error");
  } finally {
    btn.textContent = "Generate Report";
    btn.disabled = false;
  }
}

// ============================================================
// HELPERS
// ============================================================

/**
 * Fetch wrapper that always returns parsed JSON or throws.
 */
async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${path} returned ${res.status}: ${err}`);
  }
  return res.json();
}

/**
 * Set the text content of an element by ID safely.
 */
function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value ?? "—";
}

/**
 * Escape HTML to prevent XSS when rendering user data.
 */
function escHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * Truncate a string to maxLen characters.
 */
function truncate(str, maxLen) {
  if (!str) return "";
  return str.length > maxLen ? str.slice(0, maxLen) + "…" : str;
}

/**
 * Format an ISO datetime string into a readable local time.
 */
function formatDateTime(dtStr) {
  if (!dtStr) return "—";
  try {
    // SQLite stores UTC without 'Z', so append it for correct parsing
    const clean = dtStr.replace(" ", "T") + (dtStr.endsWith("Z") ? "" : "Z");
    const d = new Date(clean);
    return d.toLocaleString("en-IN", {
      month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit", hour12: false,
    });
  } catch {
    return dtStr;
  }
}

/**
 * Show a toast notification at the bottom-right corner.
 */
function showToast(message, type = "default") {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = `toast ${type} show`;
  setTimeout(() => { toast.className = "toast"; }, 4000);
}
