import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name='SupportTicket',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('subject', models.CharField(max_length=200)),
                ('category', models.CharField(choices=[('account', 'Account'), ('deposit', 'Deposit'), ('withdrawal', 'Withdrawal'), ('investment', 'Investment'), ('technical', 'Technical'), ('other', 'Other')], default='other', max_length=20)),
                ('priority', models.CharField(choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High')], default='normal', max_length=20)),
                ('status', models.CharField(choices=[('open', 'Open'), ('answered', 'Answered'), ('closed', 'Closed')], db_index=True, default='open', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='support_tickets', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'support_tickets', 'ordering': ['-updated_at']},
        ),
        migrations.CreateModel(
            name='TicketMessage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('sender', models.CharField(choices=[('user', 'User'), ('admin', 'Admin')], max_length=10)),
                ('message', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='support.supportticket')),
            ],
            options={'db_table': 'support_ticket_messages', 'ordering': ['created_at']},
        ),
    ]
