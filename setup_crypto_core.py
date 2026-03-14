import os
import shutil

src = "crypto_core_dist"
dst = "crypto_core"

if not os.path.exists(src):
    print(f"ERROR: {src} directory not found")
    exit(1)

os.makedirs(dst, exist_ok=True)

for filename in os.listdir(src):
    src_path = os.path.join(src, filename)
    if os.path.isfile(src_path):
        shutil.copy2(src_path, os.path.join(dst, filename))
        print(f"Copied {filename} to {dst}/")

print("crypto_core setup complete")

import sys
import os

sys.path.insert(0, os.getcwd())
