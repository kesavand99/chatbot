"""Fast-path intent detection for common user commands.

Handles time/date queries, website opening, Wikipedia search,
YouTube playback, and email detection without calling the LLM.
"""

import asyncio
from datetime import datetime as dt

import wikipedia


# Map of site names to URLs for the "open <site>" command.
_SITES = {
    "google": "https://www.google.com",
    "spotify": "https://www.spotify.com",
    "chatgpt": "https://chat.openai.com",
    "github": "https://github.com",
    "youtube": "https://www.youtube.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "twitter": "https://www.twitter.com",
    "linkedin": "https://www.linkedin.com",
    "amazon": "https://www.amazon.com",
    "netflix": "https://www.netflix.com",
}


# FAQ Data Store
_FAQ = {
    "pricing": "Our pricing plans start from $0/month for individuals up to $49/month for enterprises. Check our pricing page for details.",
    "features": "We offer AI-powered chat, real-time streaming, chat history, and intent detection out of the box.",
    "support": "You can reach us at support@example.com or use the 'Connect to Admin' button for immediate help.",
    "refund": "We offer a 30-day money-back guarantee for all our paid plans. No questions asked.",
    "security": "Your data is encrypted at rest and in transit. We take privacy very seriously.",
    "documentation": "Our full developer documentation is available at https://docs.example.com.",
    "integration": "You can integrate our chatbot into your website using our simple 1-line script or our robust API.",
    "hello": "Hello! I am NexusAI, your personal assistant. How can I help you today?",
    "nexusai": "NexusAI is a state-of-the-art conversational AI designed to assist with your daily tasks and queries.",
    "help": "I can help with information about our services, technical support, or even search the web for you. What do you need?",
    "payment": "We accept all major credit cards, PayPal, and wire transfers for enterprise customers.",
    "admin": "I'm sorry, I'm just an AI. If you need to speak with a human, please use the 'Connect to Admin' button.",
}


async def check_intent(message: str) -> str | None:
    """Return an instant reply if *message* matches a known command, else ``None``."""
    msg = message.lower().strip()

    # FAQ Checks - Fast-path for predefined questions
    for key, response in _FAQ.items():
        if key in msg:
            return response

    # Greetings - Fast-path to avoid LLM errors
    if msg in ["hi", "hello", "hey", "hola", "hi there", "hello there", "nexus", "nexusai"]:
        return "Hello! I am NexusAI, your personal assistant. How can I help you today?"

    # Time - more flexible matching
    if any(x in msg for x in ["time", "clock"]) and any(y in msg for y in ["what", "tell", "current", "now"]):
        return f"The current time is {dt.now().strftime('%I:%M %p')}."

    # Date - more flexible matching
    if "date" in msg and any(x in msg for x in ["what", "today", "current"]):
        return f"Today's date is {dt.now().strftime('%d/%m/%Y')}."

    # Open websites
    for site, url in _SITES.items():
        if f"open {site}" in msg:
            return f"Sure! Opening {site.capitalize()}: {url}"

    # Play / YouTube
    if msg.startswith("play "):
        song = msg.replace("play ", "").strip()
        return f"Playing {song} on YouTube: https://www.youtube.com/results?search_query={song.replace(' ', '+')}"

    # Wikipedia Search / Who is / What is
    query = None
    if msg.startswith("search wikipedia for "):
        query = msg.replace("search wikipedia for ", "").strip()
    elif msg.startswith("search "):
        query = msg.replace("search ", "").strip()
    elif msg.startswith("who is "):
        query = msg.replace("who is ", "").strip()
    elif msg.startswith("what is "):
        query = msg.replace("what is ", "").strip()

    if query:
        try:
            # Try to get summary directly first (usually works well with auto_suggest=True)
            try:
                return await asyncio.to_thread(wikipedia.summary, query, sentences=2, auto_suggest=True)
            except (wikipedia.DisambiguationError, wikipedia.PageError):
                # If direct summary fails, perform a search
                search_results = await asyncio.to_thread(wikipedia.search, query)
                if not search_results:
                    raise Exception("No results found")
                
                # Try getting the summary of the first result without auto-suggest
                try:
                    return await asyncio.to_thread(wikipedia.summary, search_results[0], sentences=2, auto_suggest=False)
                except wikipedia.DisambiguationError as e:
                    # If it's a disambiguation page, pick the first actual option
                    if e.options:
                        return await asyncio.to_thread(wikipedia.summary, e.options[0], sentences=2, auto_suggest=False)
                    raise e
        except Exception:
            return (
                f"I couldn't find a direct answer for '{query}'. Try searching on Google: "
                f"https://www.google.com/search?q={query.replace(' ', '+')}"
            )

    # Email (placeholder)
    if "send email" in msg:
        return "To send an email, please provide the recipient, subject, and body. (Feature integration in progress)"

    return None
