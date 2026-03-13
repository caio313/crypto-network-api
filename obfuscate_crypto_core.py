import os
import py_compile
import shutil


def main():
    source_dir = "crypto_core"
    dest_dir = "crypto_core_dist"

    # Remove existing dest_dir
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)

    # Create dest_dir
    os.makedirs(dest_dir, exist_ok=True)

    # Walk through source_dir
    for root, dirs, files in os.walk(source_dir):
        # Calculate relative path from source_dir
        rel_path = os.path.relpath(root, source_dir)
        dest_root = os.path.join(dest_dir, rel_path) if rel_path != "." else dest_dir

        # Create corresponding directory in dest_dir
        os.makedirs(dest_root, exist_ok=True)

        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                source_file = os.path.join(root, file)
                # Compile to bytecode
                dest_file = os.path.join(dest_root, file + "c")  # .pyc file
                py_compile.compile(source_file, dest_file)
                print(f"Compiled {source_file} -> {dest_file}")
            elif file == "__init__.py":
                # Copy __init__.py as is (empty)
                source_file = os.path.join(root, file)
                dest_file = os.path.join(dest_root, file)
                shutil.copy2(source_file, dest_file)
                print(f"Copied {source_file} -> {dest_file}")


if __name__ == "__main__":
    main()
