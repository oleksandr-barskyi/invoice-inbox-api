
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='invoices/%Y/%m/')),
                ('original_name', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('parsed', 'Parsed'), ('needs_review', 'Needs Review'), ('failed', 'Failed')], db_index=True, default='pending', max_length=20)),
                ('number', models.CharField(blank=True, max_length=64)),
                ('issue_date', models.DateField(blank=True, null=True)),
                ('currency', models.CharField(blank=True, max_length=3)),
                ('total', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('issues', models.JSONField(blank=True, default=list)),
                ('error', models.TextField(blank=True)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('parsed_at', models.DateTimeField(blank=True, null=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='LineItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=255)),
                ('quantity', models.DecimalField(decimal_places=2, max_digits=10)),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='invoices.invoice')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='Vendor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vendors', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='invoice',
            name='vendor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoices', to='invoices.vendor'),
        ),
        migrations.AddConstraint(
            model_name='vendor',
            constraint=models.UniqueConstraint(fields=('owner', 'name'), name='unique_vendor_per_owner'),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['owner', 'status'], name='invoices_in_owner_i_ca14ea_idx'),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['owner', 'issue_date'], name='invoices_in_owner_i_67e9ba_idx'),
        ),
    ]
