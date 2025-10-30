import fastapi
import uvicorn
import logging
# receive json data from python requests post client

app = fastapi.FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
@app.get("/ping")
async def ping():
    return {"message": "pong"}
@app.post("/screenshot")
async def screenshot(data: dict):
    logger.info("Screenshot received from client: %s", data['client_key'])
    # save data to file
    return {"message": "Screenshot received"}

@app.post("/keyboard")
async def keyboard(data: dict):
    logger.info("Keyboard data received from client: %s", data['client_key'])

    # save data to file
    return {"message": "Keyboard data received"}

@app.post("/mouse")
async def mouse(data: dict):
    logger.info("Mouse data received from client: %s", data['client_key'])
    # save data to file
    return {"message": "Mouse data received"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9200)