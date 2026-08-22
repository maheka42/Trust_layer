"""Generate reproducible synthetic TrustLayer seed data."""

from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import DB_PATH, fetch_counts, get_connection, reset_db
from models import Chargeback, Device, Merchant, Transaction, User

RANDOM_SEED = 42
USER_COUNT = 50
TXN_MIN = 500
TXN_MAX = 800
NORMAL_RATIO = 0.70
FRAUD_RATIO = 0.20

FIRST_NAMES = [
    "Ava", "Noah", "Mia", "Liam", "Sofia", "Ethan", "Isla", "Mason", "Olivia", "Lucas",
    "Amara", "Kai", "Elena", "Owen", "Priya", "Julian", "Nora", "Caleb", "Zara", "Adrian",
    "Hana", "Mateo", "Leila", "Henry", "Anika", "Theo", "Maya", "James", "Aisha", "Daniel",
    "Yuki", "Samuel", "Ines", "Nathan", "Fatima", "Leo", "Chloe", "Ryan", "Sana", "Isaac",
    "Lara", "Omar", "Emma", "Victor", "Nia", "Hugo", "Rina", "Felix", "Tara", "Andre",
]
LAST_NAMES = [
    "Patel", "Nguyen", "Garcia", "Kim", "Silva", "Khan", "Rossi", "Muller", "Chen", "Costa",
    "Ahmed", "Dubois", "Nakamura", "Ivanov", "Fernandez", "Okafor", "Berg", "Santos", "Walsh", "Novak",
]
CITIES = [
    ("United States", "New York", 40.7128, -74.0060, "USD"),
    ("United States", "Austin", 30.2672, -97.7431, "USD"),
    ("United Kingdom", "London", 51.5074, -0.1278, "GBP"),
    ("Germany", "Berlin", 52.5200, 13.4050, "EUR"),
    ("France", "Paris", 48.8566, 2.3522, "EUR"),
    ("India", "Mumbai", 19.0760, 72.8777, "INR"),
    ("India", "Bengaluru", 12.9716, 77.5946, "INR"),
    ("Canada", "Toronto", 43.6532, -79.3832, "CAD"),
    ("Australia", "Sydney", -33.8688, 151.2093, "AUD"),
    ("Brazil", "Sao Paulo", -23.5505, -46.6333, "BRL"),
    ("Japan", "Tokyo", 35.6762, 139.6503, "JPY"),
    ("Singapore", "Singapore", 1.3521, 103.8198, "SGD"),
    ("Spain", "Madrid", 40.4168, -3.7038, "EUR"),
    ("Netherlands", "Amsterdam", 52.3676, 4.9041, "EUR"),
    ("United Arab Emirates", "Dubai", 25.2048, 55.2708, "AED"),
]
DEVICE_PROFILES = [
    ("mobile", "iOS", "Safari"),
    ("mobile", "Android", "Chrome"),
    ("desktop", "Windows", "Chrome"),
    ("desktop", "macOS", "Safari"),
    ("tablet", "iOS", "Safari"),
    ("desktop", "Windows", "Firefox"),
]
MERCHANT_CATALOG = [
    ("FreshMart Grocery", "grocery", "low", "5411"),
    ("Daily Grind Coffee", "food", "low", "5812"),
    ("City Transit", "transport", "low", "4111"),
    ("StreamFlix", "subscription", "low", "5815"),
    ("Home Utilities Co", "utilities", "low", "4900"),
    ("BookNook", "retail", "low", "5942"),
    ("GreenLeaf Pharmacy", "health", "low", "5912"),
    ("FitLoop Gym", "fitness", "low", "7997"),
    ("CloudMail Pro", "subscription", "low", "5734"),
    ("Corner Bakery", "food", "low", "5462"),
    ("Metro Fuel", "fuel", "low", "5541"),
    ("QuickBite Delivery", "food", "low", "5814"),
    ("Office Supply Hub", "retail", "low", "5943"),
    ("PetPals Store", "retail", "low", "5995"),
    ("Local Florist", "retail", "low", "5992"),
    ("Northwind Apparel", "retail", "medium", "5651"),
    ("Summit Electronics", "electronics", "medium", "5732"),
    ("Harbor Home Furnishings", "home", "medium", "5712"),
    ("AeroFly Tickets", "travel", "medium", "4511"),
    ("StayInn Hotels", "travel", "medium", "7011"),
    ("GlobeRent Cars", "travel", "medium", "7512"),
    ("Peak Outdoor Gear", "retail", "medium", "5941"),
    ("Lumen Jewelry", "luxury", "medium", "5944"),
    ("Vineyard Wines", "food", "medium", "5921"),
    ("Nova Concerts", "entertainment", "medium", "7922"),
    ("Atlas Marketplace", "marketplace", "medium", "5399"),
    ("PixelPlay Games", "entertainment", "medium", "5816"),
    ("Craft & Co", "retail", "medium", "5970"),
    ("Urban Spa", "personal_care", "medium", "7298"),
    ("BlueWave Telecom", "utilities", "medium", "4814"),
    ("GiftCard Galaxy", "gift_cards", "high", "6051"),
    ("CryptoRail Exchange", "crypto", "high", "6051"),
    ("LuckySpin Casino", "gambling", "high", "7995"),
    ("WireNow Money Transfer", "money_transfer", "high", "4829"),
    ("ShadowVPN", "digital_goods", "high", "5817"),
    ("NightOwl Adult Shop", "adult", "high", "5967"),
    ("RapidLoan Advance", "financial", "high", "6012"),
    ("Offshore Lux Boutique", "luxury", "high", "5948"),
    ("TokenDrop NFTs", "crypto", "high", "6051"),
    ("Anonymous Relays Inc", "digital_goods", "high", "5734"),
]
NORMAL_CATEGORIES = {
    "grocery", "food", "transport", "subscription", "utilities", "retail",
    "health", "fitness", "fuel", "personal_care",
}
TRAP_CATEGORIES = {"electronics", "home", "travel", "luxury", "entertainment"}
FRAUD_CATEGORIES = {"gift_cards", "crypto", "gambling", "money_transfer", "digital_goods", "adult", "financial"}
CHARGEBACK_REASONS = [
    "unauthorized_transaction",
    "card_not_present_fraud",
    "account_takeover",
    "stolen_card",
]


