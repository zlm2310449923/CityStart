# Employment Service

独立管理就业登记和就业扶持申请，默认端口 `8002`，数据库由 `DATABASE_PATH` 指定。

```powershell
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8002
pytest
```

