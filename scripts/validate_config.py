import json
import importlib
import os
import sys

CONFIG_PATH = "../config/config.json"


def validate_service(module_path: str, class_name: str) -> bool:
    """
    Kiểm tra xem module và class có tồn tại hay không.
    """
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError:
        print(f"❌ Module not found: {module_path}")
        return False

    if hasattr(module, class_name):
        print(f"✅ Found: {module_path}.{class_name}")
        return True
    else:
        print(f"⚠️  Class '{class_name}' not found in module '{module_path}'")
        return False
    return False

def validate_config(config_path=CONFIG_PATH):
    """
    Validate file config.json:
    - Tồn tại file
    - Load được JSON
    - Module + class hợp lệ
    """
    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)

    # Đọc file JSON
    with open(config_path, "r") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ JSON invalid: {e}")
            sys.exit(1)

    print("🔍 Validating services...")

    services = config.get("services", {})
    all_ok = True

    for key, svc in services.items():
        # signals là list
        if isinstance(svc, list):
            for plugin in svc:
                ok = validate_service(plugin["module"], plugin["class"])
                all_ok &= ok
        else:
            ok = validate_service(svc["module"], svc["class"])
            all_ok &= ok

    if all_ok:
        print("\n✅ All services validated successfully!")
    else:
        print("\n❌ Some services failed validation.")
        sys.exit(1)


if __name__ == "__main__":
    validate_config()
