import os

from .base import *

# requires DOKKU_ENV = 'production' as an environment variable for production
if 'DOKKU_ENV' in os.environ:
    if os.environ['DOKKU_ENV'] == 'production':
        from .prod import *
    elif os.environ['DOKKU_ENV'] == 'staging':
        from .staging import *
    else:
        from .dev import *
else:
    from .dev import *
