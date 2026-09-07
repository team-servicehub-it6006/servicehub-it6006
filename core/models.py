from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    A record of privileged actions: role changes, service deactivations, cleaner assignments.

    Deliberately narrow. It stores what was done and by whom, not the contents of the record.
    A log that copies every customer's address is a second copy of the thing we are trying to
    protect, and it would be kept for longer than the record itself.
    """

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                              null=True, related_name='audit_entries')
    action = models.CharField(max_length=60)
    object_type = models.CharField(max_length=40)
    object_ref = models.CharField(max_length=60)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'audit log entry'
        verbose_name_plural = 'audit log'

    def __str__(self):
        who = self.actor.email if self.actor else 'system'
        return f'{who} {self.action} {self.object_type} {self.object_ref}'

    @classmethod
    def record(cls, actor, action, obj_type, obj_ref):
        return cls.objects.create(
            actor=actor if getattr(actor, 'is_authenticated', False) else None,
            action=action, object_type=obj_type, object_ref=str(obj_ref)[:60])
