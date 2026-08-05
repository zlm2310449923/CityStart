# Housing Service

独立管理住房补贴申请与资格核验，默认端口 `8003`，数据库由 `DATABASE_PATH` 指定。

```powershell
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8003
pytest
```

