const gateway = window.CITYSTART_CONFIG.gatewayUrl.replace(/\/$/, "");
const result = document.querySelector("#result");
const message = document.querySelector("#message");

async function callApi(path, options = {}) {
  message.className = "alert alert-info";
  message.textContent = "正在请求服务…";
  try {
    const response = await fetch(`${gateway}${path}`, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options
    });
    const data = await response.json();
    result.textContent = JSON.stringify(data, null, 2);
    message.className = response.ok ? "alert alert-success" : "alert alert-danger";
    message.textContent = response.ok ? "请求成功" : `请求失败（HTTP ${response.status}）`;
  } catch (error) {
    message.className = "alert alert-danger";
    message.textContent = "无法连接 API Gateway";
    result.textContent = JSON.stringify({ error: error.message }, null, 2);
  }
}

document.querySelector("#load-plan").addEventListener("click", () => {
  const citizenId = encodeURIComponent(document.querySelector("#citizen-id").value.trim());
  callApi(`/api/citizens/${citizenId}/service-plan`);
});

document.querySelector("#residence-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(event.target));
  callApi("/api/residence/residence-registrations", {
    method: "POST",
    body: JSON.stringify(values)
  });
});

