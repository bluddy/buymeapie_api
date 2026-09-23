#!/usr/bin/env python3
"""
Buy Me a Pie! (buymeapie.com) API Client & CLI
Enables reading and modifying shopping lists directly via the Buy Me a Pie REST API.
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any, Optional
import requests
from requests.auth import HTTPBasicAuth

# Ensure proper Unicode handling in Windows terminals
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_BASE_URL = "https://api.buymeapie.com"


def _load_env_file():
    """Load variables from .env if present."""
    if "BUYMEAPIE_LOGIN" in os.environ and "BUYMEAPIE_PIN" in os.environ:
        return

    candidate_paths = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(__file__), ".env"),
    ]

    try:
        from dotenv import load_dotenv, find_dotenv
        cwd_env = find_dotenv(usecwd=True)
        if cwd_env and os.path.isfile(cwd_env):
            load_dotenv(cwd_env)
        file_env = find_dotenv(usecwd=False)
        if file_env and os.path.isfile(file_env):
            load_dotenv(file_env)
    except ImportError:
        pass

    if "BUYMEAPIE_LOGIN" in os.environ and "BUYMEAPIE_PIN" in os.environ:
        return

    for path in candidate_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("'\"")
                        if k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass


class BuyMeAPieClient:
    def __init__(
        self,
        login: Optional[str] = None,
        pin: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL
    ):
        _load_env_file()
        self.login = login or os.getenv("BUYMEAPIE_LOGIN")
        self.pin = pin or os.getenv("BUYMEAPIE_PIN")
        if not self.login or not self.pin:
            raise ValueError(
                "Buy Me a Pie credentials missing. Please set BUYMEAPIE_LOGIN and BUYMEAPIE_PIN "
                "environment variables (or in .env), or pass login and pin to BuyMeAPieClient."
            )
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.login, self.pin)
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "BuyMeAPie-Agent/1.0"
        })

    def authenticate(self) -> Dict[str, Any]:
        """Verify credentials against /bauth endpoint."""
        resp = self.session.get(f"{self.base_url}/bauth")
        resp.raise_for_status()
        return resp.json()

    def get_lists(self) -> List[Dict[str, Any]]:
        """Fetch all shopping lists for the authenticated user."""
        resp = self.session.get(f"{self.base_url}/lists")
        resp.raise_for_status()
        return resp.json()

    def find_list(self, name_or_id: str) -> Dict[str, Any]:
        """Find a list by its ID or case-insensitive name."""
        lists = self.get_lists()
        # Direct ID match
        for l in lists:
            if l.get("id") == name_or_id:
                return l
        # Case-insensitive name match
        for l in lists:
            if l.get("name", "").lower() == name_or_id.lower():
                return l
        # Substring match
        for l in lists:
            if name_or_id.lower() in l.get("name", "").lower():
                return l
        raise ValueError(f"List '{name_or_id}' not found. Available lists: {[l.get('name') for l in lists]}")

    def get_items(self, list_name_or_id: str, include_purchased: bool = False) -> List[Dict[str, Any]]:
        """Fetch items for a specific list. Filters out deleted items."""
        lst = self.find_list(list_name_or_id)
        list_id = lst["id"]
        resp = self.session.get(f"{self.base_url}/lists/{list_id}/items")
        resp.raise_for_status()
        items = resp.json()

        result = []
        for it in items:
            if it.get("deleted"):
                continue
            if not include_purchased and it.get("is_purchased"):
                continue
            result.append(it)
        return result

    def add_item(self, list_name_or_id: str, title: str, amount: str = "") -> Dict[str, Any]:
        """Add a new item to the specified list."""
        lst = self.find_list(list_name_or_id)
        list_id = lst["id"]
        payload = {
            "title": title.strip(),
            "amount": amount.strip(),
            "is_purchased": False
        }
        resp = self.session.post(f"{self.base_url}/lists/{list_id}/items", json=payload)
        resp.raise_for_status()
        return resp.json()

    def _find_item(self, list_id: str, item_title_or_id: str) -> Dict[str, Any]:
        """Helper to find an active item by ID or title."""
        resp = self.session.get(f"{self.base_url}/lists/{list_id}/items")
        resp.raise_for_status()
        items = resp.json()

        # Try ID match first
        for it in items:
            if it.get("id") == item_title_or_id and not it.get("deleted"):
                return it

        # Match active (non-purchased) item by title
        for it in items:
            if it.get("title", "").lower() == item_title_or_id.lower() and not it.get("is_purchased") and not it.get("deleted"):
                return it

        # Fallback to any non-deleted item by title
        for it in items:
            if it.get("title", "").lower() == item_title_or_id.lower() and not it.get("deleted"):
                return it

        raise ValueError(f"Item '{item_title_or_id}' not found in list.")

    def update_item(
        self,
        list_name_or_id: str,
        item_title_or_id: str,
        title: Optional[str] = None,
        amount: Optional[str] = None,
        is_purchased: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update an existing item's title, amount, or purchase state."""
        lst = self.find_list(list_name_or_id)
        list_id = lst["id"]
        item = self._find_item(list_id, item_title_or_id)
        item_id = item["id"]

        payload = {
            "title": title if title is not None else item.get("title", ""),
            "amount": amount if amount is not None else item.get("amount", ""),
            "is_purchased": is_purchased if is_purchased is not None else item.get("is_purchased", False)
        }
        resp = self.session.put(f"{self.base_url}/lists/{list_id}/items/{item_id}", json=payload)
        resp.raise_for_status()
        return resp.json()

    def mark_purchased(self, list_name_or_id: str, item_title_or_id: str, is_purchased: bool = True) -> Dict[str, Any]:
        """Mark an item as purchased (or uncheck it)."""
        return self.update_item(list_name_or_id, item_title_or_id, is_purchased=is_purchased)

    def delete_item(self, list_name_or_id: str, item_title_or_id: str) -> None:
        """Delete an item from a list."""
        lst = self.find_list(list_name_or_id)
        list_id = lst["id"]
        item = self._find_item(list_id, item_title_or_id)
        item_id = item["id"]

        resp = self.session.delete(f"{self.base_url}/lists/{list_id}/items/{item_id}")
        resp.raise_for_status()

    def create_list(self, name: str) -> Dict[str, Any]:
        """Create a new shopping list."""
        payload = {
            "name": name,
            "items_purchased": 0,
            "items_not_purchased": 0
        }
        resp = self.session.post(f"{self.base_url}/lists", json=payload)
        resp.raise_for_status()
        return resp.json()

    def delete_list(self, list_name_or_id: str) -> None:
        """Delete an entire shopping list."""
        lst = self.find_list(list_name_or_id)
        list_id = lst["id"]
        resp = self.session.delete(f"{self.base_url}/lists/{list_id}")
        resp.raise_for_status()


