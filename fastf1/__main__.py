import argparse
from random import randint
from asciimatics.screen import Screen

def demo(screen):
    while True:
        screen.print_at('Hello world!',
                        randint(0, screen.width), randint(0, screen.height),
                        colour=randint(0, screen.colours - 1),
                        bg=randint(0, screen.colours - 1))
        ev = screen.get_key()
        if ev in (ord('Q'), ord('q')):
            return
        screen.refresh()

Screen.wrapper(demo)

from fastf1.internals.f1auth import (
    clear_auth_token,
    get_auth_token,
    print_auth_status
)


def main():
    parser = argparse.ArgumentParser(
        description='FastF1 Command Line Interface',
        prog='python -m fastf1'
    )
    subparsers = parser.add_subparsers(dest='command')

    # authentication subparser
    auth_parser = subparsers.add_parser(
        'auth', help='F1 authentication commands'
    )

    auth_parser.add_argument(
        'service',
        action='store',
        choices=['f1tv'],
        help='Service to authenticate with'
    )

    auth_actions_group = auth_parser.add_mutually_exclusive_group()
    auth_actions_group.add_argument('--clear',
                                    action='store_true',
                                    help='Clear stored authentication token')
    auth_actions_group.add_argument('--authenticate',
                                    action='store_true',
                                    help='Authenticate with F1TV')
    auth_actions_group.add_argument('--status',
                                    action='store_true',
                                    help='Display authentication status')

    args = parser.parse_args()

    if (args.command == 'auth') and (args.service == 'f1tv'):
        if args.clear:
            clear_auth_token()
        elif args.authenticate:
            get_auth_token()
        elif args.status:
            print_auth_status()
        else:
            auth_parser.print_help()

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
