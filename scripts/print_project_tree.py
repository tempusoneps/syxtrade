import os


def print_tree(start_path='.', prefix=''):
    entries = [e for e in os.listdir(start_path) if not e.startswith('.')]
    entries.sort()

    for index, entry in enumerate(entries):
        if entry == "venv":
            continue
        path = os.path.join(start_path, entry)
        connector = '└── ' if index == len(entries) - 1 else '├── '
        print(prefix + connector + entry)
        if os.path.isdir(path):
            extension = '    ' if index == len(entries) - 1 else '│   '
            print_tree(path, prefix + extension)


if __name__ == "__main__":
    print("📁 TempusOnePs:")
    print_tree("..")
