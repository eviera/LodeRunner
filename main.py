# Lode Runner - Entry point

import argparse

from game import Game


def _positive_int(value):
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("level must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("level must be 1 or greater")
    return parsed


def parse_args():
    parser = argparse.ArgumentParser(description="Run Lode Runner")
    parser.add_argument(
        "--level",
        type=_positive_int,
        default=1,
        help="visible level number to start on, starting at 1",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="enable temporary debug/test helpers",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    game = Game(initial_level=args.level - 1, test_mode=args.test)
    game.init()
    game.run()
