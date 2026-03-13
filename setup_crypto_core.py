import os
import base64

modules = {
    "cost": os.environ.get("CRYPTO_CORE_COST"),
    "safety": os.environ.get("CRYPTO_CORE_SAFETY"),
    "reliability": os.environ.get("CRYPTO_CORE_RELIABILITY"),
    "speed": os.environ.get("CRYPTO_CORE_SPEED"),
    "weights": os.environ.get("CRYPTO_CORE_WEIGHTS"),
    "normalizer": os.environ.get("CRYPTO_CORE_NORMALIZER"),
}

os.makedirs("crypto_core", exist_ok=True)

with open("crypto_core/__init__.py", "w") as f:
    f.write("")

for name, value in modules.items():
    if value:
        code = base64.b64decode(value).decode("utf-8")
        with open(f"crypto_core/{name}.py", "w") as f:
            f.write(code)
        print(f"Written crypto_core/{name}.py")
    else:
        print(f"ERROR: CRYPTO_CORE_{name.upper()} not set")
        exit(1)

print("crypto_core setup complete")
