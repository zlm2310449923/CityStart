# Residence Service

独立管理居住登记和居住证申请，默认端口 `8001`，数据库由 `DATABASE_PATH` 指定。

```powershell
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8001
pytest
```

