import random

from equipment import PART_BY_KEY, SLOTS, STARTING_PARTS
from bounty import log_fish, make_contracts
from journal import AREA_NAMES, claim_rewards, log_catch
from sponsors import SPONSORS
import story

WEAR_PENALTY = 0.35  # A fully worn part keeps only (1 - this) of its performance
LURE_DURABILITY = 100  # A lure starts with this much life. Each bite wears it down, and only a worn out lure is used up
LURE_BITE_WEAR = 25  # Durability a fish's bite costs the lure

BAIT_SHOP = [
    {"area": "pond", "name": "Worm Pack (x10)", "price": 25, "amount": 10,
     "desc": "Bait for the pond. Put it on the hook with a cast from the bank"},
    {"area": "shore", "name": "Paddletail Pack (x5)", "price": 30, "amount": 5,
     "desc": "A soft lure for the surf. Reel it through the water and tap Up to twitch it"},
    {"area": "boat", "name": "Metal Micro Jig (x3)", "price": 45, "amount": 3,
     "desc": "A jig for the open sea. Let it fall, then jerk it in rhythm"},
    # Attractants draw fish to the lure and make strikes more likely, for one cast each
    {"area": "pond", "name": "Garlic Scent (x5)", "price": 30, "amount": 5, "kind": "attractant",
     "desc": "Press F before you cast to scent that cast. Each scent is used up by one cast"},
    {"area": "shore", "name": "Clam Scent (x5)", "price": 40, "amount": 5, "kind": "attractant",
     "desc": "Press F before you cast to scent that cast. Each scent is used up by one cast"},
    {"area": "boat", "name": "Chum Block (x3)", "price": 60, "amount": 3, "kind": "attractant",
     "desc": "Press F before you cast to scent that cast. Each block is used up by one cast"},
]


# The food store on the walk: each item restores some of the angler's stamina when eaten
FOOD_SHOP = [
    {"key": "sandwich", "name": "Ham Sandwich", "price": 8, "energy": 40},
    {"key": "sports_drink", "name": "Sports Drink", "price": 6, "energy": 30},
    {"key": "coffee", "name": "Hot Coffee", "price": 4, "energy": 20},
    {"key": "ice_cream", "name": "Ice Cream", "price": 5, "energy": 15},
]
# Hiring a rowing boat lasts for the whole game day. It takes you out to fish the open sea.
BOAT_HIRE = {"key": "rowboat", "name": "Rowing boat for the day", "price": 40}
# A motor boat is bought once. It is always ready at the pier, so there is no daily hire fee
MOTOR_BOAT = {"key": "motorboat", "name": "Motor boat", "price": 350}

# Scents can be pressed from fish in the creel: this many fish make one scent for the zone being fished
SCENT_PRESS_FISH = 2
TANK_SLOTS = 6  # Fish the aquarium holds
TANK_PAY = 3  # Paid each game day for every fish in the aquarium
RIVALS = ("Old Ray", "Tom")  # The pond anglers, who keep a score against the angler each game day
RIVAL_PRIZE = 100  # Paid if the angler lands more fish than the best rival that day
BOAT_TRIP_WEAR = 25  # How worn the rowboat gets for each day it is taken out on the water
BOAT_BROKEN = 100  # A rowboat this worn cannot be hired until it is repaired
BOAT_REPAIR_BASE = 30  # Repairs cost this much, plus the wear
CUP_DAYS = 7  # The Pier Cup runs for a week
CUP_COUNT = 15  # Fish to land in the week for the Pier Cup
CUP_REWARD = 300
CORNER_REWARD = 250  # The tin hidden in the north-west corner, which is found by walking to it
RACE_PRIZE = 300  # The buoy race pays this, less a dollar a second, but never less than RACE_MIN_PRIZE
RACE_MIN_PRIZE = 50

