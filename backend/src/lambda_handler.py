from mangum import Mangum
from backend.src.app import app

# AWS Lambda entrypoint for API Gateway / Function URL
handler = Mangum(app)
