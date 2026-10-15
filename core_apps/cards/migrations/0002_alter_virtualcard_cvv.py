from django.db import migrations, models


class Migration(migrations.Migration):
    """A CVV is 3 digits: ``unique=True`` made card creation fail with an IntegrityError after ~35 cards."""

    dependencies = [
        ("cards", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="virtualcard",
            name="cvv",
            field=models.CharField(max_length=16),
        ),
    ]
