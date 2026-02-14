release: python manage.py migrate
web: gunicorn lowbono.wsgi:application --bind 0.0.0.0:$PORT
celery_worker: celery -A lowbono worker --concurrency=5 --beat -S django_celery_beat.schedulers:DatabaseScheduler -l info -Q celery
celery_llm_worker: celery -A lowbono worker --concurrency=1 -l info -Q llm_queue