# Side jobs the townsfolk give. The angler does one at a time, and it pays when they go back to the giver
JOB_OFFERS = [
    {"kind": "catch", "count": 3, "reward": 60, "title": "Catch 3 fish",
     "say": "Could you bring me three fish? Any kind will do."},
    {"kind": "catch", "count": 5, "reward": 110, "title": "Catch 5 fish",
     "say": "I'm feeding the whole picnic. Five fish, please."},
    {"kind": "sold", "count": 150, "reward": 40, "title": "Sell $150 of fish",
     "say": "Sell some fish for me at the shop. I'll pay you a little for the trouble."},
]
# The town contest is run each game day, and must be finished that day
CONTESTS = [
    {"kind": "catch", "count": 5, "reward": 150, "title": "Front race: land 5 fish today"},
    {"kind": "sold", "count": 200, "reward": 120, "title": "Sell $200 of fish at the shops today"},
    {"kind": "catch", "count": 2, "reward": 90, "title": "Land 2 fish in the same day"},
]

COOLER_SHOP = [
    {"key": "cooler_medium", "name": "Medium Cooler", "price": 120, "capacity": 10},
    {"key": "cooler_large", "name": "Large Cooler", "price": 300, "capacity": 16},
]


# Clothes for the angler. Each slot is coat, hat or trousers. The free ones are owned from the start.
CLOTHES = [
    {"key": "brown_coat", "name": "Brown Coat", "slot": "coat", "colour": (72, 60, 46), "price": 0},
    {"key": "oilskin", "name": "Yellow Oilskin", "slot": "coat", "colour": (226, 186, 52), "price": 150},
    {"key": "dark_cap", "name": "Dark Cap", "slot": "hat", "colour": (34, 30, 28), "price": 0},
    {"key": "red_cap", "name": "Red Cap", "slot": "hat", "colour": (186, 58, 48), "price": 60},
    {"key": "canvas", "name": "Canvas Trousers", "slot": "trousers", "colour": (96, 84, 60), "price": 0},
    {"key": "waders", "name": "Green Waders", "slot": "trousers", "colour": (70, 104, 66), "price": 120},
]
CLOTHES_BY_KEY = {item["key"]: item for item in CLOTHES}


