"""The story of Pier Town. Each chapter is a job one of the anglers gives the angler. The angler does what the job asks,
then goes back to the giver for the reward, and the next chapter opens. Progress is kept by the economy."""

CHAPTERS = [
    {"title": "Welcome to Pier Town", "giver": "Old Ray", "goal": {"kind": "talk", "count": 5},
     "task": "Say hello to all five anglers",
     "intro": "New face, eh? Make the rounds and say hello to everyone on the pier. Then come back and tell me who you met.",
     "reminder": "Keep going round the pier. Say hello to everyone you have not met yet.",
     "done": "Knew you'd make the rounds. Here's a little something for the bait.", "reward": 40},
    {"title": "The Lucky Spoon", "giver": "Old Ray", "goal": {"kind": "catch", "zone": "pond", "count": 3},
     "task": "Land three fish from the pond",
     "intro": "I dropped my lucky brass spoon off the jetty, and since then nothing I cast has landed. Land three from the pond "
              "and maybe the luck comes back.",
     "reminder": "I'm counting on you. Three from the pond, and I'll tell you where I think the spoon went.",
     "done": "Three in a row! Maybe I'll find that spoon one day. Take this for your trouble.", "reward": 60},
    {"title": "Surf's Up", "giver": "Marisol", "goal": {"kind": "catch", "zone": "shore", "count": 3},
     "task": "Land three fish from the shore",
     "intro": "Shore fishing is a knack. Land three from the surf and I'll show you the best spot for the tide.",
     "reminder": "Three from the surf. The tide's turning, so get on with it.",
     "done": "Look at you, reading the surf. Here's your share of the purse.", "reward": 90},
    {"title": "Out to Sea", "giver": "Ines", "goal": {"kind": "catch", "zone": "boat", "count": 1},
     "task": "Land a fish from the open sea",
     "intro": "The ships keep their distance, but the fish out past the pier don't. Hire a boat and land one from the open sea.",
     "reminder": "Hire a rowing boat and land one from the open sea.",
     "done": "Out past the surf, eh? Nobody else bothers. Here's your reward.", "reward": 150},
    {"title": "Picnic Money", "giver": "Pen", "goal": {"kind": "sold", "count": 300},
     "task": "Sell fish worth $300",
     "intro": "We're short on picnic money. Sell fish worth $300 at the shop, and I'll pay you back with a treat.",
     "reminder": "Sell fish at the shop until you have made $300.",
     "done": "That's the picnic sorted. Thank you, truly. You've earned it.", "reward": 120},
]


def current(economy):
    """The chapter being played now, or None once the story is told."""
    if economy.story_index < len(CHAPTERS):
        return CHAPTERS[economy.story_index]
    return None


def objective(economy):
    """What the story asks for next, for the journal and the objective line."""
    chapter = current(economy)
    if chapter is None:
        return "The story of the pier is told. Keep fishing, and see how far the big ones go."
    if economy.story_ready:
        return f"{chapter['title']}: go back to {chapter['giver']} for your reward"
    goal = chapter["goal"]
    return f"{chapter['title']}: {chapter['task']} ({economy.story_progress}/{goal['count']})"
