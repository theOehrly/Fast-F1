import argparse
import sys

from fastf1.internals.f1account import (
    AUTH_METHODS,
    set_auth_method
)
from fastf1.livetiming.client import (
    SignalRClient,
    messages_from_raw
)


def save(args):
    mode = "a" if args.append else "w"
    if args.auth_method:
        set_auth_method(args.auth_method)
    client = SignalRClient(args.file, filemode=mode, debug=args.debug,
                           timeout=args.timeout, no_auth=args.no_auth)
    client.start()


def convert(args):
    with open(args.input) as infile:
        messages = infile.readlines()
    data, ec = messages_from_raw(messages)
    with open(args.output, "w") as outfile:
        for elem in data:
            outfile.write(str(elem)+"\n")
    print(f"Completed with {ec} error(s)")


parser = argparse.ArgumentParser(
    prog="python -m fastf1.livetiming",
    description="Save live timing data during a session",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)

subparsers = parser.add_subparsers()

rec_parser = subparsers.add_parser(
    "save", help="Save live timing data"
)
conv_parser = subparsers.add_parser(
    "extract", help="Extract messages from saved debug-mode data"
)

rec_parser.add_argument("file", type=str, help="Output file name")
rec_parser.add_argument("--append", action="store_true", default=False,
                        help="Append to output file. By default the file is "
                             "overwritten if it exists already.")
rec_parser.add_argument("--debug", action="store_true", default=False,
                        help="Enable debug mode: save full SignalR message, "
                             "not just the data.")
rec_parser.add_argument("--timeout", type=int, default=60,
                        help="Timeout in seconds after which the client will "
                             "automatically exit if no data is received.")
rec_parser.add_argument("--no-auth", action="store_true", default=False,
                        help="Connect without signing in to the Formula 1 "
                             "account. Data may be incomplete or missing.")
rec_parser.add_argument("--auth-method", choices=AUTH_METHODS, default=None,
                        help="Sign-in method for the Formula 1 account. "
                             "Defaults to the FASTF1_AUTH_METHOD environment "
                             "variable, else 'password'.")
rec_parser.set_defaults(func=save)

conv_parser.add_argument("input", type=str, help="Input file name")
conv_parser.add_argument("output", type=str, help="Output file name")
conv_parser.set_defaults(func=convert)

if not len(sys.argv) > 1:
    # user did not provide any arguments
    parser.print_help()
    parser.exit(1)

args = parser.parse_args()
args.func(args)  # call function associated with subparser
