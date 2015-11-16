import pydoc

from common.models import ErrorQueue
from search.search_utils import index_instance

from celery.task.schedules import crontab
from celery.decorators import periodic_task


@periodic_task(
    run_every=(crontab(minute='*/2')),
    name="try_indexing_failed_records",
    ignore_result=True)
def retry_indexing():
    objects_with_errors = ErrorQueue.objects.filter(
        error_type='SEARCH_INDEXING_ERROR')
    for obj in objects_with_errors:
        obj_path = "{}.models.{}".format(obj.app_label, obj.model_name)
        model = pydoc.locate(obj_path)
        instance = model.objects.get(id=obj.object_pk)
        try:
            result = index_instance(
                instance._meta.app_label,
                instance.__class__.__name__,
                instance.id)
            if result:
                obj.delete()
            else:
                obj.retries = obj.retries + 1
                obj.save()
        except instance.DoesNotExist:
            # The related object is already deleted in the database
            pass
