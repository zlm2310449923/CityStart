# Residence Service

CityStart 的独立居住服务，负责 S1 居住登记和 S2 居住证申请。实现依据位于 `commend/requirements-design.md` 和 `commend/database-design.md`。

## 技术与数据

- Python 3.12、FastAPI、Pydantic v2、Uvicorn
- 默认端口：`8001`，可通过 `PORT` 修改
- SQLite 文件：默认 `data/residence.db`，可通过 `DATABASE_PATH` 修改
- 首次启动自动创建/迁移数据库
- 只保存材料元数据，不保存真实文件和敏感身份信息

数据库包含：

- `residence_registrations`
- `permit_applications`
- `application_documents`
- `status_history`
- `residence_permits`
- `permit_endorsements`

## 启动

```powershell
Copy-Item .env.example .env
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PORT='8001'
$env:DATABASE_PATH='data/residence.db'
python -m app.main
```

Swagger：<http://localhost:8001/docs>

也可以使用：

```powershell
python -m uvicorn app.main:app --reload --port 8001
```

## API

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/health` | 健康检查 |
| POST | `/residence-registrations` | 创建居住登记 |
| GET/PATCH/DELETE | `/residence-registrations/{citizen_id}` | 查询、变更或注销登记 |
| POST | `/residence-permit-applications` | 创建居住证申请并校验资格 |
| GET | `/residence-permit-applications/{application_id}` | 查询申请、材料、历史和证件 |
| POST | `/residence-permit-applications/{application_id}/documents` | 添加材料元数据 |
| PATCH | `/residence-permit-applications/{application_id}/status` | 按状态机更新审核状态 |
| GET | `/citizens/{citizen_id}/residence-status` | Gateway 使用的综合居住状态 |
| GET | `/citizens/{citizen_id}/permit-applications` | 查询公民全部申请 |
| POST | `/residence-permits/{permit_id}/endorsement` | 年度签注 |
| POST | `/residence-permits/{permit_id}/report-loss` | 挂失 |
| POST | `/residence-permits/{permit_id}/apply-reissue` | 创建补领申请 |
| POST | `/residence-permits/{permit_id}/e-permit` | 激活电子居住证 |
| POST | `/residence-permit-applications/{application_id}/check-eligibility` | 重新核验资格 |
| POST | `/residence-permit-applications/{application_id}/check-documents` | 检查材料完整性 |

申请审核状态机：

```text
pending → under_review → verification → approved
                    └→ additional_documents_required → under_review
pending / additional_documents_required / verification → rejected（按允许路径）
```

`verification → approved` 时自动生成状态为 `issued`、有效期一年的实体居住证。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

测试使用临时 SQLite 数据库，不修改本地开发数据库。

