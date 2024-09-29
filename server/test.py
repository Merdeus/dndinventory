import ssl
import time

from fastapi import FastAPI, Request, HTTPException
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
import uvicorn
import os

app = FastAPI()

client_list = {}
token_list = {}

registration_token_list = {}
random_val = 0
next_client_id = 0




@app.get("/register/{registration_token}")
async def register(request: Request, registration_token: str):

    res = registration_token_list.pop(registration_token, None)

    if res is None:
        raise HTTPException(status_code=400, detail="Invalid registration token!")
    
    ip = request.client.host

    if res.ip != ip:
        raise HTTPException(status_code=400, detail="Invalid registration token!")
    
    new_token = hash(int.from_bytes(os.urandom(8), byteorder="big"))
    new_server_side_identifier = hash(ip + new_token + random_val)

    client = Client(new_server_side_identifier, res.playerid)

    clientid = next_client_id
    next_client_id += 1

    client_list[clientid] = client
    token_list[new_server_side_identifier] = {"token": new_token, "playerid": res.playerid, "clientid": clientid}

    async def event_generator():
        try:

            # first message is the registration message
            yield {"type": "register", "clientid": clientid, "playerid": res.playerid, "token": new_token}

            while True:
                msg = await client.queue.get()
                yield {
                    "type": msg.type,
                    "data": json.dumps(msg)
                }
        except asyncio.CancelledError:
            client_list.pop(clientid, None)

    return EventSourceResponse(event_generator())


@app.get("/test")
async def register(request: Request):
    async def event_generator():
        try:

            yield "IP: " + request.client.host

            while True:
                yield json.dumps({
                    "type": "Info",
                    "data": str(time.time())
                })
                await asyncio.sleep(2)

        except asyncio.CancelledError:
            pass

    return EventSourceResponse(event_generator())


async def handle_adv_action(action_type : str, playerid : int, data):
    pass


@app.post("/action")
async def handle_action(request: Request):
    """Handle client actions via HTTP."""
    data = await request.json()
    action_type = data.get("action")

    # check if action type is provided
    if action_type is None:
        raise HTTPException(status_code=400, detail="Action type not provided")

    # Basic actions which happen without having a established EventSource connection

    if action_type == "createSession":
        # Example action: create a session and send feedback
        session_info = createNewGame(data["name"][:40], data["description"][:200], data["dm_pass"][:50])
        if session_info is None:
            raise HTTPException(status_code=400, detail="Failed to create session")

        client_id = data.get("client_id")
        await sendMessageToClient(client_id, {"type": "session_created", "session_info": session_info})
        return {"status": "Session created successfully"}

    elif action_type == "joinSession":
        # Example action: join a session
        join_info = joinSession(data["session_code"])
        if join_info is None:
            raise HTTPException(status_code=400, detail="Failed to join session")

        client_id = data.get("client_id")
        await sendMessageToClient(client_id, {"type": "joined_session", "join_info": join_info})
        return {"status": "Session joined successfully"}

    elif action_type == "resync":
        return {"status": "Resync successful"}


    # More advanced actions which require an established EventSource connection
    
    provided_token = data.get("token")
    if provided_token is None or ip is None:
        raise HTTPException(status_code=400, detail="Invalid request!")

    ip = request.client.host
    server_side_identifier = hash(ip + provided_token + random_val)
    
    if server_side_identifier not in token_list or token_list[server_side_identifier].token != provided_token:
        raise HTTPException(status_code=400, detail="Invalid request!")
    
    playerid = token_list[server_side_identifier].playerid
    clientid = token_list[server_side_identifier].clientid

    current_client = client_list.get(clientid, None)

    if current_client is None: # Client does not have a open sse connection
        raise HTTPException(status_code=400, detail="Invalid request!")

    return handle_adv_action(action_type, current_client, playerid, data)


if __name__ == "__main__":
    random_val = int.from_bytes(os.urandom(4), byteorder="big")
    uvicorn.run(app, host="0.0.0.0", port=8000)