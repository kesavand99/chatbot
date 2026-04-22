import os
import json
import asyncio
from app.utils.logger import get_logger
from typing import Optional
from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv
from datetime import datetime
from uuid import UUID
from app.services.kafka_topics import KAFKA_TOPIC_PREFIX

load_dotenv()
logger = get_logger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
KAFKA_TOPIC_PREFIX = os.getenv("KAFKA_TOPIC_PREFIX", "")

producer: Optional[AIOKafkaProducer] = None


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, UUID)):
            return str(obj)
        return super().default(obj)


async def start_kafka() -> None:
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v, cls=EnhancedJSONEncoder).encode("utf-8"),
    )

    while True:
        try:
            await producer.start()
            logger.info("✅ Kafka producer started")
            return
        except Exception as e:
            logger.warning(f"⏳ Kafka producer not ready, retrying in 3s: {e}")
            await asyncio.sleep(3)


async def stop_kafka() -> None:
    if producer:
        await producer.stop()
        logger.info("✅ Kafka producer stopped")
    else:
        logger.info("⚠️ Kafka producer was not initialized")


async def send_event(topic: str, value: dict) -> None:
    if producer is None:
        logger.warning("⚠️ Kafka producer is not initialized")
        return

    # Avoid double prefix like "dev.dev.user.registered"
    if KAFKA_TOPIC_PREFIX:
        full_topic = topic if topic.startswith(KAFKA_TOPIC_PREFIX) else f"{KAFKA_TOPIC_PREFIX}{topic}"
    else:
        full_topic = topic

    try:
        await producer.send_and_wait(full_topic, value=value)
        logger.info(f"✅ Event sent to topic '{full_topic}':\n{json.dumps(value, indent=2, cls=EnhancedJSONEncoder)}")
    except Exception as e:
        logger.error(f"❌ Failed to send event to topic '{full_topic}': {e}")