/* CityStart Portal - shared client helpers.
 *
 * Baseline compliance:
 *   §1.4  Plain JavaScript with fetch(). No framework.
 *   §4.6  Errors are read from the unified envelope
 *           {"error": {"code", "message", "details"}}
 *         FastAPI's native {"detail": ...} shape is still tolerated so the
 *         Portal keeps working if a service has not yet been migrated.
 *   §5    All calls go through /api/proxy/ -> API Gateway. Never call a
 *         business service or database directly from the browser.
 */

const GATEWAY_PROXY = '/api/proxy/';

/* Baseline §4.5 status vocabulary. */
const STATUS_LABELS = {
    pending: { text: 'Pending', css: 'bg-secondary' },
    under_review: { text: 'Under Review', css: 'bg-info text-dark' },
    approved: { text: 'Approved', css: 'bg-success' },
    rejected: { text: 'Rejected', css: 'bg-danger' },
    additional_documents_required: {
        text: 'Additional Documents Required', css: 'bg-warning text-dark'
    }
};

function statusBadge(status) {
    if (!status) {
        return '<span class="status-badge badge bg-light text-dark">Not Started</span>';
    }
    const key = String(status).toLowerCase();
    const meta = STATUS_LABELS[key];
    if (meta) {
        return `<span class="status-badge badge ${meta.css}">${escapeHtml(meta.text)}</span>`;
    }
    return `<span class="status-badge badge bg-secondary">${escapeHtml(status)}</span>`;
}

function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
}

/* Extract a human-readable message from any error shape we might receive. */
function extractError(payload, httpStatus) {
    if (payload && payload.error && typeof payload.error === 'object') {
        const e = payload.error;
        let msg = e.message || e.code || 'Request failed.';
        if (Array.isArray(e.details) && e.details.length) {
            const parts = e.details.map(d => {
                if (typeof d === 'string') return d;
                if (d && d.field) return `${d.field}: ${d.message || 'invalid'}`;
                return JSON.stringify(d);
            });
            msg += ' (' + parts.join('; ') + ')';
        }
        return { code: e.code || 'ERROR', message: msg };
    }
    /* FastAPI default / Pydantic validation fallback. */
    if (payload && payload.detail !== undefined) {
        const d = payload.detail;
        if (Array.isArray(d)) {
            return {
                code: 'VALIDATION_ERROR',
                message: d.map(x => {
                    const loc = Array.isArray(x.loc) ? x.loc.slice(1).join('.') : '';
                    return loc ? `${loc}: ${x.msg}` : x.msg;
                }).join('; ')
            };
        }
        return { code: 'ERROR', message: String(d) };
    }
    return { code: 'ERROR', message: `Request failed with HTTP ${httpStatus}.` };
}

async function apiRequest(method, endpoint, { params, body } = {}) {
    const url = new URL(GATEWAY_PROXY + endpoint, window.location.origin);
    if (params) {
        Object.keys(params).forEach(k => {
            if (params[k] !== undefined && params[k] !== null && params[k] !== '') {
                url.searchParams.append(k, params[k]);
            }
        });
    }

    const options = { method, headers: { 'Accept': 'application/json' } };
    if (body !== undefined && method !== 'GET') {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(url.toString(), options);
        let payload = null;
        try {
            payload = await response.json();
        } catch (e) {
            payload = null;
        }
        if (!response.ok) {
            return { ok: false, status: response.status, data: payload,
                     error: extractError(payload, response.status) };
        }
        return { ok: true, status: response.status, data: payload, error: null };
    } catch (networkError) {
        return {
            ok: false, status: 0, data: null,
            error: { code: 'PORTAL_NETWORK_ERROR',
                     message: 'Could not reach the Portal server. ' + networkError.message }
        };
    }
}

const apiGet = (endpoint, params) => apiRequest('GET', endpoint, { params });
const apiPost = (endpoint, body) => apiRequest('POST', endpoint, { body });
const apiPatch = (endpoint, body) => apiRequest('PATCH', endpoint, { body });

function showAlert(containerId, message, type = 'success') {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = `<div class="alert alert-${type} alert-dismissible fade show" role="alert">
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>`;
}

/* Render an error result from apiRequest into an alert container. */
function showApiError(containerId, result, prefix = 'Request failed') {
    const err = result.error || { code: 'ERROR', message: 'Unknown error.' };
    showAlert(containerId,
        `<strong>${escapeHtml(prefix)}</strong> [${escapeHtml(err.code)}] ${escapeHtml(err.message)}`,
        'danger');
}

function setLoading(buttonId, loading = true) {
    const btn = document.getElementById(buttonId);
    if (!btn) return;
    if (loading) {
        if (!btn.dataset.originalHtml) btn.dataset.originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Working...';
    } else {
        btn.disabled = false;
        if (btn.dataset.originalHtml) btn.innerHTML = btn.dataset.originalHtml;
    }
}

/* Render a JSON payload for the query panels. */
function renderJson(containerId, data) {
    const c = document.getElementById(containerId);
    if (c) {
        c.innerHTML = `<pre class="bg-light p-3 rounded small mb-0">${escapeHtml(
            JSON.stringify(data, null, 2))}</pre>`;
    }
}

/* Baseline §4.2: timestamps arrive as ISO 8601 UTC (e.g. 2026-08-05T10:30:00Z). */
function formatTimestamp(value) {
    if (!value) return 'N/A';
    const d = new Date(value);
    return isNaN(d.getTime()) ? String(value) : d.toLocaleString();
}
