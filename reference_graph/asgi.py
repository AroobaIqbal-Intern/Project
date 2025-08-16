"""
ASGI config for reference_graph project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reference_graph.settings')

application = get_asgi_application()
