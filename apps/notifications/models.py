from django.db import models
from django.conf import settings
import uuid

class Notification(models.Model):
   TYPE = (
      ('info', 'Info'),
      ('success', 'Success'),
      ('warning', 'Warning'),
      ('error', 'Error')
   )

   id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
   user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
   title = models.CharField(max_length=200)
   message = models.TextField()
   type = models.CharField(max_length=10, choices=TYPE, default='info')
   is_read = models.BooleanField(default=False)
   created_at = models.DateTimeField(auto_now_add=True)

   def __str__(self):
      return f'{self.title} - {self.user.email}'
   
   class Meta:
      db_table = 'notifications'
      ordering = ['-created_at']
