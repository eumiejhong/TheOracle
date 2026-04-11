from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oracle_data', '0009_shoppingevaluation'),
    ]

    operations = [
        migrations.AddField(
            model_name='shoppingevaluation',
            name='conversation',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='shoppingevaluation',
            name='is_complete',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='shoppingevaluation',
            name='price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='shoppingevaluation',
            name='occasion',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='shoppingevaluation',
            name='product_url',
            field=models.URLField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='shoppingevaluation',
            name='share_token',
            field=models.CharField(blank=True, db_index=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='shoppingevaluation',
            name='saved_for_later',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='shoppingevaluation',
            name='saved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='shoppingevaluation',
            name='outfit_suggestions',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
