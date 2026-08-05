# API Gateway

Portal 的唯一后端入口。负责路由转发、服务聚合、超时和下游不可用处理，默认端口 `8000`。

```powershell
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
pytest
```

