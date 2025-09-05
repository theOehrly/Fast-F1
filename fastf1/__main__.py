import argparse

from fastf1.internals.f1auth import (
    clear_auth_token,
    get_auth_token,
    print_auth_status,
    print_auth_token
)


def main():
    parser = argparse.ArgumentParser(
        description='FastF1 Command Line Interface',
        prog='python -m fastf1'
    )
    subparsers = parser.add_subparsers(dest='command')

    # f1auth subparser
    auth_parser = subparsers.add_parser(
        'f1auth', help='F1 authentication commands'
    )
    actions_group = auth_parser.add_mutually_exclusive_group()
    actions_group.add_argument('--clear',
                               action='store_true',
                               help='Clear stored authentication token')
    actions_group.add_argument('--authenticate',
                               action='store_true',
                               help='Authenticate with F1TV')
    actions_group.add_argument('--status',
                               action='store_true',
                               help='Display authentication status')
    actions_group.add_argument('--print-token',
                               action='store_true',
                               help='Print stored authentication token')

    args = parser.parse_args()

    if args.command == 'f1auth':
        if args.clear:
            clear_auth_token()
        elif args.authenticate:
            get_auth_token()
        elif args.status:
            print_auth_status()
        elif args.print_token:
            print_auth_token()
        else:
            auth_parser.print_help()

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
