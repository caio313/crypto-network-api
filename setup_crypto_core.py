import os
import base64


def decode_and_write(env_var, file_path):
    """Decode base64 environment variable and write to file."""
    content = os.getenv(env_var)
    if content is None:
        print(f"Warning: Environment variable {env_var} not set")
        return

    try:
        decoded = base64.b64decode(content).decode("utf-8")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write(decoded)
        print(f"Written {file_path}")
    except Exception as e:
        print(f"Error processing {env_var}: {e}")


def main():
    # Ensure crypto_core directory exists
    os.makedirs("crypto_core", exist_ok=True)

    # Map environment variables to file paths
    files = [
        ("CRYPTO_CORE_COST", "crypto_core/cost.py"),
        ("CRYPTO_CORE_SAFETY", "crypto_core/safety.py"),
        ("CRYPTO_CORE_RELIABILITY", "crypto_core/reliability.py"),
        ("CRYPTO_CORE_SPEED", "crypto_core/speed.py"),
        ("CRYPTO_CORE_WEIGHTS", "crypto_core/weights.py"),
        ("CRYPTO_CORE_NORMALIZER", "crypto_core/normalizer.py"),
    ]

    for env_var, file_path in files:
        decode_and_write(env_var, file_path)

    # Create empty __init__.py
    init_path = "crypto_core/__init__.py"
    with open(init_path, "w") as f:
        f.write("")
    print(f"Written {init_path}")


if __name__ == "__main__":
    main()
