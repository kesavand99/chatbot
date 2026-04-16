from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

client: AsyncIOMotorClient | None = None
database: AsyncIOMotorDatabase | None = None


async def connect_to_mongo():
    global client, database
    if client is None:
        client = AsyncIOMotorClient(settings.mongodb_uri)
        database = client[settings.mongodb_db]
        # Create indexes for better performance
        await database["chats"].create_index("session_id", unique=True)
        await database["chats"].create_index([("updated_at", -1)])


async def close_mongo_connection():
    global client, database
    if client is not None:
        client.close()
    client = None
    database = None


def get_database() -> AsyncIOMotorDatabase:
    if database is None:
        raise RuntimeError("MongoDB connection has not been initialized.")
    return database
