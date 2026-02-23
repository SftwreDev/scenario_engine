# Make config.settings a package so we can import config.settings.base and config.settings.local
import os

env = os.getenv("ENVIRONMENT", "local")
from dotenv import load_dotenv

load_dotenv()
if env == "production":
    pass
else:
    from .local import *
