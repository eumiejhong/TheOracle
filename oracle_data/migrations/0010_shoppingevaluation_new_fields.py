from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oracle_data', '0009_shoppingevaluation'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE oracle_data_shoppingevaluation ADD COLUMN IF NOT EXISTS conversation JSONB NOT NULL DEFAULT '[]'::jsonb;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="ALTER TABLE oracle_data_shoppingevaluation ADD COLUMN IF NOT EXISTS is_complete BOOLEAN NOT NULL DEFAULT FALSE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="ALTER TABLE oracle_data_shoppingevaluation ADD COLUMN IF NOT EXISTS price NUMERIC(10,2);",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="ALTER TABLE oracle_data_shoppingevaluation ADD COLUMN IF NOT EXISTS occasion VARCHAR(100) NOT NULL DEFAULT '';",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="ALTER TABLE oracle_data_shoppingevaluation ADD COLUMN IF NOT EXISTS product_url VARCHAR(500) NOT NULL DEFAULT '';",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="ALTER TABLE oracle_data_shoppingevaluation ADD COLUMN IF NOT EXISTS share_token VARCHAR(64) NOT NULL DEFAULT '';",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="ALTER TABLE oracle_data_shoppingevaluation ADD COLUMN IF NOT EXISTS saved_for_later BOOLEAN NOT NULL DEFAULT FALSE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="ALTER TABLE oracle_data_shoppingevaluation ADD COLUMN IF NOT EXISTS saved_at TIMESTAMPTZ;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="ALTER TABLE oracle_data_shoppingevaluation ADD COLUMN IF NOT EXISTS outfit_suggestions JSONB NOT NULL DEFAULT '[]'::jsonb;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
