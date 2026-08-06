# Residence Service 数据库设计文档

> **版本**: v1.0  
> **日期**: 2026-08-06  
> **数据库**: SQLite (`residence.db`)  
> **服务**: Residence Service (Port 8001)  
> **兼容**: 与现有 app/db.py 结构向后兼容

---

## 目录

1. [设计原则](#1-设计原则)
2. [ER 图（实体关系）](#2-er-图实体关系)
3. [表结构定义](#3-表结构定义)
4. [索引设计](#4-索引设计)
5. [数据字典](#5-数据字典)
6. [状态枚举值](#6-状态枚举值)
7. [迁移策略](#7-迁移策略)
8. [初始化SQL](#8-初始化sql)
9. [示例数据](#9-示例数据)

---

## 1. 设计原则

| 原则 | 说明 |
|---|---|
| **每公民单登记** | 一个 citizen_id 只能有一条有效的居住登记记录（UNIQUE 约束） |
| **一人多申请** | 一个公民可以提交多次居住证申请（如挂失补领、过期重办） |
| **申请关联登记** | 每笔居住证申请关联一条居住登记记录 |
| **状态可追溯** | 通过 status_history 表记录完整的状态变更轨迹 |
| **软删除** | 注销/取消的记录标记 is_deleted 而非物理删除 |
| **文件模拟** | 材料表仅存储元数据，不存储实际文件内容 |
| **时间标准化** | 所有时间字段使用 ISO 8601 字符串（SQLite 无 DATETIME 类型） |
| **兼容现有结构** | 保留现有 `residence_registrations`、`permit_applications`、`application_documents` 三张表，在此基础上扩展 |

---

## 2. ER 图（实体关系）

```
┌──────────────────────────────┐
│   residence_registrations    │
│──────────────────────────────│
│ PK  registration_id   TEXT   │
│ UQ  citizen_id        TEXT   │◄──────────┐
│     residential_addr  TEXT   │           │ 1:1
│     residence_start   TEXT   │           │
│     contact_phone     TEXT   │           │
│     status            TEXT   │           │
│     is_deleted        INT    │           │
│     created_at        TEXT   │           │
│     updated_at        TEXT   │           │
└──────────┬───────────────────┘           │
           │                               │
           │ 1:N (一个登记可关联多个申请)     │
           │                               │
           ▼                               │
┌──────────────────────────────┐           │
│     permit_applications      │           │
│──────────────────────────────│           │
│ PK  application_id    TEXT   │           │
│ FK  registration_id   TEXT   │           │
│     citizen_id        TEXT   │───────────┘
│     status            TEXT   │
│     eligibility_reason TEXT  │
│     reviewer_id       TEXT   │
│     reviewer_comment  TEXT   │
│     is_express        INT    │
│     submitted_at      TEXT   │
│     updated_at        TEXT   │
└──┬─────────────┬─────────────┘
   │             │
   │ 1:N         │ 1:N
   │             │
   ▼             ▼
┌──────────────────────┐  ┌──────────────────────────┐
│ application_documents│  │    status_history         │
│──────────────────────│  │──────────────────────────│
│ PK document_id  TEXT │  │ PK id              INTEGER│
│ FK application_id    │  │ FK application_id  TEXT   │
│    document_type     │  │    from_status     TEXT   │
│    file_name    TEXT │  │    to_status       TEXT   │
│    verify_status TEXT│  │    changed_by      TEXT   │
│    uploaded_at  TEXT │  │    comment         TEXT   │
└──────────────────────┘  │    changed_at      TEXT   │
                          └──────────────────────────┘

┌──────────────────────────────┐
│      residence_permits       │
│──────────────────────────────│
│ PK  permit_id         TEXT   │
│ FK  application_id    TEXT   │────── 关联到批准的申请
│     citizen_id        TEXT   │
│     permit_type       TEXT   │  ← 'physical' / 'electronic'
│     status            TEXT   │  ← 'issued' / 'expired' / 'lost' / 'revoked'
│     issued_at         TEXT   │
│     expiry_date       TEXT   │
│     is_e_permit_active INT   │
│     created_at        TEXT   │
│     updated_at        TEXT   │
└──────────┬───────────────────┘
           │
           │ 1:N
           ▼
┌──────────────────────────────┐
│    permit_endorsements       │
│──────────────────────────────│
│ PK  endorsement_id    TEXT   │
│ FK  permit_id         TEXT   │
│     endorsement_date  TEXT   │
│     previous_expiry   TEXT   │
│     new_expiry        TEXT   │
│     is_overdue        INT    │
│     created_at        TEXT   │
└──────────────────────────────┘
```

---

## 3. 表结构定义

### 3.1 residence_registrations（居住登记表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `registration_id` | TEXT | PK, NOT NULL | 居住登记唯一ID (UUID) |
| `citizen_id` | TEXT | UNIQUE, NOT NULL | 公民ID，全局唯一 |
| `residential_address` | TEXT | NOT NULL | 居住地址 |
| `residence_start_date` | TEXT | NOT NULL | 居住起始日期 (ISO 8601 date) |
| `contact_phone` | TEXT | NULL | 联系电话（可选） |
| `status` | TEXT | NOT NULL, DEFAULT 'approved' | 登记状态 |
| `cancel_reason` | TEXT | NULL | 注销原因（注销时填写） |
| `is_deleted` | INTEGER | NOT NULL, DEFAULT 0 | 软删除标记 (0=有效, 1=已删除) |
| `created_at` | TEXT | NOT NULL | 创建时间 (ISO 8601) |
| `updated_at` | TEXT | NOT NULL | 最后更新时间 (ISO 8601) |

**状态取值**: `approved`（有效）, `cancelled`（已注销）

---

### 3.2 permit_applications（居住证申请表）

与现有表结构兼容，新增字段扩展。

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `application_id` | TEXT | PK, NOT NULL | 申请唯一ID (UUID) |
| `citizen_id` | TEXT | NOT NULL, INDEXED | 公民ID |
| `registration_id` | TEXT | FK → residence_registrations, NULL | 关联的居住登记ID |
| `status` | TEXT | NOT NULL, DEFAULT 'pending' | 申请状态 |
| `application_reason` | TEXT | NULL | 申领理由 |
| `eligibility_reason` | TEXT | NULL | 资格判断结果说明 |
| `is_express` | INTEGER | NOT NULL, DEFAULT 0 | 是否加急 (0=普通, 1=加急) |
| `reviewer_id` | TEXT | NULL | 审核人ID |
| `reviewer_comment` | TEXT | NULL | 审核意见 |
| `submitted_at` | TEXT | NOT NULL | 提交时间 (ISO 8601) |
| `updated_at` | TEXT | NOT NULL | 最后更新时间 (ISO 8601) |

**状态取值**: `pending`, `under_review`, `additional_documents_required`, `verification`, `approved`, `rejected`

---

### 3.3 application_documents（申请材料表）

与现有表结构兼容，新增字段扩展。

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `document_id` | TEXT | PK, NOT NULL | 材料唯一ID (UUID) |
| `application_id` | TEXT | FK → permit_applications, NOT NULL, INDEXED | 所属申请ID |
| `document_type` | TEXT | NOT NULL | 材料类型编码 |
| `file_name` | TEXT | NOT NULL | 文件名（模拟） |
| `verification_status` | TEXT | NOT NULL, DEFAULT 'pending' | 核验状态 |
| `verification_comment` | TEXT | NULL | 核验意见 |
| `is_deleted` | INTEGER | NOT NULL, DEFAULT 0 | 软删除标记 |
| `uploaded_at` | TEXT | NOT NULL | 上传时间 (ISO 8601) |

**document_type 编码表**:

| 编码 | 名称 | 是否必需 |
|---|---|---|
| `identity_document` | 居民身份证 | 必需 |
| `residence_proof` | 居住证明（租赁合同/产权证明等） | 必需 |
| `employment_proof` | 就业证明/劳动合同 | 放宽条件 |
| `enrollment_proof` | 在读证明/学生证 | 放宽条件 |
| `social_security_record` | 社保证明 | 放宽条件 |
| `marriage_certificate` | 结婚证 | 放宽条件 |
| `application_form` | 武汉市居住证申领申请表 | 必需 |
| `other` | 其他补充材料 | 可选 |

**verification_status 取值**: `pending`（待核验）, `verified`（核验通过）, `rejected`（核验不通过）

---

### 3.4 status_history（状态变更历史表）【新增】

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | INTEGER | PK, AUTOINCREMENT | 自增主键 |
| `application_id` | TEXT | FK → permit_applications, NOT NULL, INDEXED | 所属申请ID |
| `from_status` | TEXT | NOT NULL | 变更前状态 |
| `to_status` | TEXT | NOT NULL | 变更后状态 |
| `changed_by` | TEXT | NULL | 操作人ID |
| `comment` | TEXT | NULL | 备注说明 |
| `changed_at` | TEXT | NOT NULL | 变更时间 (ISO 8601) |

**用途**:
- 追踪每笔申请的完整审批轨迹
- 用于流程挖掘分析（计算各步骤耗时）
- 支持审核超时检测

---

### 3.5 residence_permits（居住证表）【新增】

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `permit_id` | TEXT | PK, NOT NULL | 居住证唯一ID (UUID) |
| `application_id` | TEXT | FK → permit_applications, NOT NULL, UNIQUE | 关联的批准申请ID |
| `citizen_id` | TEXT | NOT NULL, INDEXED | 公民ID |
| `permit_type` | TEXT | NOT NULL, DEFAULT 'physical' | 证件类型 |
| `status` | TEXT | NOT NULL, DEFAULT 'issued' | 居住证状态 |
| `issued_at` | TEXT | NOT NULL | 发证日期 (ISO 8601) |
| `expiry_date` | TEXT | NOT NULL | 有效期截止日 (ISO 8601) |
| `is_e_permit_active` | INTEGER | NOT NULL, DEFAULT 0 | 电子居住证是否激活 (0=否, 1=是) |
| `e_permit_id` | TEXT | NULL | 电子居住证ID（申领后生成） |
| `e_permit_activated_at` | TEXT | NULL | 电子居住证激活时间 |
| `is_deleted` | INTEGER | NOT NULL, DEFAULT 0 | 软删除标记 |
| `created_at` | TEXT | NOT NULL | 创建时间 (ISO 8601) |
| `updated_at` | TEXT | NOT NULL | 最后更新时间 (ISO 8601) |

**permit_type 取值**: `physical`（实体居住证）, `electronic`（电子居住证）

**status 取值**: `issued`（正常有效）, `expired`（已过期）, `lost`（已挂失）, `revoked`（已注销）

---

### 3.6 permit_endorsements（居住证签注记录表）【新增】

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `endorsement_id` | TEXT | PK, NOT NULL | 签注唯一ID (UUID) |
| `permit_id` | TEXT | FK → residence_permits, NOT NULL, INDEXED | 关联的居住证ID |
| `endorsement_date` | TEXT | NOT NULL | 签注日期 (ISO 8601) |
| `previous_expiry` | TEXT | NOT NULL | 签注前有效期 |
| `new_expiry` | TEXT | NOT NULL | 签注后有效期（延长1年） |
| `is_overdue` | INTEGER | NOT NULL, DEFAULT 0 | 是否逾期补签 (0=正常, 1=逾期) |
| `created_at` | TEXT | NOT NULL | 创建时间 (ISO 8601) |

**用途**:
- 记录每次签注的历史
- 支持居住年限计算
- 逾期签注标记（居住年限重新计算）

---

## 4. 索引设计

```sql
-- residence_registrations
CREATE UNIQUE INDEX IF NOT EXISTS idx_registration_citizen 
    ON residence_registrations(citizen_id) WHERE is_deleted = 0;

-- permit_applications
CREATE INDEX IF NOT EXISTS idx_permit_app_citizen 
    ON permit_applications(citizen_id);
CREATE INDEX IF NOT EXISTS idx_permit_app_status 
    ON permit_applications(status);
CREATE INDEX IF NOT EXISTS idx_permit_app_registration 
    ON permit_applications(registration_id);

-- application_documents
CREATE INDEX IF NOT EXISTS idx_document_application 
    ON application_documents(application_id);
CREATE INDEX IF NOT EXISTS idx_document_type 
    ON application_documents(document_type);

-- status_history
CREATE INDEX IF NOT EXISTS idx_status_history_application 
    ON status_history(application_id);
CREATE INDEX IF NOT EXISTS idx_status_history_time 
    ON status_history(changed_at);

-- residence_permits
CREATE INDEX IF NOT EXISTS idx_permit_citizen 
    ON residence_permits(citizen_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_permit_application 
    ON residence_permits(application_id);

-- permit_endorsements
CREATE INDEX IF NOT EXISTS idx_endorsement_permit 
    ON permit_endorsements(permit_id);
```

**索引策略说明**:
- `citizen_id` 索引：高频查询字段，支持按公民ID快速检索
- `application_id` 索引：关联查询和外键查找
- `status` 索引：状态筛选（如"查询所有审核中的申请"）
- 部分索引 (`WHERE is_deleted = 0`)：只对有效记录建索引，减小索引体积
- `UNIQUE` 约束：保证 `citizen_id` 单登记、`application_id` 单证

---

## 5. 数据字典

### 5.1 核心实体

| 实体 | 表名 | 主键 | 说明 |
|---|---|---|---|
| 居住登记 | `residence_registrations` | `registration_id` | 非本市户籍公民的居住登记信息 |
| 居住证申请 | `permit_applications` | `application_id` | 居住证申领流程的申请记录 |
| 申请材料 | `application_documents` | `document_id` | 申请附带的证明材料元数据 |
| 状态历史 | `status_history` | `id` | 申请状态变更的审计日志 |
| 居住证 | `residence_permits` | `permit_id` | 已签发的居住证（实体/电子） |
| 签注记录 | `permit_endorsements` | `endorsement_id` | 居住证年度签注历史 |

### 5.2 实体生命周期

```
公民到达武汉
  │
  ▼
创建 residence_registrations (status=approved)
  │
  │ (等待满半年或满足放宽条件)
  │
  ▼
创建 permit_applications (status=pending)
  │
  ├─→ under_review → verification → approved
  ├─→ additional_documents_required → under_review → ...
  └─→ rejected
  │
  │ (申请 approved 后)
  ▼
创建 residence_permits (status=issued, expiry_date=issued_at+1年)
  │
  ├─→ (到期前1个月) 创建 permit_endorsements → 延长 expiry_date
  ├─→ (到期未签注) status → expired
  ├─→ (申报挂失) status → lost
  └─→ (补领) 创建新的 permit_applications → 新的 residence_permits
```

---

## 6. 状态枚举值

### 6.1 申请状态 (permit_applications.status)

| 值 | 含义 | 说明 |
|---|---|---|
| `pending` | 待受理 | 申请已提交，等待首次审核 |
| `under_review` | 审核中 | 审核人员正在审查材料 |
| `additional_documents_required` | 需补充材料 | 材料不全，通知申请人补交 |
| `verification` | 信息核验中 | 材料齐全，进入身份/就业/居住等信息核实阶段 |
| `approved` | 已批准 | 审核通过，进入制证环节 |
| `rejected` | 已拒绝 | 审核不通过或资格不符 |

### 6.2 居住证状态 (residence_permits.status)

| 值 | 含义 | 说明 |
|---|---|---|
| `issued` | 正常有效 | 居住证在有效期内 |
| `expired` | 已过期 | 超过有效期且未签注 |
| `lost` | 已挂失 | 实体证丢失，已申报挂失 |
| `revoked` | 已注销 | 持证人不再符合条件，证件被收回 |

### 6.3 材料核验状态 (application_documents.verification_status)

| 值 | 含义 |
|---|---|
| `pending` | 待核验 |
| `verified` | 核验通过 |
| `rejected` | 核验不通过 |

### 6.4 居住登记状态 (residence_registrations.status)

| 值 | 含义 |
|---|---|
| `approved` | 有效登记 |
| `cancelled` | 已注销 |

---

## 7. 迁移策略

### 7.1 兼容性保证

现有数据库包含三张表：
- `residence_registrations`
- `permit_applications`
- `application_documents`

**升级方案**：在 `init_db()` 中通过 `CREATE TABLE IF NOT EXISTS` 新增三张表，同时通过 `ALTER TABLE` 或重建方式为现有表增加新字段。由于 SQLite 对 ALTER TABLE 支持有限，采用以下策略：

1. 新增表：直接 CREATE TABLE IF NOT EXISTS（`status_history`, `residence_permits`, `permit_endorsements`）
2. 现有表新字段：在 init_db 中检查列是否存在，若不存在则 ALTER TABLE ADD COLUMN

### 7.2 init_db 扩展逻辑

```python
def init_db() -> None:
    with connection() as conn:
        # 1. 创建原有三张表（保持兼容）
        conn.executescript(ORIGINAL_TABLES_SQL)
        
        # 2. 为原有表补充新字段（如果不存在）
        _migrate_existing_tables(conn)
        
        # 3. 创建新增表
        conn.executescript(NEW_TABLES_SQL)
        
        # 4. 创建索引
        conn.executescript(INDEX_SQL)
```

### 7.3 字段变更清单

**residence_registrations 新增**:
- `contact_phone` TEXT
- `cancel_reason` TEXT
- `is_deleted` INTEGER DEFAULT 0

**permit_applications 新增**:
- `registration_id` TEXT（关联居住登记）
- `application_reason` TEXT
- `eligibility_reason` TEXT
- `is_express` INTEGER DEFAULT 0
- `reviewer_id` TEXT
- `reviewer_comment` TEXT

**application_documents 新增**:
- `verification_comment` TEXT
- `is_deleted` INTEGER DEFAULT 0

---

## 8. 初始化SQL

### 8.1 建表语句（完整版）

```sql
-- ============================================================
-- Residence Service 数据库初始化 DDL
-- 兼容原有三表结构 + 新增三表 + 字段扩展
-- ============================================================

-- 表1: 居住登记（扩展版）
CREATE TABLE IF NOT EXISTS residence_registrations (
    registration_id     TEXT PRIMARY KEY NOT NULL,
    citizen_id          TEXT NOT NULL UNIQUE,
    residential_address TEXT NOT NULL,
    residence_start_date TEXT NOT NULL,
    contact_phone       TEXT,
    status              TEXT NOT NULL DEFAULT 'approved',
    cancel_reason       TEXT,
    is_deleted          INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);

-- 表2: 居住证申请（扩展版）
CREATE TABLE IF NOT EXISTS permit_applications (
    application_id      TEXT PRIMARY KEY NOT NULL,
    citizen_id          TEXT NOT NULL,
    registration_id     TEXT,
    status              TEXT NOT NULL DEFAULT 'pending',
    application_reason  TEXT,
    eligibility_reason  TEXT,
    is_express          INTEGER NOT NULL DEFAULT 0,
    reviewer_id         TEXT,
    reviewer_comment    TEXT,
    submitted_at        TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    FOREIGN KEY (registration_id) 
        REFERENCES residence_registrations(registration_id)
);

-- 表3: 申请材料（扩展版）
CREATE TABLE IF NOT EXISTS application_documents (
    document_id          TEXT PRIMARY KEY NOT NULL,
    application_id       TEXT NOT NULL,
    document_type        TEXT NOT NULL,
    file_name            TEXT NOT NULL,
    verification_status  TEXT NOT NULL DEFAULT 'pending',
    verification_comment TEXT,
    is_deleted           INTEGER NOT NULL DEFAULT 0,
    uploaded_at          TEXT NOT NULL,
    FOREIGN KEY (application_id) 
        REFERENCES permit_applications(application_id)
);

-- 表4: 状态变更历史（新增）
CREATE TABLE IF NOT EXISTS status_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id  TEXT NOT NULL,
    from_status     TEXT NOT NULL,
    to_status       TEXT NOT NULL,
    changed_by      TEXT,
    comment         TEXT,
    changed_at      TEXT NOT NULL,
    FOREIGN KEY (application_id) 
        REFERENCES permit_applications(application_id)
);

-- 表5: 居住证（新增）
CREATE TABLE IF NOT EXISTS residence_permits (
    permit_id            TEXT PRIMARY KEY NOT NULL,
    application_id       TEXT NOT NULL UNIQUE,
    citizen_id           TEXT NOT NULL,
    permit_type          TEXT NOT NULL DEFAULT 'physical',
    status               TEXT NOT NULL DEFAULT 'issued',
    issued_at            TEXT NOT NULL,
    expiry_date          TEXT NOT NULL,
    is_e_permit_active   INTEGER NOT NULL DEFAULT 0,
    e_permit_id          TEXT,
    e_permit_activated_at TEXT,
    is_deleted           INTEGER NOT NULL DEFAULT 0,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL,
    FOREIGN KEY (application_id) 
        REFERENCES permit_applications(application_id)
);

-- 表6: 签注记录（新增）
CREATE TABLE IF NOT EXISTS permit_endorsements (
    endorsement_id   TEXT PRIMARY KEY NOT NULL,
    permit_id        TEXT NOT NULL,
    endorsement_date TEXT NOT NULL,
    previous_expiry  TEXT NOT NULL,
    new_expiry       TEXT NOT NULL,
    is_overdue       INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL,
    FOREIGN KEY (permit_id) 
        REFERENCES residence_permits(permit_id)
);
```

### 8.2 索引创建语句

```sql
-- residence_registrations 索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_registration_citizen_active 
    ON residence_registrations(citizen_id) WHERE is_deleted = 0;

-- permit_applications 索引
CREATE INDEX IF NOT EXISTS idx_permit_app_citizen 
    ON permit_applications(citizen_id);
CREATE INDEX IF NOT EXISTS idx_permit_app_status 
    ON permit_applications(status);
CREATE INDEX IF NOT EXISTS idx_permit_app_registration 
    ON permit_applications(registration_id);

-- application_documents 索引
CREATE INDEX IF NOT EXISTS idx_document_application 
    ON application_documents(application_id);
CREATE INDEX IF NOT EXISTS idx_document_type 
    ON application_documents(document_type);

-- status_history 索引
CREATE INDEX IF NOT EXISTS idx_status_history_app 
    ON status_history(application_id);
CREATE INDEX IF NOT EXISTS idx_status_history_time 
    ON status_history(changed_at);

-- residence_permits 索引
CREATE INDEX IF NOT EXISTS idx_permit_citizen 
    ON residence_permits(citizen_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_permit_application 
    ON residence_permits(application_id);

-- permit_endorsements 索引
CREATE INDEX IF NOT EXISTS idx_endorsement_permit 
    ON permit_endorsements(permit_id);
```

---

## 9. 示例数据

### 9.1 场景：正常居住登记 + 半年后申请居住证 + 签发

```sql
-- 1. 居住登记
INSERT INTO residence_registrations VALUES (
    'REG-2026-00001',
    'C001',
    '武汉市洪山区珞喻路1037号',
    '2026-01-15',
    '13800138000',
    'approved',
    NULL,
    0,
    '2026-01-15T10:00:00Z',
    '2026-01-15T10:00:00Z'
);

-- 2. 居住证申请（2026-08-01，登记已满半年）
INSERT INTO permit_applications VALUES (
    'APP-2026-00001',
    'C001',
    'REG-2026-00001',
    'approved',
    '就业需要',
    '居住登记已满半年，满足申领条件',
    0,
    'REV001',
    '材料齐全，审核通过',
    '2026-08-01T09:00:00Z',
    '2026-08-12T16:30:00Z'
);

-- 3. 申请材料
INSERT INTO application_documents VALUES 
('DOC-001', 'APP-2026-00001', 'identity_document', 'id_card_front.pdf', 'verified', NULL, 0, '2026-08-01T09:05:00Z'),
('DOC-002', 'APP-2026-00001', 'identity_document', 'id_card_back.pdf', 'verified', NULL, 0, '2026-08-01T09:05:00Z'),
('DOC-003', 'APP-2026-00001', 'residence_proof', 'lease_contract.pdf', 'verified', NULL, 0, '2026-08-01T09:06:00Z'),
('DOC-004', 'APP-2026-00001', 'application_form', 'permit_application_form.pdf', 'verified', NULL, 0, '2026-08-01T09:07:00Z');

-- 4. 状态变更历史
INSERT INTO status_history VALUES 
(1, 'APP-2026-00001', 'pending', 'under_review', NULL, '系统自动受理', '2026-08-01T09:10:00Z'),
(2, 'APP-2026-00001', 'under_review', 'verification', 'REV001', '材料齐全，转核实', '2026-08-02T10:00:00Z'),
(3, 'APP-2026-00001', 'verification', 'approved', 'REV001', '信息核验通过', '2026-08-12T16:30:00Z');

-- 5. 签发居住证
INSERT INTO residence_permits VALUES (
    'PMT-2026-00001',
    'APP-2026-00001',
    'C001',
    'physical',
    'issued',
    '2026-08-12T16:30:00Z',
    '2027-08-12T16:30:00Z',  -- 有效期1年
    0,  -- 未激活电子居住证
    NULL,
    NULL,
    0,
    '2026-08-12T16:30:00Z',
    '2026-08-12T16:30:00Z'
);
```

### 9.2 场景：补件流程

```sql
-- 申请缺少材料
INSERT INTO permit_applications VALUES (
    'APP-2026-00002',
    'C002',
    'REG-2026-00002',
    'approved',  -- 最终审批通过
    '工作需要',
    '居住登记已满半年',
    0,
    'REV002',
    '补交材料后审核通过',
    '2026-07-20T09:00:00Z',
    '2026-08-05T16:00:00Z'
);

-- 状态流转：补件 → 审核 → 通过
INSERT INTO status_history VALUES 
(4, 'APP-2026-00002', 'pending', 'under_review', NULL, '受理', '2026-07-20T09:10:00Z'),
(5, 'APP-2026-00002', 'under_review', 'additional_documents_required', 'REV002', '缺少居住证明材料', '2026-07-21T14:00:00Z'),
(6, 'APP-2026-00002', 'additional_documents_required', 'under_review', NULL, '申请人补交材料', '2026-07-25T10:00:00Z'),
(7, 'APP-2026-00002', 'under_review', 'verification', 'REV002', '材料齐全，进入核验', '2026-07-26T09:00:00Z'),
(8, 'APP-2026-00002', 'verification', 'approved', 'REV002', '核验通过', '2026-08-05T16:00:00Z');
```

### 9.3 场景：签注续期

```sql
-- 1年后签注
INSERT INTO permit_endorsements VALUES (
    'END-2027-00001',
    'PMT-2026-00001',
    '2027-07-15T10:00:00Z',       -- 在到期前1个月办理签注
    '2027-08-12T16:30:00Z',       -- 旧有效期
    '2028-08-12T16:30:00Z',       -- 新有效期（延长1年）
    0,                            -- 正常签注，非逾期
    '2027-07-15T10:00:00Z'
);

-- 更新居住证有效期
UPDATE residence_permits 
SET expiry_date = '2028-08-12T16:30:00Z', updated_at = '2027-07-15T10:00:00Z'
WHERE permit_id = 'PMT-2026-00001';
```

---

## 附：与现有 app/db.py 的集成指南

### 向后兼容性

现有 `init_db()` 函数创建的三个表保持不变，新增表和字段通过 `CREATE TABLE IF NOT EXISTS` 和 `ALTER TABLE ADD COLUMN`（带异常处理）安全添加。

### 建议的代码组织结构

```
residence-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 路由与请求处理
│   ├── models.py            # Pydantic 请求/响应模型
│   ├── db.py                # 数据库连接与初始化（扩展）
│   ├── schemas.py           # [新增] 数据库表对应的 dataclass/typeddict
│   ├── services.py           # [新增] 业务逻辑层
│   ├── rules.py              # [新增] 资格判断等业务规则
│   └── constants.py          # [新增] 枚举常量定义
├── tests/
│   ├── test_health.py
│   ├── test_residence.py     # 扩展测试用例
│   └── conftest.py           # [新增] 测试 fixtures
├── commend/
│   ├── requirements-design.md
│   └── database-design.md    # 本文件
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

---

> **文档状态**: 待评审  
> **下一步**: 与需求设计文档一同评审后，进入编码实现阶段
