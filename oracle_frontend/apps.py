from django.apps import AppConfig
import os

class OracleFrontendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'oracle_frontend'
    path = os.path.dirname(__file__)  # explicitly set path to avoid multi-path error
