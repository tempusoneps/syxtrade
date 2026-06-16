import json
import os


def load_config(args, log_queue):
    module = args.strategy
    current_folder = os.path.dirname(os.path.abspath(__file__))
    if module == "":
        cfg_file_path = os.path.dirname(current_folder) + "/config/config.json"
    else:
        cfg_file_path = os.path.dirname(current_folder) + "/strategies/" + module + "/config/config.json"
    is_file = os.path.isfile(cfg_file_path)
    if not is_file:
        exit("Could not find the config file")
    log_queue.log({"config_file": cfg_file_path})
    with open(cfg_file_path, "r") as f:
        return json.load(f)