def _unique_id(prefix: str, index: int, width: int = 3) -> str:
    return f"{prefix}_{index:0{width}d}"


def _jitter(value: float, scale: float) -> float:
    return round(value + random.uniform(-scale, scale), 6)


def _ip_for_city(city: str, octet: int) -> str:
    seed_byte = (sum(ord(ch) for ch in city) + octet) % 200 + 20
    return f"{seed_byte}.{10 + (octet % 40)}.{(octet * 7) % 250}.{(octet * 13) % 250}"


def _card_last4(user_index: int) -> str:
    return f"{1000 + (user_index * 37) % 9000:04d}"


def generate_users() -> list[User]:
    users: list[User] = []
    used_emails: set[str] = set()
    used_phones: set[str] = set()
    start = datetime(2024, 1, 1)

    for i in range(USER_COUNT):
        first = FIRST_NAMES[i]
        last = LAST_NAMES[i % len(LAST_NAMES)]
        email = f"{first.lower()}.{last.lower()}{i:02d}@example.com"
        phone = f"+1-555-{1000 + i:04d}"
        if email in used_emails or phone in used_phones:
            raise RuntimeError("Duplicate user identity generated")
        used_emails.add(email)
        used_phones.add(phone)

        country, city, lat, lng, currency = CITIES[i % len(CITIES)]
        created_at = start + timedelta(days=i * 7, hours=i % 24)
        typical_avg = round(random.uniform(18.0, 140.0), 2)
        users.append(
            User(
                id=_unique_id("user", i + 1),
                full_name=f"{first} {last}",
                email=email,
                phone=phone,
                country=country,
                city=city,
                home_lat=lat,
                home_lng=lng,
                currency=currency,
                typical_avg_amount=typical_avg,
                created_at=created_at.isoformat(timespec="seconds"),
            )
        )
    return users


