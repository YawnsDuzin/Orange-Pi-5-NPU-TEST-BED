"""
Notification Service Module

Handles event notifications via MQTT and Webhooks.
Provides pluggable notification backends with async support.
"""

import asyncio
import json
import logging
from typing import Optional

from app.config import NotificationSettings
from app.models.system import EventRecord

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Notification Service - delivers event notifications.

    Supports:
    - MQTT publish (for IoT integration)
    - Webhook POST (for external system integration)
    - Async, non-blocking delivery
    - Graceful degradation when backends unavailable
    """

    def __init__(self, settings: NotificationSettings):
        self._settings = settings
        self._mqtt_client = None
        self._http_client = None

    async def handle_event(self, event: EventRecord) -> None:
        """Handle an event from the event handler (listener callback)."""
        tasks = []
        if self._settings.mqtt_enabled:
            tasks.append(self._publish_mqtt(event))
        if self._settings.webhook_enabled and self._settings.webhook_url:
            tasks.append(self._send_webhook(event))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Notification delivery failed: {result}")

    async def _publish_mqtt(self, event: EventRecord) -> None:
        """Publish event to MQTT broker."""
        try:
            if self._mqtt_client is None:
                await self._connect_mqtt()

            if self._mqtt_client is None:
                return

            topic = f"{self._settings.mqtt_topic_prefix}/{event.event_type}/{event.camera_id}"
            payload = json.dumps(event.model_dump(mode="json"), default=str)

            self._mqtt_client.publish(topic, payload)
            logger.debug(f"MQTT published: {topic}")

        except Exception as e:
            logger.error(f"MQTT publish error: {e}")

    async def _send_webhook(self, event: EventRecord) -> None:
        """Send event via webhook POST."""
        try:
            if self._http_client is None:
                await self._init_http_client()

            if self._http_client is None:
                return

            payload = event.model_dump(mode="json")

            response = await self._http_client.post(
                self._settings.webhook_url,
                json=payload,
                timeout=self._settings.webhook_timeout,
            )

            if response.status_code >= 400:
                logger.warning(f"Webhook returned status {response.status_code}")
            else:
                logger.debug(f"Webhook sent: {event.event_type}")

        except Exception as e:
            logger.error(f"Webhook error: {e}")

    async def _connect_mqtt(self) -> None:
        """Connect to MQTT broker."""
        try:
            import paho.mqtt.client as mqtt

            client = mqtt.Client(
                client_id=f"npu-platform-{id(self)}",
                protocol=mqtt.MQTTv5,
            )
            client.connect(
                self._settings.mqtt_broker,
                self._settings.mqtt_port,
            )
            client.loop_start()
            self._mqtt_client = client
            logger.info(
                f"MQTT connected: {self._settings.mqtt_broker}:{self._settings.mqtt_port}"
            )
        except ImportError:
            logger.warning("paho-mqtt not installed - MQTT disabled")
        except Exception as e:
            logger.error(f"MQTT connection error: {e}")

    async def _init_http_client(self) -> None:
        """Initialize async HTTP client."""
        try:
            import httpx

            self._http_client = httpx.AsyncClient(
                timeout=self._settings.webhook_timeout,
            )
        except ImportError:
            logger.warning("httpx not installed - webhook disabled")
        except Exception as e:
            logger.error(f"HTTP client init error: {e}")

    async def close(self) -> None:
        """Close notification connections."""
        if self._mqtt_client:
            try:
                self._mqtt_client.loop_stop()
                self._mqtt_client.disconnect()
            except Exception:
                pass
            self._mqtt_client = None

        if self._http_client:
            try:
                await self._http_client.aclose()
            except Exception:
                pass
            self._http_client = None

        logger.info("Notification service closed")
