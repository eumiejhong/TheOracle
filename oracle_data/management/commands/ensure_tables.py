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
                    evaluation TEXT NOT NULL DEFAULT '',
                    conversation JSONB NOT NULL DEFAULT '[]'::jsonb,
                    verdict VARCHAR(20) NOT NULL DEFAULT 'consider',
                    is_complete BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE
                );
            """)
            cursor.execute("""
                ALTER TABLE oracle_data_shoppingevaluation
                ADD COLUMN IF NOT EXISTS conversation JSONB NOT NULL DEFAULT '[]'::jsonb;
            """)
            cursor.execute("""
                ALTER TABLE oracle_data_shoppingevaluation
                ADD COLUMN IF NOT EXISTS is_complete BOOLEAN NOT NULL DEFAULT FALSE;
            """)
            self.stdout.write(self.style.SUCCESS("ensure_tables: oracle_data_shoppingevaluation OK"))
