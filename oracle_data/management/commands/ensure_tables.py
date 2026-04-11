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
            for col_sql in [
                "ADD COLUMN IF NOT EXISTS conversation JSONB NOT NULL DEFAULT '[]'::jsonb",
                "ADD COLUMN IF NOT EXISTS is_complete BOOLEAN NOT NULL DEFAULT FALSE",
                "ADD COLUMN IF NOT EXISTS price NUMERIC(10,2)",
                "ADD COLUMN IF NOT EXISTS occasion VARCHAR(100) NOT NULL DEFAULT ''",
                "ADD COLUMN IF NOT EXISTS product_url VARCHAR(500) NOT NULL DEFAULT ''",
                "ADD COLUMN IF NOT EXISTS share_token VARCHAR(64) NOT NULL DEFAULT ''",
                "ADD COLUMN IF NOT EXISTS saved_for_later BOOLEAN NOT NULL DEFAULT FALSE",
                "ADD COLUMN IF NOT EXISTS saved_at TIMESTAMPTZ",
                "ADD COLUMN IF NOT EXISTS outfit_suggestions JSONB NOT NULL DEFAULT '[]'::jsonb",
            ]:
                cursor.execute(f"ALTER TABLE oracle_data_shoppingevaluation {col_sql};")
            self.stdout.write(self.style.SUCCESS("ensure_tables: oracle_data_shoppingevaluation OK"))
