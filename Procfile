web: daphne messenger.asgi:application --port $PORT --bind 0.0.0.0
worker: celery -A messenger worker -l info
beat: celery -A messenger beat -l info