def generate_devices(users: list[User]) -> list[Device]:
    devices: list[Device] = []
    fingerprints: set[str] = set()
    device_n = 0

    for user_index, user in enumerate(users):
        device_count = 2 if user_index % 5 else 3
        for d in range(device_count):
            device_n += 1
            profile = DEVICE_PROFILES[(user_index + d) % len(DEVICE_PROFILES)]
            fingerprint = f"fp-{user.id}-{d}-{user_index:02d}{d}"
            if fingerprint in fingerprints:
                raise RuntimeError("Duplicate device fingerprint generated")
            fingerprints.add(fingerprint)
            first_seen = datetime.fromisoformat(user.created_at) + timedelta(days=d, hours=d)
            devices.append(
                Device(
                    id=_unique_id("dev", device_n),
                    user_id=user.id,
                    fingerprint=fingerprint,
                    device_type=profile[0],
                    os_name=profile[1],
                    browser=profile[2],
                    is_primary=1 if d == 0 else 0,
                    first_seen=first_seen.isoformat(timespec="seconds"),
                )
            )
    return devices


def generate_merchants() -> list[Merchant]:
    merchants: list[Merchant] = []
    names: set[str] = set()
    for i, (name, category, risk, mcc) in enumerate(MERCHANT_CATALOG):
        if name in names:
            raise RuntimeError("Duplicate merchant name in catalog")
        names.add(name)
        country = CITIES[i % len(CITIES)][0]
        merchants.append(
            Merchant(
                id=_unique_id("merch", i + 1),
                name=name,
                category=category,
                country=country,
                mcc=mcc,
                risk_level=risk,
            )
        )
    return merchants


def _merchants_by_categories(merchants: list[Merchant], categories: set[str]) -> list[Merchant]:
    matched = [m for m in merchants if m.category in categories]
    if not matched:
        raise RuntimeError(f"No merchants found for categories: {categories}")
    return matched


def _txn_timestamp(index: int, hour: int) -> datetime:
    base = datetime(2026, 1, 15, 0, 0, 0)
    return base + timedelta(minutes=index * 17, hours=hour % 24, seconds=index % 60)


def _build_transaction(
    *,
    txn_id: str,
    user: User,
    device: Device,
    merchant: Merchant,
    amount: float,
    timestamp: datetime,
    city: str,
    country: str,
    lat: float,
    lng: float,
    ip_octet: int,
    channel: str,
    ground_truth: str,
    user_index: int,
) -> Transaction:
    return Transaction(
        id=txn_id,
        user_id=user.id,
        device_id=device.id,
        merchant_id=merchant.id,
        amount=round(amount, 2),
        currency=user.currency,
        timestamp=timestamp.isoformat(timespec="seconds"),
        ip_address=_ip_for_city(city, ip_octet),
        city=city,
        country=country,
        latitude=lat,
        longitude=lng,
        channel=channel,
        payment_method="card",
        card_last4=_card_last4(user_index),
        ground_truth=ground_truth,  # type: ignore[arg-type]
    )


