import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0002_seed_roles')]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(
                max_length=20,
                validators=[django.core.validators.RegexValidator(
                    regex=r'^(\+64[\s-]?|0)[2-9][\s-]?(\d[\s-]?){6,9}\d$',
                    message='Enter a New Zealand phone number, for example 021 123 4567.',
                )],
            ),
        ),
    ]
