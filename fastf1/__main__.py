import argparse
import sys
from datetime import datetime

from fastf1.exceptions import F1AuthError
from fastf1.internals.f1account import (
    AUTH_METHODS,
    clear_token,
    get_auth_method,
    get_token,
    token_manager
)


def authenticate(method: str):
    try:
        get_token(force_renew=True, method=method)
    except F1AuthError as exc:
        print(f"Sign-in failed: {exc}")
        sys.exit(1)
    print("Sign-in successful.")


def print_status():
    print(f"Sign-in method: {get_auth_method()}")

    token = token_manager.get_stored()
    if token is None:
        print("Not authenticated")
        return

    if token.is_valid():
        expiry = datetime.fromtimestamp(token.expires_at)
        token_status = f"Expires {expiry:%Y-%m-%d %H:%M:%S}"
    else:
        token_status = "EXPIRED"
    claims = token.claims
    print(f"Token Status: {token_status}\n"
          f"Subscription Status: {claims.get('SubscriptionStatus')}\n"
          f"Subscribed Product: {claims.get('SubscribedProduct')}")


def main():
    parser = argparse.ArgumentParser(
        description="FastF1 Command Line Interface",
        prog="python -m fastf1"
    )
    subparsers = parser.add_subparsers(dest="command")

    # authentication subparser
    auth_parser = subparsers.add_parser(
        "auth", help="F1 authentication commands"
    )

    auth_parser.add_argument(
        "service",
        action="store",
        choices=["f1tv"],
        help="Service to authenticate with"
    )
    auth_parser.add_argument(
        "--method",
        choices=AUTH_METHODS,
        default=None,
        help="Sign-in method used with --authenticate. Defaults to the "
             "FASTF1_AUTH_METHOD environment variable, else 'password'."
    )

    auth_actions_group = auth_parser.add_mutually_exclusive_group()
    auth_actions_group.add_argument("--clear",
                                    action="store_true",
                                    help="Clear stored authentication token")
    auth_actions_group.add_argument("--authenticate",
                                    action="store_true",
                                    help="Authenticate with F1TV")
    auth_actions_group.add_argument("--status",
                                    action="store_true",
                                    help="Display authentication status")

    args = parser.parse_args()

    if (args.command == "auth") and (args.service == "f1tv"):
        if args.clear:
            clear_token()
        elif args.authenticate:
            authenticate(args.method or get_auth_method())
        elif args.status:
            print_status()
        else:
            auth_parser.print_help()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
