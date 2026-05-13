# Lode Runner - Entry point

import argparse


def _parse_bool(value):
    value = value.lower()
    if value in ("1", "yes", "true", "on"):
        return True
    if value in ("0", "no", "false", "off"):
        return False
    raise argparse.ArgumentTypeError("usar yes/no, true/false, 1/0 u on/off")


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
    parser.add_argument(
        "--fullscreen",
        type=_parse_bool,
        default=False,
        metavar="yes|no",
        help="start in fullscreen mode (default: no)",
    )
    parser.add_argument(
        "--computer-control",
        type=_parse_bool,
        default=False,
        metavar="yes|no",
        help="enable mouse/click controls for Computer Use testing",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    from game import Game

    game = Game(
        initial_level=args.level - 1,
        test_mode=args.test,
        fullscreen=args.fullscreen,
        computer_control=args.computer_control,
    )
    game.init()
    game.run()
