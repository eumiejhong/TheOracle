from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Create missing tables that migrations may have skipped"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS oracle_data_shoppingevaluation (
                    id BIGSERIAL PRIMARY KEY,
                    item_image BYTEA,
                    item_description JSONB NOT NULL DEFAULT '{}'::jsonb,
                    evaluation TEXT NOT NULL,
                    verdict VARCHAR(20) NOT NULL DEFAULT 'consider',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE
                );
            """)
            self.stdout.write(self.style.SUCCESS("ensure_tables: oracle_data_shoppingevaluation OK"))
