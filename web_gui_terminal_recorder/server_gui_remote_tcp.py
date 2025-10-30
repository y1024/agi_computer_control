import fastapi
import uvicorn
import logging
import pydantic


class KeyboardData(pydantic.BaseModel):
    keyboard: str
    client_key: str


class MouseData(pydantic.BaseModel):
    mouse: str
    client_key: str


class ScreenshotData(pydantic.BaseModel):
    screenshot_base64: str
    screenshot_filename: str
    client_key: str


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
    parsed_data = ScreenshotData(**data)
    logger.info("Screenshot received from client: %s", parsed_data.client_key)
    # save data to file
    return {"message": "Screenshot received"}


@app.post("/keyboard")
async def keyboard(data: dict):
    parsed_data = KeyboardData(**data)
    logger.info("Keyboard data received from client: %s", parsed_data.client_key)

    # save data to file
    return {"message": "Keyboard data received"}


@app.post("/mouse")
async def mouse(data: dict):
    parsed_data = MouseData(**data)
    logger.info("Mouse data received from client: %s", parsed_data.client_key)
    # save data to file
    return {"message": "Mouse data received"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9200)
