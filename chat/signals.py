# In your Django app's signals.py
from django.contrib.sessions.models import Session
from django.db.models.signals import post_delete
from django.dispatch import receiver
import redisUtils

@receiver(post_delete, sender=Session)
def delete_temp_user_key_on_session_delete(sender, instance, **kwargs):
    user_id = instance.get_decoded().get('temp_user_id')
    if user_id:
        RedisUtils.delete_temp_user_key(user_id)