def main():
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--login", default=argparse.SUPPRESS, help="Buy Me a Pie username (default: BUYMEAPIE_LOGIN env var or .env)")
    common_parser.add_argument("--pin", default=argparse.SUPPRESS, help="Buy Me a Pie PIN/password (default: BUYMEAPIE_PIN env var or .env)")
    common_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Output raw JSON (ideal for agent tool calling)")

    parser = argparse.ArgumentParser(description="Buy Me a Pie! CLI & Agent Tool", parents=[common_parser])
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # lists command
    subparsers.add_parser("lists", parents=[common_parser], help="List all shopping lists")

    # items command
    items_p = subparsers.add_parser("items", parents=[common_parser], help="List items in a shopping list")
    items_p.add_argument("list", nargs="?", default=None, help="List name or ID (default: 'Shopping list')")
    items_p.add_argument("--list", "-l", dest="list_opt", default=None, help="List name or ID")
    items_p.add_argument("--all", action="store_true", help="Include purchased/history items")

    # add command
    add_p = subparsers.add_parser("add", parents=[common_parser], help="Add item to a list")
    add_p.add_argument("item", help="Item name to add")
    add_p.add_argument("list", nargs="?", default=None, help="List name or ID (default: 'Shopping list')")
    add_p.add_argument("--list", "-l", dest="list_opt", default=None, help="List name or ID")
    add_p.add_argument("--amount", "-a", default="", help="Quantity or notes (e.g. '2 bottles', '500g')")

    # buy/check command
    buy_p = subparsers.add_parser("buy", parents=[common_parser], help="Mark item as bought / purchased")
    buy_p.add_argument("item", help="Item name or ID")
    buy_p.add_argument("list", nargs="?", default=None, help="List name or ID (default: 'Shopping list')")
    buy_p.add_argument("--list", "-l", dest="list_opt", default=None, help="List name or ID")

    # unbuy/uncheck command
    unbuy_p = subparsers.add_parser("unbuy", parents=[common_parser], help="Mark item as not purchased (restore to active)")
    unbuy_p.add_argument("item", help="Item name or ID")
    unbuy_p.add_argument("list", nargs="?", default=None, help="List name or ID (default: 'Shopping list')")
    unbuy_p.add_argument("--list", "-l", dest="list_opt", default=None, help="List name or ID")

    # delete command
    del_p = subparsers.add_parser("delete", parents=[common_parser], help="Delete item from a list")
    del_p.add_argument("item", help="Item name or ID")
    del_p.add_argument("list", nargs="?", default=None, help="List name or ID (default: 'Shopping list')")
    del_p.add_argument("--list", "-l", dest="list_opt", default=None, help="List name or ID")

    # create-list command
    cl_p = subparsers.add_parser("create-list", parents=[common_parser], help="Create a new shopping list")
    cl_p.add_argument("name", help="Name of the new list")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    login = getattr(args, "login", None)
    pin = getattr(args, "pin", None)
    is_json = bool(getattr(args, "json", False))

    client = BuyMeAPieClient(login=login, pin=pin)

    def get_target_list():
        return getattr(args, "list_opt", None) or getattr(args, "list", None) or "Shopping list"

    try:
        if args.command == "lists":
            lists = client.get_lists()
            if is_json:
                print(json.dumps(lists, indent=2))
            else:
                print(f"Lists ({len(lists)}):")
                for l in lists:
                    print(f" - {l.get('name')} [ID: {l.get('id')}]")

        elif args.command == "items":
            target_list = get_target_list()
            items = client.get_items(target_list, include_purchased=args.all)
            if is_json:
                print(json.dumps(items, indent=2))
            else:
                lst = client.find_list(target_list)
                print(f"Items in '{lst.get('name')}' ({len(items)}):")
                for it in items:
                    status = "[x]" if it.get("is_purchased") else "[ ]"
                    amt = f" ({it['amount']})" if it.get("amount") else ""
                    print(f" {status} {it['title']}{amt}")

        elif args.command == "add":
            target_list = get_target_list()
            item = client.add_item(target_list, args.item, amount=args.amount)
            if is_json:
                print(json.dumps(item, indent=2))
            else:
                amt = f" ({args.amount})" if args.amount else ""
                print(f"Added '{args.item}'{amt} to '{target_list}'.")

        elif args.command == "buy":
            target_list = get_target_list()
            item = client.mark_purchased(target_list, args.item, is_purchased=True)
            if is_json:
                print(json.dumps(item, indent=2))
            else:
                print(f"Marked '{args.item}' as purchased in '{target_list}'.")

        elif args.command == "unbuy":
            target_list = get_target_list()
            item = client.mark_purchased(target_list, args.item, is_purchased=False)
            if is_json:
                print(json.dumps(item, indent=2))
            else:
                print(f"Restored '{args.item}' to active in '{target_list}'.")

        elif args.command == "delete":
            target_list = get_target_list()
            client.delete_item(target_list, args.item)
            if is_json:
                print(json.dumps({"status": "success", "deleted": args.item}))
            else:
                print(f"Deleted '{args.item}' from '{target_list}'.")

        elif args.command == "create-list":
            lst = client.create_list(args.name)
            if is_json:
                print(json.dumps(lst, indent=2))
            else:
                print(f"Created list '{args.name}' [ID: {lst.get('id')}].")

    except Exception as e:
        if is_json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
