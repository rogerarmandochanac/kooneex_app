from django.urls import re_path
from .consumers import ViajeConsumer
from .consumers import MototaxiConsumer

websocket_urlpatterns = [
    re_path(r"ws/viaje/(?P<viaje_id>\d+)/$", ViajeConsumer.as_asgi()),
    re_path(r"ws/mototaxi/", MototaxiConsumer.as_asgi()),
    
]