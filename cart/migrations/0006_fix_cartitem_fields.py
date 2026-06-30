# Fix cartitem fields to be non-nullable

from django.db import migrations, models
import django.db.models.deletion


def set_default_content_type(apps, schema_editor):
    CartItem = apps.get_model("cart", "CartItem")
    Product = apps.get_model("products", "Product")
    content_type = schema_editor.connection.cursor()

    from django.contrib.contenttypes.models import ContentType

    product_ct = ContentType.objects.get_for_model(Product)

    CartItem.objects.filter(content_type__isnull=True).update(content_type=product_ct)


class Migration(migrations.Migration):
    dependencies = [
        ("cart", "0005_add_content_type"),
    ]

    operations = [
        migrations.RunPython(set_default_content_type),
        migrations.AlterField(
            model_name="cartitem",
            name="content_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="contenttypes.contenttype",
            ),
        ),
        migrations.AlterField(
            model_name="cartitem", name="object_id", field=models.PositiveIntegerField()
        ),
    ]
