from util import LogLevel, discord_webhook_url, loglevel_prefixes
import requests
from datetime import datetime

enableDebugLog = True
printLogToConsole = True

def send_discord_message(msg):

    if not discord_webhook_url:
        return # No webhook URL set, don't send the message
    
    data = {
        "content": msg,
        "username": "DnD Logger"
    }

    # Send the POST request to Discord's webhook URL
    response = requests.post(discord_webhook_url, json=data)

    if response.status_code == 204:
        print("Message sent successfully")
    else:
        print(f"Failed to send message, status code: {response.status_code}")

def log(msg : str, level=LogLevel.INFO) -> None:

    if level == LogLevel.DEBUG and not enableDebugLog:
        return

    timestamp = datetime.now().strftime('[%H:%M:%S]')

    toAdd = timestamp + " " + loglevel_prefixes.get(level, "[?]") + " " + msg
    if printLogToConsole or level == LogLevel.ERROR:
        print(toAdd)

def logErrorAndNotify(msg : str) -> None:
    log(msg, level=LogLevel.ERROR)