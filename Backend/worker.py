"""Dedicated scheduler process. Run with: python worker.py"""
from signal import SIGINT, SIGTERM, signal
from threading import Event

from core.scheduler import iniciar_scheduler, scheduler


def main() -> None:
    stopped = Event()
    signal(SIGINT, lambda *_: stopped.set())
    signal(SIGTERM, lambda *_: stopped.set())
    iniciar_scheduler()
    try:
        stopped.wait()
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=True)


if __name__ == "__main__":
    main()
