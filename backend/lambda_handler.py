from mangum import Mangum
from backend.api import app


handler = Mangum(app, lifespan="off")
