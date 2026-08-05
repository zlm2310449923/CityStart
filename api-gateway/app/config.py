import os


RESIDENCE_SERVICE_URL = os.getenv("RESIDENCE_SERVICE_URL", "http://localhost:8001")
EMPLOYMENT_SERVICE_URL = os.getenv("EMPLOYMENT_SERVICE_URL", "http://localhost:8002")
HOUSING_SERVICE_URL = os.getenv("HOUSING_SERVICE_URL", "http://localhost:8003")
MATCHING_SERVICE_URL = os.getenv("MATCHING_SERVICE_URL", "http://localhost:8004")
DOWNSTREAM_TIMEOUT_SECONDS = float(os.getenv("DOWNSTREAM_TIMEOUT_SECONDS", "5"))

