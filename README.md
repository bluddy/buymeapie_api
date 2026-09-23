# Buy Me a Pie! (buymeapie.com) API & Agent Tool

This tool allows direct programmatic access to read and modify shopping lists on [buymeapie.com](https://buymeapie.com).

## Overview

The Buy Me a Pie backend exposes a REST API at `https://api.buymeapie.com` authenticated using standard **HTTP Basic Authentication** (`username:pin`).

## Configuration

Credentials can be provided via environment variables or a `.env` file in the root directory:

```bash
BUYMEAPIE_LOGIN="your_username"
BUYMEAPIE_PIN="your_pin"
```

Alternatively, you can pass credentials explicitly to the CLI using `--login` and `--pin`, or into `BuyMeAPieClient(login=..., pin=...)`.

---

## Command Line Interface (CLI)

You or any AI agent can execute `buymeapie.py` directly from the terminal or shell.

### 1. View Shopping Lists
```bash
python buymeapie.py lists
```

### 2. View Items in a List
```bash
# View active (unpurchased) items in default "Shopping list"
python buymeapie.py items

# View active items in a specific list (e.g., "Costco" or "Weekly Grocery")
python buymeapie.py items "Weekly Grocery"

# Include purchased/checked-off items
python buymeapie.py items "Shopping list" --all

# Output raw JSON (recommended for AI agents)
python buymeapie.py items "Shopping list" --json
```

### 3. Add an Item
```bash
# Add to default "Shopping list"
python buymeapie.py add "Almond milk" --amount "2 cartons"

# Add to a specific list
python buymeapie.py add "Paper towels" -l "Costco" --amount "1 pack"
```

### 4. Check Off / Buy an Item
```bash
# Mark as purchased
python buymeapie.py buy "Almond milk"
```

### 5. Uncheck an Item (Restore to Active)
```bash
# Restore item to active
python buymeapie.py unbuy "Almond milk"
```

### 6. Delete an Item
```bash
# Delete item from list
python buymeapie.py delete "Almond milk"
```

### 7. Create a List
```bash
python buymeapie.py create-list "Weekend Party"
```

---

## Python Module Usage

Any agent or Python script can import `BuyMeAPieClient`:

```python
from buymeapie import BuyMeAPieClient

# Loads BUYMEAPIE_LOGIN and BUYMEAPIE_PIN automatically from environment or .env
client = BuyMeAPieClient()

# Or pass explicitly:
# client = BuyMeAPieClient(login="your_username", pin="your_pin")

# 1. Fetch lists
lists = client.get_lists()

# 2. Get active items in a list (by name or ID)
items = client.get_items("Shopping list")

# 3. Add an item
client.add_item("Shopping list", title="Apples", amount="1 kg")

# 4. Check off an item (mark purchased)
client.mark_purchased("Shopping list", "Apples", is_purchased=True)

# 5. Delete an item
client.delete_item("Shopping list", "Apples")
```

---

## Direct REST API Reference

| Operation | Method | Endpoint | Headers / Body |
|---|---|---|---|
| **Verify Auth** | `GET` | `https://api.buymeapie.com/bauth` | `Authorization: Basic <base64>` |
| **Get Lists** | `GET` | `https://api.buymeapie.com/lists` | `Authorization: Basic <base64>` |
| **Get Items** | `GET` | `https://api.buymeapie.com/lists/<list_id>/items` | `Authorization: Basic <base64>` |
| **Add Item** | `POST` | `https://api.buymeapie.com/lists/<list_id>/items` | JSON: `{"title": "Milk", "amount": "1L", "is_purchased": false}` |
| **Update Item** | `PUT` | `https://api.buymeapie.com/lists/<list_id>/items/<item_id>` | JSON: `{"title": "Milk", "amount": "1L", "is_purchased": true}` |
| **Delete Item** | `DELETE` | `https://api.buymeapie.com/lists/<list_id>/items/<item_id>` | `Authorization: Basic <base64>` |

### Basic Auth Header Calculation
For user `username` and PIN `pin`:
- Plaintext: `username:pin`
- Base64: Base64 encoding of `username:pin` (e.g. `dXNlcm5hbWU6cGlu`)
- Header: `Authorization: Basic <base64_encoded_string>`
