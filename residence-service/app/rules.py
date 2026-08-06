from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from .constants import DOCUMENT_TYPES, REQUIRED_DOCUMENT_TYPES, SHORTCUT_DOCUMENT_TYPES


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_datetime(value: datetime | None = None) -> str:
    current = value or utc_now()
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def registration_days(residence_start_date: str, today: date | None = None) -> int:
    start = date.fromisoformat(residence_start_date)
    return max(0, ((today or utc_now().date()) - start).days)


def check_eligibility(
    days: int,
    *,
    has_social_security_6m: bool = False,
    is_enrolled_6m: bool = False,
    is_employed_6m: bool = False,
    is_married_to_local_6m: bool = False,
) -> dict:
    descriptions = {
        "social_security": "连续缴纳社保满6个月",
        "enrollment": "连续就读满6个月",
        "employment": "连续就业满6个月",
        "marriage": "与本地户籍人员结婚满半年",
    }
    flags = {
        "social_security": has_social_security_6m,
        "enrollment": is_enrolled_6m,
        "employment": is_employed_6m,
        "marriage": is_married_to_local_6m,
    }
    shortcut_conditions = [
        {"condition": key, "description": descriptions[key], "met": True}
        for key, met in flags.items()
        if met
    ]
    meets_basic = days >= 183
    meets_shortcut = bool(shortcut_conditions)
    if meets_basic:
        reason = "居住登记已满半年"
    elif meets_shortcut:
        reason = f"{shortcut_conditions[0]['description']}，适用放宽条件"
    else:
        reason = "居住登记未满半年且不满足放宽条件"
    return {
        "is_eligible": meets_basic or meets_shortcut,
        "reason": reason,
        "registration_days": days,
        "meets_basic_condition": meets_basic,
        "meets_shortcut": meets_shortcut,
        "meets_shortcut_conditions": shortcut_conditions,
        "missing_requirements": [] if meets_basic or meets_shortcut else ["registration_183_days_or_shortcut_condition"],
    }


def check_document_completeness(document_types: Iterable[str], meets_basic: bool) -> dict:
    uploaded = set(document_types)
    missing = sorted(REQUIRED_DOCUMENT_TYPES - uploaded)
    shortcut_uploaded = sorted(SHORTCUT_DOCUMENT_TYPES & uploaded)
    if not meets_basic and not shortcut_uploaded:
        missing.append("shortcut_supporting_document")
    required = [
        {"type": doc_type, "name": DOCUMENT_TYPES[doc_type], "uploaded": doc_type in uploaded}
        for doc_type in sorted(REQUIRED_DOCUMENT_TYPES)
    ]
    optional = [
        {"type": doc_type, "name": DOCUMENT_TYPES[doc_type], "uploaded": doc_type in uploaded}
        for doc_type in sorted(SHORTCUT_DOCUMENT_TYPES | {"application_form", "other"})
    ]
    suggestions = {
        "identity_document": "请上传身份证明材料",
        "residence_proof": "请上传居住证明材料（租赁合同/产权证明/住宿证明）",
        "shortcut_supporting_document": "请上传社保、就学、就业或婚姻放宽条件证明中的至少一项",
    }
    return {
        "is_complete": not missing,
        "required_documents": required,
        "optional_documents": optional,
        "missing_documents": missing,
        "suggestion": "；".join(suggestions[item] for item in missing) if missing else "材料完整",
    }


def add_one_year(value: datetime) -> datetime:
    year = value.year + 1
    day = min(value.day, monthrange(year, value.month)[1])
    return value.replace(year=year, day=day)


def next_business_day(value: datetime) -> datetime:
    candidate = value + timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate

