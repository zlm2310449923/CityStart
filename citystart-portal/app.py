"""CityStart Portal (F).

Compliance with the CityStart Technical Baseline
-----------------------------------------------
§1.4  HTML + Bootstrap + JavaScript fetch only. No React/Vue.
§2    Portal listens on port 3000. The Gateway address comes from the
      API_GATEWAY_URL environment variable; no host or port is hard-coded in
      business logic.
§3.3  The Portal never touches a business database.
§4.6  Every error the Portal returns to the browser uses the unified
      {"error": {"code", "message", "details"}} envelope.
§5    The Portal may only call the API Gateway. There is deliberately no
      route that reaches Residence/Employment/Housing/Matching directly --
      an earlier debug bypass was removed to keep this invariant enforceable
      by inspection.
"""

import os

import httpx
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

API_GATEWAY_URL = os.environ.get("API_GATEWAY_URL", "http://localhost:8000").rstrip("/")
PORT = int(os.environ.get("PORT", "3000"))
GATEWAY_TIMEOUT_SECONDS = float(os.environ.get("GATEWAY_TIMEOUT_SECONDS", "30"))

# The Gateway is always a local/internal address. If the developer's machine
# has a system HTTP proxy configured (common with VPN or clash-style tools),
# httpx would route Gateway calls through it and a stopped Gateway would come
# back as the proxy's own non-JSON 502 rather than a connection failure. That
# turns a clear "Gateway is down" into a misleading "invalid response", so the
# proxy is bypassed for these calls unless explicitly re-enabled.
TRUST_ENV = os.environ.get("PORTAL_TRUST_ENV_PROXY", "0") == "1"

PAGES = {
    "/": ("index.html", None),
    "/citizen-profile": ("citizen_profile.html", None),
    "/residence-registration": ("residence_registration.html", None),
    "/residence-permit": ("residence_permit.html", None),
    "/employment-registration": ("employment_registration.html", None),
    "/employment-support": ("employment_support.html", None),
    "/housing-subsidy": ("housing_subsidy.html", None),
    "/service-recommendation": ("service_recommendation.html", None),
    "/application-status": ("application_status.html", None),
    "/process-analytics": ("process_analytics.html", None),
}


def _error(code, message, details=None, status=502):
    """Build a Baseline §4.6 compliant error envelope."""
    return jsonify({
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        }
    }), status


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/citizen-profile")
def citizen_profile():
    return render_template("citizen_profile.html")


@app.route("/residence-registration")
def residence_registration():
    return render_template("residence_registration.html")


@app.route("/residence-permit")
def residence_permit():
    return render_template("residence_permit.html")


@app.route("/employment-registration")
def employment_registration():
    return render_template("employment_registration.html")


@app.route("/employment-support")
def employment_support():
    return render_template("employment_support.html")


@app.route("/housing-subsidy")
def housing_subsidy():
    return render_template("housing_subsidy.html")


@app.route("/service-recommendation")
def service_recommendation():
    return render_template("service_recommendation.html")


@app.route("/application-status")
def application_status():
    return render_template("application_status.html")


@app.route("/process-analytics")
def process_analytics():
    return render_template("process_analytics.html")


@app.route("/healthz")
def healthz():
    """Liveness probe for E's integration checks."""
    return jsonify({
        "status": "ok",
        "service": "citystart-portal",
        "port": PORT,
        "gateway": API_GATEWAY_URL,
    })


@app.route("/api/proxy/<path:service_path>",
           methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
def proxy(service_path):
    """Forward a browser request to the API Gateway.

    This is the Portal's only outbound path (Baseline §5). The browser never
    contacts the Gateway directly, which keeps the Gateway free of CORS
    configuration and keeps the Portal as the single origin the user's browser
    talks to.

    Upstream errors are passed through unchanged so that the Gateway's unified
    error envelope reaches the browser intact. Only failures originating in the
    Portal itself (Gateway unreachable, timeout, non-JSON reply) are wrapped
    here, and they use the same envelope shape.
    """
    target_url = f"{API_GATEWAY_URL}/api/{service_path}"
    body = request.get_json(silent=True)

    try:
        with httpx.Client(timeout=GATEWAY_TIMEOUT_SECONDS, trust_env=TRUST_ENV) as client:
            response = client.request(
                request.method,
                target_url,
                params=request.args.to_dict(flat=True) or None,
                json=body if request.method not in ("GET", "DELETE") else None,
            )
    except httpx.TimeoutException:
        return _error(
            "GATEWAY_TIMEOUT",
            f"The API Gateway did not respond within {GATEWAY_TIMEOUT_SECONDS:.0f} seconds.",
            [{"target": target_url}],
            status=504,
        )
    except httpx.RequestError as exc:
        return _error(
            "GATEWAY_UNAVAILABLE",
            "The API Gateway could not be reached.",
            [{"target": target_url, "reason": type(exc).__name__}],
            status=503,
        )

    try:
        return jsonify(response.json()), response.status_code
    except ValueError:
        return _error(
            "GATEWAY_INVALID_RESPONSE",
            "The API Gateway returned a response that is not valid JSON.",
            [{"target": target_url,
              "upstream_status": response.status_code,
              "content_type": response.headers.get("content-type", "")}],
            status=502,
        )


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print(f"CityStart Portal -> http://localhost:{PORT}")
    print(f"API Gateway      -> {API_GATEWAY_URL}")
    app.run(host="0.0.0.0", port=PORT, debug=debug)
