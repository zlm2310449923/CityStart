# CityStart

CityStart 是面向新市民居住、就业和住房事项的一站式服务课程原型。本仓库只包含可运行系统相关内容，各服务可独立开发、测试和启动。

## 模块

| 模块 | 端口 | 职责 | 数据 |
|---|---:|---|---|
| `citystart-portal` | 3000 | HTML/Bootstrap/JavaScript 用户入口 | 无 |
| `api-gateway` | 8000 | 路由、聚合、超时与统一错误处理 | 无 |
| `residence-service` | 8001 | 居住登记、居住证申请与补件 | `residence.db` |
| `employment-service` | 8002 | 就业登记与就业扶持申请 | `employment.db` |
| `housing-service` | 8003 | 住房补贴申请与资格核验 | `housing.db` |
| `service-matching-service` | 8004 | 规则型服务推荐 | 无状态 |

调用链固定为：`Citizen → Portal → API Gateway → Microservices`。Portal 不直接访问业务服务或数据库。

## 使用 Docker Compose 启动

```powershell
Copy-Item .env.example .env
docker compose up --build
```

启动后访问：

- Portal：<http://localhost:3000>
- Gateway Swagger：<http://localhost:8000/docs>
- 各服务 Swagger：端口 `8001` 至 `8004` 的 `/docs`

停止服务：

```powershell
docker compose down
```

## 本地独立启动

进入每个后端目录，安装该目录自己的依赖并运行：

```powershell
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8001
```

按模块修改端口为 `8002`、`8003`、`8004` 或 `8000`。Portal 在自身目录运行：

```powershell
python -m http.server 3000
```

也可以在各模块依赖安装完成后，从根目录运行 `./start_all.ps1`。

## API 约定

- 字段：`snake_case`
- 时间：ISO 8601 UTC
- 数据交换：JSON
- 状态：小写英文，例如 `pending`、`under_review`、`approved`
- 服务地址：通过环境变量配置
- 错误：`{"error":{"code":"...","message":"...","details":[]}}`

三个 SQLite 数据库由对应服务首次启动时自动初始化，不共享数据库。上传材料只保存模拟元数据，不保存真实敏感文件。

