import random

from fish import SPECIES

CONTRACTS_PER_DAY = 3


def make_contracts(day):
    """The local market posts three contracts each game day. Every player sees the same ones on the same day."""
    rng = random.Random(day)
    # Only species that do not need special tackle, so every contract can be filled
    species = [spec for area in SPECIES for spec in SPECIES[area] if not spec.get("requires")]
    contracts = []
    for _ in range(CONTRACTS_PER_DAY):
        spec = rng.choice(species)
        count = rng.randint(2, 3)
        min_lbs = round(rng.uniform(1, 4), 1) if rng.random() < 0.5 else None
        name = f"Need {count} {spec['name']}" + (f" over {min_lbs} lb" if min_lbs else "")
        contracts.append({
            "name": name, "species": spec["name"], "count": count, "min_lbs": min_lbs,
            "progress": 0, "price": int(spec["price"] * count * 1.5),  # The reward is shown in the price pill
        })
    return contracts


def log_fish(contracts, fish):
    """Counts a landed fish towards any open contract it fits. Returns the contracts it completed."""
    done = []
    for contract in contracts:
        if contract["progress"] >= contract["count"] or contract["species"] != fish.name:
            continue
        if contract["min_lbs"] and fish.lbs < contract["min_lbs"]:
            continue
        contract["progress"] += 1
        if contract["progress"] == contract["count"]:
            done.append(contract)
        break  # A fish only counts towards one contract
    return done
