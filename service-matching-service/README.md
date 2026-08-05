# Service Matching Service

无状态、规则驱动的服务推荐模块，默认端口 `8004`，不使用数据库。

```powershell
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8004
pytest
```

