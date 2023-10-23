#!/usr/bin/env python3
import argparse
import cryptography.fernet


parser = argparse.ArgumentParser(description="Generates a key for cookie encryption")

if __name__ == "__main__":
    args = parser.parse_args()

    print(cryptography.fernet.Fernet.generate_key().decode("ascii"))