class Economy:
    def __init__(self):
        self.money = 150
        self.motorboat = False  # Bought from the Boat Hire. Then a boat is always ready, with no daily fee
        self.tank = []  # Fish kept in the aquarium, each as {"name", "price"}, paid for each game day
        self.job = None  # The side job a townsperson has given, or None: {"giver", "kind", "count", "progress", "reward", "title"}
        self.contest = None  # Today's town contest, or None: {"kind", "count", "progress", "reward", "title", "paid"}
        self.day_catches = 0  # Fish the angler landed today, for the rivalry with the pond anglers
        self.rival_today = {name: 0 for name in RIVALS}  # Fish each rival landed today
        self.cup = None  # This week's Pier Cup: {"title", "count", "progress", "reward", "paid"}, or None
        self.cup_week = None  # The week the Pier Cup was last set
        self.trophies = []  # Pier Cups won, as text for the journal
        self.boat_wear = 0.0  # How worn the rowboat is, from 0 (new) to BOAT_BROKEN
        self.boat_used = False  # Whether the rowboat was out on the water today
        self.corner_found = False  # Whether the tin in the north-west corner has been found
        self.jobs_done = 0  # Side jobs paid for, which unlock the hidden fish
        self.best_race = None  # The fastest buoy race, in seconds
        self.boat_day = None  # The game day a rowing boat was last hired for
        self.bait = {"pond": 5, "shore": 0, "boat": 0}
        self.lure_hp = {"pond": LURE_DURABILITY, "shore": LURE_DURABILITY, "boat": LURE_DURABILITY}  # The lure on the line for each area
        self.attractant = {"pond": 0, "shore": 0, "boat": 0}  # Scent or chum left for each area, one used per cast
        self.owned = set(STARTING_PARTS)  # Every tackle part the angler has bought
        self.wardrobe = {item["key"] for item in CLOTHES if item["price"] == 0}  # Every piece of clothing owned
        self.outfit = {"coat": "brown_coat", "hat": "dark_cap", "trousers": "canvas"}  # The piece worn in each slot
        self.setup = {PART_BY_KEY[key]["slot"]: key for key in STARTING_PARTS}  # The part in use for each slot
        self.creel = []  # Caught fish waiting to be sold, each as {"name", "price"}
        self.creel_limit = 6  # How many fish the cooler holds before you need to sell
        self.total_caught = 0  # Lifetime stats, shown on the menu
        self.total_sold = 0
        self.catch_log = {}  # The field journal: per species, how many were caught and the personal bests
        self.claimed = set()  # Journal milestones whose rewards have been paid
        self.new_rewards = []  # Milestone messages the fishing scene should announce
        self.contracts = []  # Today's bounty contracts from the local market
        self.contract_day = None
        self.reputation = 0  # Earned by finishing contracts
        self.wear = {}  # Per part key: how worn it is, from 0 (new) to 100 (broken down)
        self.sponsors = set()  # Sponsor keys the angler has signed with
        self.zone_setups = {}  # The tackle setup kept for each fishing zone, so going there brings its own gear
        self.zone = None  # The zone whose setup is in use now
        self.story_index = 0  # The chapter of the story being played, from story.CHAPTERS
        self.story_progress = 0  # How far the angler has got with the chapter's job
        self.story_told = False  # Whether the giver has given the chapter's opening line
        self.story_ready = False  # The job is done, and the reward waits for the giver

    def switch_setup(self, area):
        """Going to a zone brings that zone's tackle. The setup in use is kept for the zone it was fished in,
        and a zone seen for the first time starts with the gear the angler already has."""
        if area == self.zone:
            return
        if self.zone is not None:
            self.zone_setups[self.zone] = dict(self.setup)
        self.zone = area
        self.setup = dict(self.zone_setups.setdefault(area, self.setup))

    def equipped(self, slot):
        return PART_BY_KEY[self.setup[slot]]

    def condition(self, slot):
        """Worn parts perform less. A fully worn part keeps (1 - WEAR_PENALTY) of its numbers."""
        wear = self.wear.get(self.setup[slot], 0)
        return 1 - WEAR_PENALTY * wear / 100

    def stats(self):
        """The combined numbers from every equipped part, used by the fishing scene.
        Rating and strength are not reduced by wear, so the fish you can catch does not change under you."""
        rod, reel, line, hook, scope = (self.equipped(slot) for slot in SLOTS)
        rod_c, reel_c, line_c, hook_c = (self.condition(slot) for slot in ("rod", "reel", "line", "hook"))
        return {
            "rating": rod["rating"], "power": rod["power"] * rod_c, "reach": rod["reach"] * rod_c,
            "speed": reel["speed"] * reel_c, "drag": reel["drag"] * reel_c,
            "strength": line["strength"], "stealth": line["stealth"] * line_c,
            "window": hook["window"] * hook_c, "tolerance": scope["tolerance"],
            "jobs_done": self.jobs_done,  # Hidden fish come to an angler who has done the townsfolk's jobs
        }

    def wear_part(self, slot, amount):
        """Wears the part in use for a slot. Used by the fishing scene as the line, rod, reel and hooks are put to work."""
        key = self.setup[slot]
        self.wear[key] = min(100.0, self.wear.get(key, 0) + amount)

    def repair_cost(self, key):
        # Repairs cost about half the part's value at full wear, with a floor so cheap parts are not free
        return max(10, round(max(PART_BY_KEY[key]["price"], 100) * self.wear[key] / 100 * 0.5))

    def repair_items(self):
        """Owned parts that are worn, for the shop's repair bench."""
        return [
            {"key": key, "name": PART_BY_KEY[key]["name"], "price": self.repair_cost(key), "wear": self.wear[key]}
            for key in sorted(self.owned) if self.wear.get(key, 0) > 0
        ]

    def repair(self, key):
        if self.wear.get(key, 0) <= 0:
            return False
        cost = self.repair_cost(key)
        if self.money < cost:
            return False
        self.money -= cost
        self.wear[key] = 0
        return True

    def sign_sponsor(self, sponsor):
        """Signing is free, and fits the signature part straight away."""
        if sponsor["key"] in self.sponsors or self.reputation < sponsor["reputation"]:
            return False
        self.sponsors.add(sponsor["key"])
        self.owned.add(sponsor["part"])
        self.setup[PART_BY_KEY[sponsor["part"]]["slot"]] = sponsor["part"]
        return True

    def record_catch(self, fish):
        """Returns False if the cooler is full, in which case the fish goes back in the water."""
        if len(self.creel) >= self.creel_limit:
            return False
        self.total_caught += 1
        self.creel.append({"name": fish.name, "price": fish.price})
        log_catch(self.catch_log, fish)
        self.new_rewards.extend(claim_rewards(self))
        for contract in log_fish(self.contracts, fish):
            self.money += contract["price"]
            self.reputation += 1
            self.new_rewards.append(f"Contract done: {contract['species']} (+${contract['price']})")
        self.advance_counts("catch", 1)
        self.day_catches += 1
        self.add_diary(fish)
        return True

    def add_diary(self, fish):
        """Adds a line to the diary on the species' page in the journal: the day, the weight and where it was caught.
        Only the last few are kept, so the page shows the latest catches."""
        entry = self.catch_log[fish.name]
        diary = entry.setdefault("diary", [])
        where = AREA_NAMES.get(self.zone, "the water")
        diary.append(f"Day {self.contract_day or 1}: {fish.lbs:.1f} lb from the {where}")
        del diary[:-3]

    def new_day(self, day):
        """Starts a new game day when the day changes: contracts, a new town contest, the rivalry and the boat's wear. It pays
        the sponsors and the aquarium, and starts a new Pier Cup each week."""
        if day != self.contract_day:
            if self.contract_day is not None:
                self.pay_sponsors()
                self.pay_tank()
                if self.contest and not self.contest["paid"]:
                    self.new_rewards.append(f"Missed the contest: {self.contest['title']}")
                self.settle_rivalry()
                self.wear_boat()
            self.contract_day = day
            self.contracts = make_contracts(day)
            self.contest = dict(CONTESTS[day % len(CONTESTS)], progress=0, paid=False)
            self.day_catches = 0
            self.rival_today = {name: 0 for name in RIVALS}
            week = day // CUP_DAYS
            if week != self.cup_week:
                if self.cup and not self.cup["paid"]:
                    self.new_rewards.append(f"Missed the {self.cup['title']}")
                self.cup_week = week
                self.cup = {"title": "Pier Cup", "count": CUP_COUNT, "progress": 0, "reward": CUP_REWARD, "paid": False}

    def rival_catch(self, name):
        """A pond angler landed a fish. The rivalry counts it for the day."""
        if name in self.rival_today:
            self.rival_today[name] += 1

    def settle_rivalry(self):
        """The angler is paid if they landed more fish than the best rival did that day. The rival's name is in the news either way."""
        best = max(self.rival_today, key=self.rival_today.get)
        if self.day_catches > self.rival_today[best]:
            self.money += RIVAL_PRIZE
            self.new_rewards.append(f"You out-fished {best}, {self.day_catches} to {self.rival_today[best]} (+${RIVAL_PRIZE})")
        else:
            self.new_rewards.append(f"{best} out-fished you, {self.rival_today[best]} to {self.day_catches}")

    def wear_boat(self):
        """A day out on the water wears the rowboat. Once it is broken, it is not hired until it is repaired."""
        if self.boat_used:
            self.boat_wear = min(BOAT_BROKEN, self.boat_wear + BOAT_TRIP_WEAR)
            self.boat_used = False
            if self.boat_wear >= BOAT_BROKEN:
                self.new_rewards.append("The rowboat is worn out. Repair it at the Boat Hire")

    def boat_repair_cost(self):
        return BOAT_REPAIR_BASE + round(self.boat_wear)

    def repair_boat(self):
        """Mends the rowboat. Returns False if it needs no repair, or the angler cannot pay."""
        if self.boat_wear <= 0 or self.money < self.boat_repair_cost():
            return False
        self.money -= self.boat_repair_cost()
        self.boat_wear = 0.0
        return True

    def finish_race(self, seconds):
        """The buoy race is over: round the buoy and home in this many seconds. Faster pays more, and the best time is kept."""
        reward = max(RACE_MIN_PRIZE, RACE_PRIZE - int(seconds))
        self.money += reward
        if self.best_race is None or seconds < self.best_race:
            self.best_race = seconds
        self.new_rewards.append(f"Buoy race: {seconds:.1f} s (+${reward})")
        return reward

    def found_corner(self):
        """The angler walked to the tin in the north-west corner. It pays once."""
        if self.corner_found:
            return False
        self.corner_found = True
        self.money += CORNER_REWARD
        self.new_rewards.append(f"You found a tin of money in the corner (+${CORNER_REWARD})")
        return True

    def advance_counts(self, kind, amount):
        """Counts catches or sales towards the townsfolk's job and today's contest. Pays the contest as soon as it is finished."""
        if self.job and self.job["kind"] == kind and self.job["progress"] < self.job["count"]:
            self.job["progress"] += amount
            if self.job["progress"] >= self.job["count"]:
                self.new_rewards.append(f"Job done: {self.job['title']}. Go back to {self.job['giver']}")
        contest = self.contest
        if contest and not contest["paid"] and contest["kind"] == kind:
            contest["progress"] += amount
            if contest["progress"] >= contest["count"]:
                contest["paid"] = True
                self.money += contest["reward"]
                self.new_rewards.append(f"Contest won: {contest['title']} (+${contest['reward']})")
        cup = self.cup
        if cup and not cup["paid"] and kind == "catch":
            cup["progress"] += amount
            if cup["progress"] >= cup["count"]:
                cup["paid"] = True
                self.money += cup["reward"]
                self.trophies.append(f"Pier Cup, week {self.cup_week + 1}")
                self.new_rewards.append(f"Pier Cup won! Trophy added to the journal (+${cup['reward']})")

    def talk_job(self, name, rng=random):
        """What a townsperson says about a side job: they offer one if the angler has none, reminds them of it, or pays it
        when it is done. Returns None if the angler is doing a job for someone else, so the talk stays as normal chat."""
        if self.job is None:
            offer = rng.choice(JOB_OFFERS)
            self.job = dict(offer, giver=name, progress=0)
            return f"{offer['say']} ({offer['title']}, pays ${offer['reward']})"
        if self.job["giver"] != name:
            return None
        job = self.job
        if job["progress"] < job["count"]:
            return f"Still need {job['count'] - job['progress']} more. Thanks for trying."
        self.money += job["reward"]
        self.jobs_done += 1
        self.new_rewards.append(f"Job paid: {job['title']} (+${job['reward']})")
        self.job = None
        return "Perfect, you did it! Here's your pay."

    def press_scent(self, area):
        """Presses the newest fish in the creel into a scent for the area. Returns False if there are not enough fish."""
        if len(self.creel) < SCENT_PRESS_FISH:
            return False
        for _ in range(SCENT_PRESS_FISH):
            self.creel.pop()
        self.attractant[area] += 1
        return True

    def tank_in(self, index):
        """Moves a fish from the creel into the aquarium. Returns False if the tank is full."""
        if len(self.tank) >= TANK_SLOTS or not 0 <= index < len(self.creel):
            return False
        self.tank.append(self.creel.pop(index))
        return True

    def tank_out(self, index):
        """Takes a fish from the aquarium back into the creel. Returns False if the cooler is full."""
        if len(self.creel) >= self.creel_limit or not 0 <= index < len(self.tank):
            return False
        self.creel.append(self.tank.pop(index))
        return True

    def pay_tank(self):
        if self.tank:
            pay = TANK_PAY * len(self.tank)
            self.money += pay
            self.new_rewards.append(f"Aquarium paid ${pay}")

    def reset(self):
        """Starts again as a new game, as a fresh save slot does."""
        self.__init__()

    def pay_sponsors(self):
        for sponsor in SPONSORS:
            if sponsor["key"] not in self.sponsors:
                continue
            if self.setup[PART_BY_KEY[sponsor["part"]]["slot"]] == sponsor["part"]:
                self.money += sponsor["pay"]
                self.new_rewards.append(f"{sponsor['name']} paid ${sponsor['pay']}")
            else:
                self.new_rewards.append(f"{sponsor['name']} paid nothing: fit their part")

    def buy_clothes(self, item):
        """Buys a piece of clothing and puts it on. Returns False if the angler already owns it or cannot pay."""
        if item["key"] in self.wardrobe or self.money < item["price"]:
            return False
        self.money -= item["price"]
        self.wardrobe.add(item["key"])
        self.wear_clothes(item)
        return True

    def wear_clothes(self, item):
        self.outfit[item["slot"]] = item["key"]

    def outfit_colours(self):
        """The colour of the coat, hat and trousers being worn, for the angler's body."""
        return {slot: CLOTHES_BY_KEY[key]["colour"] for slot, key in self.outfit.items()}

    def buy_cooler(self, item):
        if self.creel_limit >= item["capacity"] or self.money < item["price"]:
            return False
        self.money -= item["price"]
        self.creel_limit = item["capacity"]
        return True

    def buy_bait(self, item):
        if self.money < item["price"]:
            return False
        self.money -= item["price"]
        if item.get("kind") == "attractant":
            self.attractant[item["area"]] += item["amount"]
        else:
            self.bait[item["area"]] += item["amount"]
        return True

    def buy_food(self, item):
        if self.money < item["price"]:
            return False
        self.money -= item["price"]
        return True

    def hire_boat(self, day):
        """Hires a rowing boat for this game day. Returns False if there is no money, or a boat is already hired today."""
        if self.boat_hired(day) or self.boat_wear >= BOAT_BROKEN or self.money < BOAT_HIRE["price"]:
            return False
        self.money -= BOAT_HIRE["price"]
        self.boat_day = day
        return True

    def boat_hired(self, day):
        """Whether a boat is ready today: a motor boat always is, and a rowing boat lasts the day it was hired."""
        return self.motorboat or self.boat_day == day

    def buy_motorboat(self):
        if self.motorboat or self.money < MOTOR_BOAT["price"]:
            return False
        self.money -= MOTOR_BOAT["price"]
        self.motorboat = True
        return True

    def can_cast(self, area):
        """A lure can be cast while the one on the line has life left, or there is a spare in the stock."""
        return self.bait[area] > 0 or self.lure_hp[area] > 0

    def lure_bitten(self, area):
        """A fish bit the lure, which wears it down. A worn out lure is replaced from the stock, and is used up for good.
        Returns 'fresh' if a new lure was tied on, 'none' if the stock is empty, or None if the lure still has life."""
        self.lure_hp[area] -= LURE_BITE_WEAR
        if self.lure_hp[area] > 0:
            return None
        return self.lose_lure(area)

    def lose_lure(self, area):
        """The lure is gone, snagged or snapped away, or worn out. A spare from the stock takes its place."""
        if self.bait[area] > 0:
            self.bait[area] -= 1
            self.lure_hp[area] = LURE_DURABILITY
            return "fresh"
        self.lure_hp[area] = 0
        return "none"

    def use_attractant(self, area):
        """Spends one scent for a cast. Returns whether the lure is scented."""
        if self.attractant[area] <= 0:
            return False
        self.attractant[area] -= 1
        return True

    def buy_part(self, part):
        """Buying a part also fits it to its slot. The setup menu can swap it back later."""
        if part["key"] in self.owned or self.money < part["price"]:
            return False
        self.money -= part["price"]
        self.owned.add(part["key"])
        self.setup[part["slot"]] = part["key"]
        return True

    def equip(self, part):
        if part["key"] not in self.owned:
            return False
        self.setup[part["slot"]] = part["key"]
        return True

    def sell(self, index):
        fish = self.creel.pop(index)
        self.money += fish["price"]
        self.total_sold += fish["price"]
        self.advance_story("sold", None, fish["price"])
        self.advance_counts("sold", fish["price"])
        return fish

    def advance_story(self, kind, zone=None, amount=1):
        """Counts something the angler has done towards the chapter's job. kind is 'talk', 'catch' or 'sold'. A job with a zone
        only counts fish from that zone. When the count is reached the reward waits for the giver."""
        chapter = story.current(self)
        if chapter is None or self.story_ready:
            return
        goal = chapter["goal"]
        if goal["kind"] != kind or goal.get("zone", zone) != zone:
            return
        self.story_progress += amount
        if self.story_progress >= goal["count"]:
            self.story_ready = True
            self.new_rewards.append(f"{chapter['title']}: done. Go back to {chapter['giver']} for your reward")

    def talk_story(self, name):
        """The line the giver says about the chapter, or None if this angler has no story to tell. Handing in a finished
        chapter pays its reward and opens the next one."""
        chapter = story.current(self)
        if chapter is None or chapter["giver"] != name:
            return None
        if self.story_ready:
            self.story_index += 1
            self.story_progress = 0
            self.story_told = False
            self.story_ready = False
            self.money += chapter["reward"]
            self.new_rewards.append(f"Story: {chapter['title']} (+${chapter['reward']})")
            return chapter["done"]
        if not self.story_told:
            self.story_told = True
            return chapter["intro"]
        return chapter["reminder"]
