import os
from dotenv import load_dotenv
from service_manager.cli import run


def main():
    load_dotenv()
    print("Starting Beauty Clinic Application...")
    run()


if __name__ == "__main__":
    main()
