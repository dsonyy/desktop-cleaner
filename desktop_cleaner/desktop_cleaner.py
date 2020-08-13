import os
import sys
import yaml
import shutil
import logging
from time import time, sleep
from win10toast import ToastNotifier

def getusedtime(item):
    return max(os.path.getatime(item), 
               os.path.getctime(item), 
               os.path.getmtime(item))

def scan():
    with open("config.yaml", "r") as config_file:
        try:
            config = yaml.safe_load(config_file)
            watching_path = config["watching_path"]
            copy_to_path = config["copy_to_path"]
            move_after = config["move_after"]
            items_ignore = config["items_ignore"]
        except yaml.YAMLError as e:
            print(e)
    
    items = {item:getusedtime(os.path.join(watching_path, item)) for item in os.listdir(watching_path)}

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
        move_after = 7 * 24 # a week
    
    for item in items_ignore:
        items.pop(item, None)

    moved = False
    for item, created in items.items():
        timedelta = (time() - created) / 3600
        if timedelta >= move_after:
            print("Moving '{}' (last used {}h ago) to {}".format(
                item, round(timedelta, 1), copy_to_path))

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
        if total_items_moved > 10:
            ToastNotifier().show_toast("Desktop Cleaner", 
                "There are {} items moved from your desktop. Check them out!"
                .format(total_items_moved),
                duration=10)

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
    while True:
        scan()
        sleep(30)

def main():
    if "--update-ignore".lower() in sys.argv:
        update_ignore()
    else:
        loop()

if __name__ == "__main__":
    main()