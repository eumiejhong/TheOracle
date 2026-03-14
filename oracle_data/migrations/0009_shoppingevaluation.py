from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('oracle_data', '0008_remove_wardrobeitem_visual_descriptors_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShoppingEvaluation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_image', models.BinaryField(blank=True, null=True)),
                ('item_description', models.JSONField(default=dict)),
                ('evaluation', models.TextField()),
                ('verdict', models.CharField(choices=[('strong_buy', 'Strong Buy'), ('consider', 'Worth Considering'), ('skip', 'Skip It'), ('redundant', 'You Already Own This')], default='consider', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
