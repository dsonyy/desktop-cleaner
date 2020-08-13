"""
Desktop Cleaner

A few lines of code which keep old and unused files away from your desktop
forever!

Author:     Szymon "dsonyy" Bednorz
Github:     https://github.com/dsonyy/desktop-cleaner
License:    MIT License
"""
import os
import sys
import yaml
import shutil
import pystray
import threading
import logging
from PIL import Image
from time import time, sleep

ICON_SIZE = (32, 32)
ICON_COLOR = (79, 151, 238)
REFRESH_RATE = 60 # seconds

running = True
trayicon = None
watching_path = None
destination_path = None
move_file_after_hours = None
notify_after_files = None
items_ignore = None

def quit():
    """Quit application"""
    logging.info("Quitting")
    trayicon.stop()
    global running
    running = False

def trayicon_init():
    """Initialize trayicon"""
    try:
        image = Image.open("icon.ico")
    except:
        image = Image.new('RGB', ICON_SIZE, ICON_COLOR)
        logging.warning("Icon file not found")
    
    menu = pystray.Menu(
        pystray.MenuItem("Exit", quit),
        pystray.MenuItem("Open watching directory",
            lambda: os.startfile(watching_path)),
        pystray.MenuItem("Open destination directory",
            lambda: os.startfile(destination_path)))
    
    global trayicon
    trayicon = pystray.Icon("Desktop Cleaner", icon=image, menu=menu,
        title="Desktop Cleaner")
    trayicon.run()

def notify(text, ok=True):
    if ok:
        logging.info(text)
        trayicon.notify(text, title="Desktop Cleaner")
    else:
        logging.critical(text)
        trayicon.notify(text, title="Desktop Cleaner Critical")

def getusedtime(item):
    """Get the latest timestamp of file access, modification or creation"""
    return max(os.path.getatime(item), 
        os.path.getctime(item), 
        os.path.getmtime(item))

def config_load() -> bool:
    """Load variables from config.yaml"""
    global watching_path
    global destination_path
    global move_file_after_hours
    global items_ignore
    global notify_after_files

    try:
        with open("config.yaml", "r") as config_file:        
            config = yaml.safe_load(config_file)
            watching_path = config["watching_path"]
            destination_path = config["destination_path"]
            move_file_after_hours = config["move_file_after_hours"]
            notify_after_files = config["notify_after_files"]
            items_ignore = config["items_ignore"]
    except yaml.YAMLError:
        notify("An error occured while parsing config.yaml file.", False)
        return False
    except FileNotFoundError:
        notify("config.yaml file does not exist.", False)
        return False

    if not items_ignore:
        items_ignore = []
    
    if not watching_path:
        watching_path = os.path.join(os.environ["HOMEPATH"], "Desktop")
    if not os.path.exists(watching_path):
        notify("Watching path ({}) does not exist. "
            .format(os.path.abspath(watching_path)), False)
        return False

    if not destination_path:
        destination_path = os.path.join(watching_path, "desktop_cleaner")
        items_ignore.append(os.path.basename(destination_path))
    if not os.path.exists(destination_path):
        try:
            os.mkdir(destination_path)
        except OSError:
            notify("Destination path ({}) does not exist or cannot be created."
                .format(os.path.abspath(destination_path)), False)
            return False
    
    if not move_file_after_hours:
        move_file_after_hours = 24 * 5

    if not notify_after_files:
        notify_after_files = 10

    return True
    
def scan() -> bool:
    """Scan desktop and move unused files"""
    if not config_load():
        return False

    items = {item:getusedtime(os.path.join(watching_path, item)) 
        for item in os.listdir(watching_path)}

    for item in items_ignore:
        items.pop(item, None)

    moved = False
    for item, created in items.items():
        timedelta = (time() - created) / 3600
        if timedelta >= move_file_after_hours:
            original = os.path.join(watching_path, item)
            destination = os.path.join(destination_path, item)

            while os.path.exists(destination):
                basename, ext = os.path.splitext(destination)
                destination = os.path.join(destination_path, basename + "-" + ext)

            logging.info("Moving '{}' (last used {}h ago) to {}"
                .format(original, round(timedelta, 1), destination))

            try:
                shutil.move(original, destination)
                moved = True
            except shutil.Error:
                logging.warning("Error occured while moving '{}' to '{}'"
                    .format(original, destination))
                # shutil.move() copies files if it's unable to move them, so we
                # have to remove copied files
                try:
                    if os.path.isdir(destination):
                        shutil.rmtree(destination)
                    else:
                        os.remove(destination)
                except FileNotFoundError:
                    pass
            except PermissionError:
                logging.warning("Permission error occured while moving '{}' to '{}'"
                    .format(original, destination))
                # shutil.move() copies files if it's unable to move them, so we 
                # have to remove copied files
                try:
                    if os.path.isdir(destination):
                        shutil.rmtree(destination)
                    else:
                        os.remove(destination)
                except FileNotFoundError:
                    pass
    
    if moved:
        total_items_moved = len(os.listdir(destination_path))
        if total_items_moved >= notify_after_files:
            notify("There are {} unused items moved from your desktop. "
                "Take a look!".format(total_items_moved))
    
    return True

def update_ignore():
    """Collect every desktop file and put it on items_ignore in config.yaml"""
    with open("config.yaml", "r") as config_file:
        config = yaml.safe_load(config_file)

        watching_path = config["watching_path"]
        if not watching_path:
            watching_path = os.path.join(os.environ["HOMEPATH"], "Desktop")
    
    config["items_ignore"] = os.listdir(watching_path)

    with open("config.yaml", "w") as config_file:
        yaml.dump(config, config_file)

def loop():
    """Desktop scanning loop"""
    sleep(2) # Wait for trayicon initialization
    
    while running:
        if not scan():
            quit()
        else:
            sleep(REFRESH_RATE)

def main():
    try:
        logging.basicConfig(filename="desktop_cleaner.log", level=logging.INFO,
            format="%(asctime)s %(levelname)s: %(message)s")
        logging.info(50 * "-")
        logging.info("Starting")

        watcher = threading.Thread(target=loop)
        watcher.start()

        trayicon_init()

        watcher.join()
    except Exception as e:
        notify("Unexpected critical error occured.", False)
        logging.exception(e)

if __name__ == "__main__":
    main()