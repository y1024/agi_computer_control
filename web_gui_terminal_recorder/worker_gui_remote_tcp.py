import argparse
import threading
import json
import glob

import mss
import time
import os
import pathlib

from pynput import mouse
from pynput import keyboard

import requests
import base64

# import queue

# use tcp connection, if timed out, just discard all received data.

# we need three processes/threads

# one for screenshot, using mss, taking one and save to jpeg every one second

# one for keyboard events, using pynput

# one for mouse events, using pynput

# the entire thing will be saved under a specific directory

# file handles will be closed within the "finally" code block


# use queue for communication between processes/threads
# mouse_event_queue = queue.Queue()
# keyboard_event_queue = queue.Queue()
# screenshot_queue = queue.Queue()

def argument_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./worker_gui_remote_output",
        help="path to output directory",
    )
    parser.add_argument(
        "--config_file",
        type=str,
        default="worker_gui_remote_config.json",
        help="path to config file json",
    )
    return parser


def config_parser(config_file: str):
    with open(config_file, "r") as f:
        config = json.load(f)
    return config


def screenshot_worker(output_dir: str, sleep_interval=1):
    os.makedirs(output_dir, exist_ok=True)
    with mss.mss() as sct:
        while True:
            time.sleep(sleep_interval)
            timestamp = time.time()
            output_path = os.path.join(output_dir, "screenshot_%s.png" % timestamp)
            sct.shot(output=output_path)
            # screenshot_queue.put(output_path)


def keyboard_worker(output_file: str):
    with open(output_file, "a+") as f:

        def on_press(key):
            if type(key) != str:
                key = str(key)
            f.write(
                json.dumps(dict(event="key_press", key=key, timestamp=time.time()))
                + "\n"
            )
            f.flush()

        def on_release(key):
            if type(key) != str:
                key = str(key)
            f.write(
                json.dumps(dict(event="key_release", key=key, timestamp=time.time()))
                + "\n"
            )
            f.flush()

        with keyboard.Listener(
            on_press=on_press, on_release=on_release
        ) as keyboard_listener:
            keyboard_listener.join()


def mouse_worker(output_file: str):
    with open(output_file, "a+") as f:

        def on_move(x: int, y: int):
            f.write(
                json.dumps(dict(event="mouse_move", x=x, y=y, timestamp=time.time()))
                + "\n"
            )
            f.flush()

        def on_click(x: int, y: int, button: mouse.Button, pressed: bool):
            f.write(
                json.dumps(
                    dict(
                        event="mouse_click",
                        x=x,
                        y=y,
                        button=str(button),
                        pressed=pressed,
                        timestamp=time.time(),
                    )
                )
                + "\n"
            )
            f.flush()

        def on_scroll(x: int, y: int, dx: int, dy: int):
            f.write(
                json.dumps(
                    dict(
                        event="mouse_scroll",
                        x=x,
                        y=y,
                        dx=dx,
                        dy=dy,
                        timestamp=time.time(),
                    )
                )
                + "\n"
            )
            f.flush()

        with mouse.Listener(
            on_move=on_move, on_click=on_click, on_scroll=on_scroll
        ) as listener:
            listener.join()


def keyboard_and_mouse_worker(output_dir: str):
    mouse_output_file = os.path.join(output_dir, "mouse.log")
    keyboard_output_file = os.path.join(output_dir, "keyboard.log")

    mouse_thread = threading.Thread(
        target=mouse_worker, args=(mouse_output_file,), daemon=True
    )
    keyboard_thread = threading.Thread(
        target=keyboard_worker, args=(keyboard_output_file,), daemon=True
    )

    mouse_thread.start()
    keyboard_thread.start()

    for thread in [mouse_thread, keyboard_thread]:
        thread.join()


def request_worker(output_dir: str, remote_url: str, client_key: str, poll_interval=1):
    mouse_output_file = os.path.join(output_dir, "mouse.log")
    keyboard_output_file = os.path.join(output_dir, "keyboard.log")

    session = requests.Session()
    session.timeout = 5

    def cleanup_loop():

        # purge mouse log
        with open(mouse_output_file, "w") as f:
            f.write("")

        # purge keyboard log
        with open(keyboard_output_file, "w") as f:
            f.write("")

            # purge screenshot
        for screenshot_file in glob.glob(os.path.join(output_dir, "screenshot*.png")):
            os.remove(screenshot_file)

    def request_loop():
        # first, read keyboard and mouse logs
        with open(mouse_output_file, "r") as f:
            mouse_data = f.read()
        with open(keyboard_output_file, "r") as f:
            keyboard_data = f.read()

        # send data to remote server
        mouse_data = {
            "mouse": mouse_data,
            "client_key": client_key,
        }
        session.post(remote_url + "/mouse", json=mouse_data)
        keyboard_data = {
            "keyboard": keyboard_data,
            "client_key": client_key,
        }
        session.post(remote_url + "/keyboard", json=keyboard_data)
        # next, gather screenshots
        screenshot_filepaths = [
            os.listdir(output_dir)[i]
            for i in range(len(os.listdir(output_dir)))
            if os.listdir(output_dir)[i].endswith(".png")
        ]
        for screenshot_filepath in screenshot_filepaths:
            screenshot_file = os.path.join(output_dir, screenshot_filepath)
            with open(screenshot_file, "rb") as f:
                screenshot_data = f.read()
            screenshot_data = {
                "screenshot_base64": base64.b64encode(screenshot_data).decode("utf-8"),
                "screenshot_filename": screenshot_filepath,
                "client_key": client_key,
            }
            session.post(remote_url + "/screenshot", json=screenshot_data)

    while True:
        try:
            time.sleep(poll_interval)
            try:
                # first, check if server is alive
                session.get(remote_url + "/ping")
            except requests.exceptions.ConnectionError:
                print("Server is not alive. Waiting for it to come alive...")
                continue
            try:
                request_loop()
            except Exception as e:
                print(f"Error sending request: {e}")
                continue
        finally:
            cleanup_loop()


def main():
    parser = argument_parser()
    args = parser.parse_args()
    output_dir = args.output_dir
    config_file = args.config_file
    config = config_parser(config_file)
    remote_url = config["remote_url"]
    client_key = config["client_key"]

    # create the directory first
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)

    screenshot_thread = threading.Thread(
        target=screenshot_worker,
        kwargs=dict(
            output_dir=output_dir,
        ),
        daemon=True,
    )
    keyboard_and_mouse_thread = threading.Thread(
        target=keyboard_and_mouse_worker,
        kwargs=dict(
            output_dir=output_dir,
        ),
        daemon=True,
    )
    request_thread = threading.Thread(
        target=request_worker,
        kwargs=dict(
            output_dir=output_dir, remote_url=remote_url, client_key=client_key
        ),
        daemon=True,
    )
    print("Remote URL:", remote_url)
    print("Client Key:", client_key)
    print("Starting threads...")
    threads = [screenshot_thread, keyboard_and_mouse_thread, request_thread]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    finally:
        print("Worker GUI: Stopping threads...")


if __name__ == "__main__":
    main()
