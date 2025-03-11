from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Provider',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('website', models.URLField(blank=True, null=True)),
                ('logo_url', models.URLField(blank=True, null=True)),
                ('api_base_url', models.URLField(blank=True, null=True)),
                ('active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='QuoteQueryLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_country', models.CharField(max_length=3)),
                ('destination_country', models.CharField(max_length=3)),
                ('source_currency', models.CharField(max_length=3)),
                ('destination_currency', models.CharField(max_length=3)),
                ('send_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('user_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddIndex(
            model_name='quoteQueryLog',
            index=models.Index(fields=['source_country', 'destination_country'], name='quotes_quot_source__c9da84_idx'),
        ),
        migrations.AddIndex(
            model_name='quoteQueryLog',
            index=models.Index(fields=['timestamp'], name='quotes_quot_timesta_0b9e63_idx'),
        ),
        migrations.CreateModel(
            name='FeeQuote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_country', models.CharField(max_length=3)),
                ('destination_country', models.CharField(max_length=3)),
                ('source_currency', models.CharField(max_length=3)),
                ('destination_currency', models.CharField(max_length=3)),
                ('payment_method', models.CharField(max_length=50)),
                ('delivery_method', models.CharField(max_length=50)),
                ('send_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('fee_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('exchange_rate', models.DecimalField(decimal_places=6, max_digits=12)),
                ('delivery_time_minutes', models.IntegerField()),
                ('destination_amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('last_updated', models.DateTimeField(default=django.utils.timezone.now)),
                ('provider', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='quotes', to='quotes.provider')),
            ],
        ),
        migrations.AddIndex(
            model_name='FeeQuote',
            index=models.Index(fields=['provider', 'source_country', 'destination_country'], name='quotes_feeq_provide_57fb66_idx'),
        ),
        migrations.AddIndex(
            model_name='FeeQuote',
            index=models.Index(fields=['source_country', 'destination_country'], name='quotes_feeq_source__8b0b3d_idx'),
        ),
        migrations.AddIndex(
            model_name='FeeQuote',
            index=models.Index(fields=['provider', 'payment_method', 'delivery_method'], name='quotes_feeq_provide_fd2c09_idx'),
        ),
        migrations.AddIndex(
            model_name='FeeQuote',
            index=models.Index(fields=['last_updated'], name='quotes_feeq_last_up_86f071_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='feequote',
            unique_together={('provider', 'source_country', 'destination_country', 'source_currency', 'destination_currency', 'payment_method', 'delivery_method', 'send_amount')},
        ),
    ] 