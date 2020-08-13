import os
import sys
import yaml
import shutil
import pystray
import threading
from PIL import Image, ImageDraw
from time import time, sleep

ICON_SIZE = (32, 32)
ICON_COLOR = (79, 151, 238)
REFRESH_RATE = 15 # sec
DEFAULT_MOVE_AFTER = 24 * 5 # hours
FILES_NOTIFY = 10

running = True
trayicon = None
watching_path = None
copy_to_path = None
move_after = None
items_ignore = None

def quit():
    trayicon.stop()
    global running
    running = False

def trayicon_init():
    try:
        image = Image.open("icon.ico")
    except:
        image = Image.new('RGB', ICON_SIZE, ICON_COLOR)
    
    menu = pystray.Menu(
        pystray.MenuItem("Exit", quit),
        pystray.MenuItem("Open watching directory",
            lambda: os.startfile(watching_path)),
        pystray.MenuItem("Open destination directory",
            lambda: os.startfile(copy_to_path))
    )
    
    global trayicon
    trayicon = pystray.Icon("Desktop Cleaner", icon=image, menu=menu,
        title="Desktop Cleaner")
    trayicon.run()

def getusedtime(item):
    return max(os.path.getatime(item), 
        os.path.getctime(item), 
        os.path.getmtime(item))

def config_load():
    global watching_path
    global copy_to_path
    global move_after
    global items_ignore

    with open("config.yaml", "r") as config_file:
        try:
            config = yaml.safe_load(config_file)
            watching_path = config["watching_path"]
            copy_to_path = config["copy_to_path"]
            move_after = config["move_after"]
            items_ignore = config["items_ignore"]
        except yaml.YAMLError as e:
            print(e)
    
    if not items_ignore:
        items_ignore = []
    
    if not watching_path:
        watching_path = os.path.join(os.environ["HOMEPATH"], "Desktop")

    if not copy_to_path:
        copy_to_path = os.path.join(watching_path, "desktop_cleaner")
        items_ignore.append(os.path.basename(copy_to_path))
    if not os.path.exists(copy_to_path):
        try:
            os.mkdir(copy_to_path)
        except Exception as e:
            print(e)
    
    if not move_after:
        move_after = DEFAULT_MOVE_AFTER # a week
    
def scan():
    config_load()

    items = {item:getusedtime(os.path.join(watching_path, item)) 
        for item in os.listdir(watching_path)}

    for item in items_ignore:
        items.pop(item, None)

    moved = False
    for item, created in items.items():
        timedelta = (time() - created) / 3600
        if timedelta >= move_after:
            print("Moving '{}' (last used {}h ago) to {}"
                .format(item, round(timedelta, 1), copy_to_path))

            original = os.path.join(watching_path, item)
            destination = os.path.join(copy_to_path, item)
            while os.path.exists(destination):
                basename, ext = os.path.splitext(destination)
                destination = os.path.join(copy_to_path, basename + "-" + ext)
            try:
                shutil.move(original, destination)
                moved = True
            except Exception as e:
                print(e)
    
    if moved:
        total_items_moved = len(os.listdir(copy_to_path))
        if total_items_moved > FILES_NOTIFY:
            trayicon.notify("There are {} items moved from your desktop.\n"
                "Take a look!".format(total_items_moved),
                title="Desktop Cleaner")

def update_ignore():
    with open("config.yaml", "r") as config_file:
        config = yaml.safe_load(config_file)

        watching_path = config["watching_path"]
        if not watching_path:
            watching_path = os.path.join(os.environ["HOMEPATH"], "Desktop")
    
    config["items_ignore"] = os.listdir(watching_path)

    with open("config.yaml", "w") as config_file:
        yaml.dump(config, config_file)

def loop():
    while not trayicon: # Wait for trayicon initialization
        sleep(0)

    while running:
        scan()
        sleep(REFRESH_RATE)

def main():
    if "--update-ignore".lower() in sys.argv:
        update_ignore()
    else:
        watcher = threading.Thread(target=loop)
        watcher.start()

        trayicon_init()

        watcher.join()

if __name__ == "__main__":
    main()