def generate_transactions(
    users: list[User],
    devices: list[Device],
    merchants: list[Merchant],
) -> list[Transaction]:
    devices_by_user: dict[str, list[Device]] = {}
    for device in devices:
        devices_by_user.setdefault(device.user_id, []).append(device)

    normal_merchants = _merchants_by_categories(merchants, NORMAL_CATEGORIES)
    trap_merchants = _merchants_by_categories(merchants, TRAP_CATEGORIES)
    fraud_merchants = _merchants_by_categories(merchants, FRAUD_CATEGORIES)

    total = random.randint(TXN_MIN, TXN_MAX)
    n_normal = int(total * NORMAL_RATIO)
    n_fraud = int(total * FRAUD_RATIO)
    n_trap = total - n_normal - n_fraud
    labels = (["normal"] * n_normal) + (["fraud"] * n_fraud) + (["trap"] * n_trap)
    random.shuffle(labels)

    transactions: list[Transaction] = []
    seen_keys: set[tuple[str, str, float, str]] = set()
    seen_ids: set[str] = set()

    for i, label in enumerate(labels):
        user_index = i % len(users)
        user = users[user_index]
        user_devices = devices_by_user[user.id]
        primary = next(d for d in user_devices if d.is_primary == 1)
        txn_id = _unique_id("txn", i + 1, width=4)
        if txn_id in seen_ids:
            raise RuntimeError("Duplicate transaction id generated")
        seen_ids.add(txn_id)

        if label == "normal":
            merchant = normal_merchants[i % len(normal_merchants)]
            amount = max(4.0, random.gauss(user.typical_avg_amount, user.typical_avg_amount * 0.25))
            hour = random.choice([8, 9, 12, 13, 18, 19, 20])
            timestamp = _txn_timestamp(i, hour)
            txn = _build_transaction(
                txn_id=txn_id,
                user=user,
                device=primary,
                merchant=merchant,
                amount=amount,
                timestamp=timestamp,
                city=user.city,
                country=user.country,
                lat=_jitter(user.home_lat, 0.02),
                lng=_jitter(user.home_lng, 0.02),
                ip_octet=i,
                channel=random.choice(["online", "pos"]),
                ground_truth="normal",
                user_index=user_index,
            )
        elif label == "trap":
            merchant = trap_merchants[i % len(trap_merchants)]
            amount = user.typical_avg_amount * random.uniform(4.5, 9.0)
            hour = random.choice([1, 2, 3, 22, 23])
            timestamp = _txn_timestamp(i, hour)
            travel_city = CITIES[(user_index + 5) % len(CITIES)]
            use_travel = merchant.category == "travel" or i % 3 == 0
            city, country, lat, lng = (
                (travel_city[1], travel_city[0], travel_city[2], travel_city[3])
                if use_travel
                else (user.city, user.country, user.home_lat, user.home_lng)
            )
            txn = _build_transaction(
                txn_id=txn_id,
                user=user,
                device=primary,
                merchant=merchant,
                amount=amount,
                timestamp=timestamp,
                city=city,
                country=country,
                lat=_jitter(lat, 0.03),
                lng=_jitter(lng, 0.03),
                ip_octet=i + 300,
                channel="online",
                ground_truth="trap",
                user_index=user_index,
            )
        else:
            merchant = fraud_merchants[i % len(fraud_merchants)]
            amount = user.typical_avg_amount * random.uniform(8.0, 22.0)
            hour = random.choice([0, 1, 2, 3, 4])
            timestamp = _txn_timestamp(i, hour)
            remote = CITIES[(user_index + 9) % len(CITIES)]
            # Fraud uses a non-primary device when available; otherwise the primary
            # with a clearly remote location / high-risk merchant.
            device = user_devices[-1] if len(user_devices) > 1 else primary
            txn = _build_transaction(
                txn_id=txn_id,
                user=user,
                device=device,
                merchant=merchant,
                amount=amount,
                timestamp=timestamp,
                city=remote[1],
                country=remote[0],
                lat=_jitter(remote[2], 0.08),
                lng=_jitter(remote[3], 0.08),
                ip_octet=i + 700,
                channel="online",
                ground_truth="fraud",
                user_index=user_index,
            )

        key = (txn.user_id, txn.timestamp, txn.amount, txn.merchant_id)
        if key in seen_keys:
            raise RuntimeError("Duplicate transaction record generated")
        seen_keys.add(key)
        transactions.append(txn)

    return transactions


def generate_chargebacks(transactions: list[Transaction]) -> list[Chargeback]:
    """Attach a small historical chargeback set to a subset of fraud transactions."""
    fraud_txns = [txn for txn in transactions if txn.ground_truth == "fraud"]
    selected = fraud_txns[::7][:24]
    chargebacks: list[Chargeback] = []
    seen_txn_ids: set[str] = set()

    for n, txn in enumerate(selected, start=1):
        if txn.id in seen_txn_ids:
            raise RuntimeError("Duplicate chargeback for transaction")
        seen_txn_ids.add(txn.id)
        filed_at = datetime.fromisoformat(txn.timestamp) + timedelta(days=2 + (n % 10), hours=4)
        chargebacks.append(
            Chargeback(
                id=_unique_id("cb", n),
                transaction_id=txn.id,
                user_id=txn.user_id,
                amount=txn.amount,
                reason=CHARGEBACK_REASONS[n % len(CHARGEBACK_REASONS)],
                status="open" if n % 4 else "won",
                filed_at=filed_at.isoformat(timespec="seconds"),
            )
        )
    return chargebacks


