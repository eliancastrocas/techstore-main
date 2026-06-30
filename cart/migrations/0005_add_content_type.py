# Generated manually to fix missing GenericForeignKey fields

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("cart", "0004_alter_cart_id_alter_cartitem_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="cartitem",
            name="content_type",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="contenttypes.contenttype",
            ),
        ),
        migrations.AddField(
            model_name="cartitem",
            name="object_id",
            field=models.PositiveIntegerField(null=True),
        ),
    ]
