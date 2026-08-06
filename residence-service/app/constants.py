APPLICATION_STATUSES = {
    "pending",
    "under_review",
    "additional_documents_required",
    "verification",
    "approved",
    "rejected",
}

ALLOWED_STATUS_TRANSITIONS = {
    "pending": {"under_review", "rejected"},
    "under_review": {"additional_documents_required", "verification"},
    "additional_documents_required": {"under_review", "rejected"},
    "verification": {"approved", "rejected"},
    "approved": set(),
    "rejected": set(),
}

UPLOADABLE_APPLICATION_STATUSES = {"pending", "additional_documents_required"}

DOCUMENT_TYPES = {
    "identity_document": "身份证",
    "residence_proof": "居住证明",
    "employment_proof": "就业证明",
    "enrollment_proof": "在读证明",
    "social_security_record": "社保证明",
    "marriage_certificate": "结婚证",
    "spouse_id_document": "配偶身份证明",
    "application_form": "居住证申领申请表",
    "other": "其他材料",
}

REQUIRED_DOCUMENT_TYPES = {"identity_document", "residence_proof"}
SHORTCUT_DOCUMENT_TYPES = {
    "social_security_record",
    "enrollment_proof",
    "employment_proof",
    "marriage_certificate",
}