def insert_all(
    conn,
    users: list[User],
    devices: list[Device],
    merchants: list[Merchant],
    transactions: list[Transaction],
    chargebacks: list[Chargeback],
) -> None:
    conn.executemany(
        """
        INSERT INTO users (
            id, full_name, email, phone, country, city, home_lat, home_lng,
            currency, typical_avg_amount, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                u.id, u.full_name, u.email, u.phone, u.country, u.city,
                u.home_lat, u.home_lng, u.currency, u.typical_avg_amount, u.created_at,
            )
            for u in users
        ],
    )
    conn.executemany(
        """
        INSERT INTO devices (
            id, user_id, fingerprint, device_type, os_name, browser, is_primary, first_seen
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (d.id, d.user_id, d.fingerprint, d.device_type, d.os_name, d.browser, d.is_primary, d.first_seen)
            for d in devices
        ],
    )
    conn.executemany(
        """
        INSERT INTO merchants (id, name, category, country, mcc, risk_level)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [(m.id, m.name, m.category, m.country, m.mcc, m.risk_level) for m in merchants],
    )
    conn.executemany(
        """
        INSERT INTO transactions (
            id, user_id, device_id, merchant_id, amount, currency, timestamp,
            ip_address, city, country, latitude, longitude, channel,
            payment_method, card_last4, ground_truth
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                t.id, t.user_id, t.device_id, t.merchant_id, t.amount, t.currency,
                t.timestamp, t.ip_address, t.city, t.country, t.latitude, t.longitude,
                t.channel, t.payment_method, t.card_last4, t.ground_truth,
            )
            for t in transactions
        ],
    )
    conn.executemany(
        """
        INSERT INTO chargebacks (
            id, transaction_id, user_id, amount, reason, status, filed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (c.id, c.transaction_id, c.user_id, c.amount, c.reason, c.status, c.filed_at)
            for c in chargebacks
        ],
    )
    conn.commit()


def print_sample_transactions(conn) -> None:
    query = """
        SELECT id, user_id, device_id, merchant_id, amount, currency,
               timestamp, city, country, ground_truth
        FROM transactions
        WHERE ground_truth = ?
        ORDER BY id
        LIMIT 3
    """
    for label in ("normal", "fraud", "trap"):
        rows = conn.execute(query, (label,)).fetchall()
        print(f"\nSample {label} transactions:")
        for row in rows:
            print(
                f"  {row['id']} user={row['user_id']} device={row['device_id']} "
                f"merchant={row['merchant_id']} amount={row['amount']} {row['currency']} "
                f"at={row['timestamp']} loc={row['city']}, {row['country']} "
                f"ground_truth={row['ground_truth']}"
            )


def seed() -> dict[str, int]:
    random.seed(RANDOM_SEED)
    users = generate_users()
    devices = generate_devices(users)
    merchants = generate_merchants()
    transactions = generate_transactions(users, devices, merchants)
    chargebacks = generate_chargebacks(transactions)

    conn = get_connection()
    try:
        reset_db(conn)
        insert_all(conn, users, devices, merchants, transactions, chargebacks)
        counts = fetch_counts(conn)
        print(f"Database created: {DB_PATH}")
        print(f"Database exists: {DB_PATH.exists()}")
        print(f"users: {counts['users']}")
        print(f"transactions: {counts['transactions']}")
        print(f"normal: {counts['normal']}")
        print(f"fraud: {counts['fraud']}")
        print(f"traps: {counts['traps']}")
        print(f"devices: {counts['devices']}")
        print(f"merchants: {counts['merchants']}")
        print(f"chargebacks: {counts['chargebacks']}")
        print_sample_transactions(conn)
    finally:
        conn.close()
    return counts


def main() -> None:
    seed()


if __name__ == "__main__":
    main()
