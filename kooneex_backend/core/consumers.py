from channels.generic.websocket import AsyncWebsocketConsumer
from channels.generic.websocket import AsyncJsonWebsocketConsumer
import json

class MototaxiConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.group_name = "mototaxistas"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def nuevo_viaje(self, event):
        await self.send_json(event["data"])

class ViajeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.viaje_id = self.scope['url_route']['kwargs']['viaje_id']
        self.room_group_name = f'viaje_{self.viaje_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def enviar_actualizacion(self, event):
        await self.send(text_data=json.dumps(event["data"]))
    
    async def estado_viaje(self, event):
        await self.send(text_data=json.dumps({
            "type": "estado_viaje",
            "estado": event["estado"],
            "viaje_id": event["viaje_id"],
            "mototaxista": event.get("mototaxista"),
            "costo_final": event.get("costo_final"),
        }))