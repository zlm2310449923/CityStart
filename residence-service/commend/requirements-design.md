# Residence Service 需求设计文档

> **版本**: v1.0  
> **日期**: 2026-08-06  
> **负责人**: B (Residence Service Developer)  
> **服务定位**: 居住登记与居住证申请管理微服务  
> **参考来源**: 《武汉市居住证服务与管理办法》(2024修订)、湖北公安政务服务平台办事指南、项目任务分配文档

---

## 目录

1. [业务背景与真实流程](#1-业务背景与真实流程)
2. [服务边界与定位](#2-服务边界与定位)
3. [功能需求详细设计](#3-功能需求详细设计)
4. [API接口设计](#4-api接口设计)
5. [状态机与工作流](#5-状态机与工作流)
6. [业务规则](#6-业务规则)
7. [事件日志模拟场景](#7-事件日志模拟场景)
8. [非功能性需求](#8-非功能性需求)
9. [附录：真实官方流程对照](#9-附录真实官方流程对照)

---

## 1. 业务背景与真实流程

### 1.1 政策依据

Residence Service 以武汉市真实的居住证办理流程为业务参考。依据《武汉市居住证服务与管理暂行办法》（2017年公布，2024年5月9日武汉市人民政府令第322号第二次修改，自2024年7月1日起施行）：

- **居住登记**（S1）：非本市户籍公民自到达居住地之日起**7日内**，向公安机关或受委托的社区服务机构申报居住登记。
- **居住证申领**（S2）：居住登记满半年后（或满足社保/就学/就业/结婚等放宽条件），可申领居住证。受理后**15个工作日内**发放。
- **签注续期**：居住证有效期为1年，每年签注1次，应在期满前1个月内办理。
- **电子居住证**：实体居住证申领成功1个工作日后，可在湖北公安政务服务平台领取电子居住证，具有同等法律效力。

### 1.2 真实办理流程（公安部门）

以下是真实世界中武汉居住证申领的完整流程，本项目 P1 BPMN 流程以此为基础建模：

```
Step 1: 申请人提交居住登记（线上/线下）
  ├─ 线上：湖北政务服务网 / 湖北公安政务服务平台
  └─ 线下：社区流管站 / 公安派出所

Step 2: 居住登记审核
  ├─ 材料齐全 → 登记成功，开始计算登记时长
  └─ 材料不全 → 一次性告知补正材料

Step 3: 居住登记满半年（或满足放宽条件）
  └─ 申请人提交居住证申领

Step 4: 受理与材料核验
  ├─ 窗口受理人员初步审查材料完整性
  │   ├─ 材料齐全 → 受理，转社区民警核实
  │   └─ 材料不全 → 一次性告知需补正的全部材料
  ├─ 社区民警核实材料真实性
  │   ├─ 必要时实地走访调查居住情况
  │   └─ 将申领人信息录入派出所基础工作管理系统
  └─ 材料上传至基础管理系统

Step 5: 呈批与逐级审批
  ├─ 社区民警签署核实意见 → 派出所领导审核（1个工作日）
  ├─ 派出所领导审核通过 → 分（县市）局审批
  └─ 分（县市）局审批签发 → 制证（2个工作日）

Step 6: 发放与归档
  ├─ 证件发放至原受理窗口
  ├─ 通知申领人携带有效证件领取
  ├─ 申领人签字确认领取
  └─ 一人一档归档保存
```

### 1.3 本项目简化建模

本系统为课程原型系统，在保留核心业务逻辑的基础上做以下简化：

| 真实流程要素 | 本系统处理方式 |
|---|---|
| 公安内网系统（派出所基础工作管理系统） | 本地 SQLite 数据库 |
| 社区民警实地走访 | 模拟为系统自动核验状态流转 |
| 逐级审批（社区民警→派出所领导→分局） | 简化为 `under_review → approved/rejected` |
| 实体IC卡制证与发放 | 模拟为状态标记 `issued` |
| 电子居住证申领 | 独立接口，1个工作日后可申领 |
| 签注续期（线下办理） | 独立接口，模拟签注流程 |
| 一人一档归档 | 数据库记录归档 |

---

## 2. 服务边界与定位

### 2.1 服务职责

Residence Service 负责 CityStart 平台中与**居住**相关的全部业务逻辑，涵盖两个核心服务：

| 服务编号 | 服务名称 | 提供者 |
|---|---|---|
| S1 | 居住登记 (Residence Registration) | 公安政务部门 |
| S2 | 居住证申请 (Residence Permit Application) | 公安政务部门 |

### 2.2 与其他服务的交互

```
                    ┌─────────────────────┐
                    │   API Gateway        │
                    │   (Port 8000)        │
                    └──────┬──────────────┘
                           │ HTTPX
          ┌────────────────┼──────────────────┐
          │                │                  │
          ▼                ▼                  ▼
  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
  │ Residence    │ │ Employment   │ │ Housing      │
  │ Service:8001 │ │ Service:8002 │ │ Service:8003 │
  └──────┬───────┘ └──────────────┘ └──────┬───────┘
         │                                 │
         │  ┌──────────────────────────┐   │
         └──│ Service Matching:8004    │───┘
            │ (stateless, 无数据库)     │
            └──────────────────────────┘
```

- **Residence Service → Matching Service**：Matching Service 通过 Gateway 调用 Residence Service 的 `/citizens/{citizen_id}/residence-status` 获取居住状态，作为服务推荐的输入条件。
- **Residence Service → Housing Service**：Housing Service 在资格核验时可能需要确认申请人的居住状态（通过 Gateway 中转）。
- **无直接数据库共享**：各服务独立管理自己的 SQLite 数据库。

### 2.3 不做什么

- **不做**真实身份认证（身份证号联网核查）
- **不做**公安内网系统对接
- **不做**实体IC卡制作与物流跟踪
- **不做**复杂的权限体系（如民警 vs 派出所领导的多角色审批）
- **不做**真实文件上传与存储（仅记录 document_id 及元数据）

---

## 3. 功能需求详细设计

### 3.1 功能全景

```
Residence Service
├── 居住登记管理 (S1)
│   ├── F1.1  创建居住登记
│   ├── F1.2  查询居住登记
│   ├── F1.3  更新居住登记信息（地址变更）
│   └── F1.4  注销居住登记
│
├── 居住证申请管理 (S2)
│   ├── F2.1  创建居住证申请
│   ├── F2.2  查询居住证申请详情
│   ├── F2.3  补充/上传申请材料
│   ├── F2.4  更新申请审核状态
│   ├── F2.5  查询公民居住综合状态
│   ├── F2.6  居住证签注（续期）
│   ├── F2.7  居住证挂失与补领
│   └── F2.8  电子居住证申领
│
├── 资格核验与规则
│   ├── F3.1  居住证申领资格判断
│   ├── F3.2  材料完整性检查
│   └── F3.3  放宽条件资格判断
│
└── 系统功能
    ├── F4.1  健康检查
    └── F4.2  申请列表查询（按公民ID）
```

### 3.2 功能详细描述

---

#### F1.1 创建居住登记

| 属性 | 说明 |
|---|---|
| **描述** | 为非本市户籍公民创建流动人口居住登记记录 |
| **前置条件** | citizen_id 有效且未重复登记 |
| **触发方式** | 公民通过 Portal 提交居住登记表单，Gateway 转发至本服务 |
| **输入** | citizen_id, residential_address, residence_start_date, 可选 contact_phone |
| **处理逻辑** | 1. 校验 citizen_id 是否已有有效居住登记<br>2. 若已存在则返回 409 Conflict<br>3. 验证地址和日期字段非空<br>4. 生成 registration_id (UUID)<br>5. 自动设置状态为 `approved`（模拟自动通过）<br>6. 记录 created_at / updated_at |
| **输出** | 完整的居住登记记录 JSON |
| **异常** | 409: 已存在居住登记; 422: 参数校验失败 |
| **后置条件** | residence_registered = true，居住登记计时开始 |

---

#### F1.2 查询居住登记

| 属性 | 说明 |
|---|---|
| **描述** | 根据 citizen_id 查询该公民的居住登记信息 |
| **前置条件** | 公民已完成居住登记 |
| **触发方式** | Portal 查询 / Gateway 服务组合 / Matching Service 调用 |
| **输入** | citizen_id (路径参数) |
| **输出** | registration_id, citizen_id, residential_address, residence_start_date, status, registration_days (登记天数), created_at, updated_at |
| **异常** | 404: 未找到居住登记 |
| **业务价值** | 为其他服务提供居住状态判断依据 |

---

#### F1.3 更新居住登记信息

| 属性 | 说明 |
|---|---|
| **描述** | 当公民居住地址变更时，更新居住登记信息 |
| **前置条件** | 已存在有效的居住登记 |
| **业务规则** | 真实流程要求在地址变更后3日内办理信息变更 |
| **输入** | residential_address（可选）, contact_phone（可选） |
| **输出** | 更新后的居住登记记录 |
| **异常** | 404: 未找到居住登记 |

---

#### F1.4 注销居住登记

| 属性 | 说明 |
|---|---|
| **描述** | 公民搬离本市或其他原因需注销居住登记 |
| **前置条件** | 已存在居住登记 |
| **输入** | cancel_reason（注销原因） |
| **输出** | 注销确认 |
| **业务规则** | 注销后，关联的居住证申请如仍在办理中应同步更新状态 |
| **异常** | 404: 未找到居住登记 |

---

#### F2.1 创建居住证申请

| 属性 | 说明 |
|---|---|
| **描述** | 公民提交居住证申领请求 |
| **前置条件** | 1. 公民已完成居住登记（residence_registered = true）<br>2. 满足申领条件（登记满半年 或 满足放宽条件） |
| **触发方式** | 公民通过 Portal 提交申请 |
| **输入** | citizen_id, 可选: application_reason（申领理由）, is_express（是否加急） |
| **处理逻辑** | 1. 查询该公民居住登记是否存在<br>2. 计算居住登记天数<br>3. 若不满足半年条件，检查是否符合放宽条件<br>4. 若均不满足，返回 400 并说明原因<br>5. 生成 application_id (UUID)<br>6. 初始状态为 `pending`<br>7. 记录 submitted_at / updated_at |
| **输出** | 申请记录 JSON（含 application_id, status, eligibility_check_result） |
| **异常** | 400: 不满足申领条件; 404: 未找到居住登记 |
| **后置条件** | 居住证申请进入待审核队列 |

---

#### F2.2 查询居住证申请详情

| 属性 | 说明 |
|---|---|
| **描述** | 根据 application_id 查询申请完整信息，含已上传的材料列表 |
| **输入** | application_id (路径参数) |
| **输出** | 完整的申请记录 + 材料列表 + 状态历史 |
| **异常** | 404: 未找到申请 |

---

#### F2.3 补充/上传申请材料

| 属性 | 说明 |
|---|---|
| **描述** | 为居住证申请上传/补充材料 |
| **前置条件** | 申请存在且状态允许上传（pending / additional_documents_required） |
| **输入** | document_type, file_name（模拟，不存实际文件内容） |
| **处理逻辑** | 1. 校验申请是否存在<br>2. 校验申请状态是否允许上传<br>3. 生成 document_id (UUID)<br>4. 记录 document_type, file_name, verification_status=pending<br>5. 记录 uploaded_at |
| **支持的材料类型** | identity_document（身份证）、residence_proof（居住证明）、employment_proof（就业证明）、enrollment_proof（在读证明）、social_security_record（社保证明）、marriage_certificate（结婚证）、application_form（申请表）、other（其他） |
| **输出** | 材料记录 JSON |
| **异常** | 404: 申请不存在; 400: 状态不允许上传 |

---

#### F2.4 更新申请审核状态

| 属性 | 说明 |
|---|---|
| **描述** | 公安部门审核人员更新居住证申请的审核状态 |
| **输入** | status（目标状态）, 可选: reviewer_comment（审核意见）, reviewer_id（审核人ID） |
| **状态转换规则** | 见 [5. 状态机与工作流](#5-状态机与工作流) |
| **输出** | 更新后的完整申请记录 |
| **异常** | 404: 申请不存在; 400: 非法状态转换 |

---

#### F2.5 查询公民居住综合状态

| 属性 | 说明 |
|---|---|
| **描述** | 聚合查询某公民在居住维度的完整状态，供 Gateway/Matching Service 使用 |
| **输入** | citizen_id |
| **输出** | `{ citizen_id, residence_registered: bool, residence_permit_approved: bool, registration: {...}, permit_applications: [...], current_permit: {...} }` |
| **用途** | Matching Service 的推荐规则依赖此接口判断居住状态 |

---

#### F2.6 居住证签注（续期）

| 属性 | 说明 |
|---|---|
| **描述** | 已持有有效居住证的公民办理年度签注续期 |
| **前置条件** | 持有 approved 状态的居住证 |
| **输入** | permit_id, current_address |
| **处理逻辑** | 1. 校验当前居住证是否存在且有效<br>2. 判断是否在签注时间窗口内（到期前1个月）<br>3. 创建签注记录<br>4. 更新居住证有效期至下一年<br>5. 更新 updated_at |
| **输出** | 更新后的居住证记录 |
| **异常** | 404: 居住证不存在; 400: 不在签注窗口内 |

---

#### F2.7 居住证挂失与补领

| 属性 | 说明 |
|---|---|
| **描述** | 实体居住证丢失后办理挂失，并申请补领 |
| **输入** | permit_id, action: `report_loss`（挂失）/ `apply_reissue`（补领） |
| **处理逻辑** | 挂失：标记居住证为 lost 状态，记录挂失时间<br>补领：创建新的补领申请，与原居住证关联 |
| **输出** | 更新后的记录 |
| **备注** | 真实流程中电子居住证在有效期内仍可使用 |

---

#### F2.8 电子居住证申领

| 属性 | 说明 |
|---|---|
| **描述** | 实体居住证审核通过后，申领同等效力的电子居住证 |
| **前置条件** | 实体居住证状态为 approved 且距审批通过满1个工作日 |
| **输入** | permit_id |
| **处理逻辑** | 1. 校验实体居住证状态<br>2. 校验时间是否满足1个工作日条件<br>3. 生成电子居住证记录（e_permit_id）<br>4. 标记 is_e_permit_active = true |
| **输出** | 电子居住证信息 |
| **异常** | 400: 不满足申领时间条件 |

---

#### F3.1 居住证申领资格判断

| 属性 | 说明 |
|---|---|
| **描述** | 判断某公民是否具备申领居住证的资格 |
| **规则** | 见 [6. 业务规则](#6-业务规则) |

---

#### F3.2 材料完整性检查

| 属性 | 说明 |
|---|---|
| **描述** | 基于申请类型，检查已上传材料是否满足基本要求 |
| **必需材料清单** | - 身份证 (identity_document)：必须<br>- 居住证明 (residence_proof)：必须<br>- 补充证明（满足放宽条件时）：社保证明/在读证明/就业证明/结婚证（至少一项） |
| **输出** | `{ is_complete: bool, missing_documents: [...], optional_documents: [...] }` |

---

## 4. API接口设计

### 4.1 接口总览

| 方法 | 路径 | 功能 | 编号 |
|---|---|---|---|
| GET | `/health` | 健康检查 | - |
| POST | `/residence-registrations` | 创建居住登记 | API-R01 |
| GET | `/residence-registrations/{citizen_id}` | 查询居住登记 | API-R02 |
| PATCH | `/residence-registrations/{citizen_id}` | 更新居住登记 | API-R03 |
| DELETE | `/residence-registrations/{citizen_id}` | 注销居住登记 | API-R04 |
| POST | `/residence-permit-applications` | 创建居住证申请 | API-R05 |
| GET | `/residence-permit-applications/{application_id}` | 查询申请详情 | API-R06 |
| POST | `/residence-permit-applications/{application_id}/documents` | 上传材料 | API-R07 |
| PATCH | `/residence-permit-applications/{application_id}/status` | 更新审核状态 | API-R08 |
| GET | `/citizens/{citizen_id}/residence-status` | 查询居住综合状态 | API-R09 |
| GET | `/citizens/{citizen_id}/permit-applications` | 查询公民所有申请 | API-R10 |
| POST | `/residence-permits/{permit_id}/endorsement` | 居住证签注 | API-R11 |
| POST | `/residence-permits/{permit_id}/report-loss` | 居住证挂失 | API-R12 |
| POST | `/residence-permits/{permit_id}/apply-reissue` | 居住证补领 | API-R13 |
| POST | `/residence-permits/{permit_id}/e-permit` | 申领电子居住证 | API-R14 |
| POST | `/residence-permit-applications/{application_id}/check-eligibility` | 资格判断 | API-R15 |
| POST | `/residence-permit-applications/{application_id}/check-documents` | 材料完整性检查 | API-R16 |

### 4.2 详细接口定义

#### API-R01: POST /residence-registrations

```
Request:
{
  "citizen_id": "C001",
  "residential_address": "武汉市洪山区珞喻路1037号",
  "residence_start_date": "2026-08-01",
  "contact_phone": "13800138000"        // 可选
}

Response 201:
{
  "registration_id": "550e8400-e29b-41d4-a716-446655440000",
  "citizen_id": "C001",
  "residential_address": "武汉市洪山区珞喻路1037号",
  "residence_start_date": "2026-08-01",
  "contact_phone": "13800138000",
  "status": "approved",
  "registration_days": 0,
  "created_at": "2026-08-06T10:30:00Z",
  "updated_at": "2026-08-06T10:30:00Z"
}

Error 409:
{
  "error": {
    "code": "DUPLICATE_REGISTRATION",
    "message": "该公民已存在有效的居住登记",
    "details": []
  }
}
```

---

#### API-R05: POST /residence-permit-applications

```
Request:
{
  "citizen_id": "C001",
  "application_reason": "就业",          // 可选
  "is_express": false                   // 可选，是否加急
}

Response 201:
{
  "application_id": "660e8400-e29b-41d4-a716-446655440001",
  "citizen_id": "C001",
  "status": "pending",
  "registration_days": 185,
  "eligibility": {
    "is_eligible": true,
    "reason": "居住登记已满半年",
    "meets_shortcut": false
  },
  "submitted_at": "2026-08-06T10:30:00Z",
  "updated_at": "2026-08-06T10:30:00Z"
}

Error 400 (不满足条件):
{
  "error": {
    "code": "NOT_ELIGIBLE",
    "message": "不满足居住证申领条件：居住登记未满半年且不满足放宽条件",
    "details": {
      "registration_days": 120,
      "requires_days": 183,
      "shortcut_conditions_met": []
    }
  }
}
```

---

#### API-R08: PATCH /residence-permit-applications/{application_id}/status

```
Request:
{
  "status": "under_review",
  "reviewer_id": "REV001",              // 可选
  "reviewer_comment": "材料齐全，转社区民警核实"   // 可选
}

Response 200:
{
  "application_id": "...",
  "status": "under_review",
  "previous_status": "pending",
  "status_history": [
    { "status": "pending", "timestamp": "2026-08-06T10:30:00Z" },
    { "status": "under_review", "timestamp": "2026-08-06T10:35:00Z", "reviewer_id": "REV001", "comment": "材料齐全，转社区民警核实" }
  ],
  "updated_at": "2026-08-06T10:35:00Z"
}

Error 400 (非法状态转换):
{
  "error": {
    "code": "INVALID_STATUS_TRANSITION",
    "message": "不允许从 approved 转换为 under_review",
    "details": {
      "current_status": "approved",
      "allowed_transitions": []
    }
  }
}
```

---

#### API-R15: POST /residence-permit-applications/{application_id}/check-eligibility

```
Response 200:
{
  "application_id": "...",
  "citizen_id": "C001",
  "is_eligible": true,
  "registration_days": 185,
  "meets_basic_condition": true,       // 居住登记满半年
  "meets_shortcut_conditions": [        // 满足的放宽条件列表
    {
      "condition": "employment",
      "description": "持有有效就业证明且连续就业超过6个月",
      "met": true
    }
  ],
  "missing_requirements": []
}
```

---

#### API-R16: POST /residence-permit-applications/{application_id}/check-documents

```
Response 200:
{
  "application_id": "...",
  "is_complete": false,
  "required_documents": [
    { "type": "identity_document", "name": "身份证", "uploaded": true },
    { "type": "residence_proof", "name": "居住证明", "uploaded": false }
  ],
  "optional_documents": [
    { "type": "employment_proof", "name": "就业证明", "uploaded": true }
  ],
  "missing_documents": ["residence_proof"],
  "suggestion": "请上传居住证明材料（房屋租赁合同/产权证明/购房合同/住宿证明）"
}
```

---

### 4.3 统一错误格式

所有错误响应遵循项目统一规范：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": []
  }
}
```

本服务定义的错误码：

| 错误码 | HTTP状态码 | 说明 |
|---|---|---|
| `VALIDATION_ERROR` | 422 | 请求参数校验失败 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `DUPLICATE_REGISTRATION` | 409 | 已存在居住登记 |
| `NOT_ELIGIBLE` | 400 | 不满足申领条件 |
| `INVALID_STATUS_TRANSITION` | 400 | 非法状态转换 |
| `DOCUMENT_UPLOAD_DENIED` | 400 | 当前状态不允许上传材料 |
| `ENDORSEMENT_NOT_DUE` | 400 | 不在签注时间窗口内 |
| `E_PERMIT_NOT_READY` | 400 | 电子居住证申领条件未满足 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

---

## 5. 状态机与工作流

### 5.1 居住证申请状态机

```
                    ┌──────────────┐
                    │   pending    │  ← 初始状态（申请已提交）
                    └──────┬───────┘
                           │ 受理
                           ▼
                ┌──────────────────┐
                │  under_review    │  ← 材料审核中
                └──┬───────────┬───┘
                   │           │
        材料不全   │           │ 材料齐全
                   ▼           ▼
   ┌──────────────────────┐  ┌──────────────────┐
   │ additional_documents │  │   verification   │  ← 信息核验中
   │      _required       │  └────────┬─────────┘
   └──────────┬───────────┘           │
              │ 公民补交材料           ├──────────────┐
              ▼                       │              │
         回到 under_review            ▼              ▼
                           ┌──────────────┐  ┌──────────┐
                           │   approved   │  │ rejected │
                           └──────┬───────┘  └──────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │  issued  │ │ expired  │ │  lost    │
              └──────────┘ └──────────┘ └────┬─────┘
                                             │
                                             ▼
                                       ┌──────────┐
                                       │reissued  │
                                       └──────────┘
```

### 5.2 状态转换规则表

| 当前状态 | 允许转换为 | 触发条件 |
|---|---|---|
| `pending` | `under_review` | 审核人员受理 |
| `pending` | `rejected` | 明显不符合条件，直接拒绝 |
| `under_review` | `additional_documents_required` | 材料不全 |
| `under_review` | `verification` | 材料齐全，进入核实阶段 |
| `additional_documents_required` | `under_review` | 公民补交材料后重新进入审核 |
| `additional_documents_required` | `rejected` | 逾期未补交或补交后仍不符合要求 |
| `verification` | `approved` | 核验通过 |
| `verification` | `rejected` | 核验不通过 |
| `approved` | `issued` | 证件发放 |
| `issued` | `expired` | 有效期届满未签注 |
| `issued` | `lost` | 公民申报挂失 |
| `lost` | `reissued` | 补领完成 |

### 5.3 签注状态流程

```
issued ──(到期前1个月)──→ 可办理签注
   │
   ├── 正常签注 → 有效期延长1年
   │
   └── 逾期未签注 → expired（居住年限重新计算）
```

---

## 6. 业务规则

### 6.1 居住证申领资格规则（核心）

```
Rule: ELIGIBILITY_CHECK

输入:
  - registration_days: 居住登记天数
  - has_social_security_6m: 是否连续缴纳社保满6个月
  - is_enrolled_6m: 是否连续就读满6个月
  - is_employed_6m: 是否连续就业满6个月
  - is_married_to_local_6m: 是否与本地户籍人员结婚满半年

输出:
  - is_eligible: bool
  - reason: string
  - meets_basic: bool (登记满半年)
  - meets_shortcut: bool (满足放宽条件)

规则:
  IF registration_days >= 183 THEN
    is_eligible = true, reason = "居住登记已满半年"
  ELSE IF has_social_security_6m THEN
    is_eligible = true, reason = "连续缴纳社保满6个月，适用放宽条件"
  ELSE IF is_enrolled_6m THEN
    is_eligible = true, reason = "连续就读满6个月，适用放宽条件"
  ELSE IF is_employed_6m THEN
    is_eligible = true, reason = "连续就业满6个月，适用放宽条件"
  ELSE IF is_married_to_local_6m THEN
    is_eligible = true, reason = "与本地户籍人员结婚满半年，适用放宽条件"
  ELSE
    is_eligible = false, reason = "不满足申领条件"
```

### 6.2 材料完整性规则

```
Rule: DOCUMENT_COMPLETENESS

必需材料（所有申请）:
  - identity_document（身份证）
  - residence_proof（居住证明）

放宽条件补充材料（满足任一即可）:
  - 社保路径: social_security_record
  - 就学路径: enrollment_proof
  - 就业路径: employment_proof
  - 婚姻路径: marriage_certificate + spouse_id_document

最小材料集合:
  basic_set = [identity_document, residence_proof]
  shortcut_set = [social_security_record | enrollment_proof | employment_proof | marriage_certificate]

  IF meets_basic_condition AND has_all(basic_set) THEN
    is_complete = true
  ELSE IF meets_shortcut AND has_all(basic_set) AND has_any(shortcut_set) THEN
    is_complete = true
  ELSE
    is_complete = false
```

### 6.3 电子居住证申领规则

```
Rule: E_PERMIT_ELIGIBILITY

IF permit.status == "issued" THEN
  days_since_approval = now() - permit.approved_at
  IF days_since_approval >= 1 business_day THEN
    can_apply = true
  ELSE
    can_apply = false, wait_hours = 24 - days_since_approval_hours
```

### 6.4 签注时间窗口规则

```
Rule: ENDORSEMENT_WINDOW

IF permit.status == "issued" THEN
  days_until_expiry = permit.expiry_date - today()
  IF 0 < days_until_expiry <= 30 THEN
    can_endorse = true  // 在到期前1个月的时间窗口内
  ELSE IF days_until_expiry <= 0 THEN
    can_endorse = true, is_overdue = true  // 逾期也可以补办，但居住年限重新计算
  ELSE
    can_endorse = false, reason = "尚未到签注时间窗口"
```

---

## 7. 事件日志模拟场景

为满足课程要求的流程挖掘分析，本服务需生成 P1 流程的模拟事件日志。以下是需要覆盖的6种场景变体：

### 场景1：直接审核通过（Happy Path）

```
CASE_P1_001:
  T1: Submit Application          → pending
  T2: Validate Identity           → identity_verified
  T3: Check Documents             → documents_complete
  T4: Review Application          → under_review
  T5: Approve Application         → approved
  T6: Issue Permit                → issued
  T7: Notify Applicant            → notified

处理时间: 10个工作日
```

### 场景2：补件一次后通过

```
CASE_P1_002:
  T1: Submit Application          → pending
  T2: Validate Identity           → identity_verified
  T3: Check Documents             → documents_incomplete
  T4: Request Additional Docs     → additional_documents_required
  T5: Submit Additional Docs      → documents_updated
  T6: Review Application          → under_review
  T7: Approve Application         → approved
  T8: Issue Permit                → issued

处理时间: 18个工作日（含补件等待3天）
```

### 场景3：多次补件

```
CASE_P1_003:
  T1: Submit Application      → pending
  T2: Check Documents         → documents_incomplete
  T3: Request Docs (1st)      → additional_documents_required
  T4: Submit Docs (1st)       → partially_complete
  T5: Request Docs (2nd)      → additional_documents_required
  T6: Submit Docs (2nd)       → documents_complete
  T7: Review Application      → under_review
  T8: Approve                 → approved

处理时间: 25个工作日
```

### 场景4：材料不完整被拒

```
CASE_P1_004:
  T1: Submit Application      → pending
  T2: Check Documents         → documents_incomplete
  T3: Request Additional Docs → additional_documents_required
  T4: (超时未补交)              → timeout
  T5: Reject Application      → rejected

处理时间: 15个工作日（含7天补件等待超时）
```

### 场景5：资格不符被拒

```
CASE_P1_005:
  T1: Submit Application      → pending
  T2: Validate Eligibility    → not_eligible
  T3: Reject Application      → rejected

处理时间: 2个工作日
```

### 场景6：审核超时

```
CASE_P1_006:
  T1-T4: 正常审核流程
  T5: (审核超过15个工作日法定时限)
  T6: (系统自动触发提醒)
  T7: Approve (加速处理)       → approved

处理时间: 20个工作日（超时5天）
```

### 日志格式

遵循全组统一的事件日志格式：

| 字段 | 类型 | 说明 |
|---|---|---|
| case_id | string | 案例ID，如 CASE_P1_001 |
| process_name | string | 固定为 "P1_Residence_Permit" |
| activity | string | 活动名称，对应 BPMN 任务编号 |
| timestamp | ISO 8601 | 事件发生时间 |
| resource | string | 执行角色：citizen / platform / public_security |
| outcome | string | 活动结果：completed / rejected / timeout |
| service_name | string | 固定为 "residence-service" |

---

## 8. 非功能性需求

### 8.1 技术约束

| 约束项 | 要求 |
|---|---|
| 语言 | Python 3.12 |
| 框架 | FastAPI + Pydantic v2 + Uvicorn |
| 数据库 | SQLite（文件：residence.db） |
| 端口 | 8001（通过环境变量 PORT 配置） |
| 通信协议 | HTTP REST + JSON |
| 时间格式 | ISO 8601（UTC，如 2026-08-06T10:30:00Z） |
| 字段命名 | snake_case |
| 状态值 | 小写英文 |

### 8.2 性能要求

| 指标 | 目标 |
|---|---|
| API 响应时间 (P95) | < 200ms |
| 并发支持 | 单进程，满足课程演示需求 |
| 数据库连接 | 每次请求独立连接，自动释放 |

### 8.3 数据安全

- 本项目使用模拟数据，不连接真实政府数据库
- 不存储真实个人敏感信息（身份证号使用模拟ID）
- 文件上传仅记录元数据，不存储实际文件内容

### 8.4 可测试性

- 使用 pytest 进行单元测试和集成测试
- 使用 TestClient (FastAPI) + tmp_path 进行隔离测试
- 至少覆盖6个API测试案例，覆盖所有状态转换路径

---

## 9. 附录：真实官方流程对照

### 9.1 武汉居住证办理官方步骤 → BPMN 映射

| 官方办事步骤 | BPMN 编号 | BPMN 任务 | 系统实现 |
|---|---|---|---|
| 申请人提交居住登记 | P1-T1 | Submit Residence Registration | POST /residence-registrations |
| 公安部门受理居住登记 | P1-T2 | Process Registration | 自动 approved |
| 居住登记满半年 | P1-G1 | Check Registration Duration | eligibility 规则 |
| 申请人提交居住证申请材料 | P1-T3 | Submit Permit Application | POST /residence-permit-applications |
| 窗口受理人员检查材料完整性 | P1-T4 | Check Documents | check-documents 接口 |
| 一次性告知补正材料 | P1-T5 | Request Additional Documents | status → additional_documents_required |
| 申请人补交材料 | P1-T6 | Submit Additional Documents | POST .../documents |
| 社区民警核实材料真实性 | P1-T7 | Verify Information | status → verification |
| 派出所领导审核 | P1-T8 | Review Application | status → under_review |
| 分(县市)局审批制证 | P1-T9 | Approve & Issue | status → approved → issued |
| 通知申领人领取 | P1-T10 | Notify Applicant | 响应数据 |

### 9.2 官方资料来源

1. 《武汉市居住证服务与管理暂行办法》（武汉市人民政府令第322号，2024年7月1日施行）
2. 湖北公安政务服务平台 - 居住证业务办事指南
3. 湖北政务服务网 - 核发居住证（流动人口居住登记 / 首次申领居住证）
4. 武汉市住房保障和房屋管理局 - 相关配套政策

---

> **文档状态**: 待评审  
> **下一步**: 基于本文档进行数据库表设计，然后进入编码实现阶段
