# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0006_alter_order_id_alter_orderitem_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="service",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="products.service",
            ),
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="service",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="products.service",
            ),
        ),
    ]
