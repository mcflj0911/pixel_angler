"""The people out walking: the men, women and children who go about the town on their trips. Each has a first name and a story,
which moves on one part at a time with every talk. They stop and turn to face the angler while they talk, then walk on."""
NAMES = {
    "man": ["Dave", "Pete", "Harold", "Stan", "Ed"],
    "woman": ["Maggie", "Joan", "Ruth", "Carol", "Helen"],
    "child": ["Rosie", "Finn", "Alfie", "Poppy", "Ned"],
}

LINES = {
    "man": {
        "greet": ["Afternoon. Nice spot for it.", "Morning. Keep your hat on, it's breezy."],
        "chat": ["Quiet out here, isn't it.", "Good weather for reading the paper."],
    },
    "woman": {
        "greet": ["Morning! Lovely day for a stroll.", "Oh, hello. Pen gave me too many sandwiches, want one?"],
        "chat": ["The gulls are getting bold.", "I always walk the front before the shop opens."],
    },
    "child": {
        "greet": ["Hiya! Are you a real fisherman?", "Mum said not to talk to strangers, but you look nice."],
        "chat": ["Can I have a go with your rod?", "I've got a crab in my bucket!"],
    },
}

# Each person's story: a list of parts, given one per talk
STORIES = {
    "man": [
        ["I come down here every Sunday to read the paper.",
         "This week the headline was about the big carp in the pond.",
         "I reckon Old Ray is the one who knows where it lives.",
         "Right, I'll go and find him, then. Thanks for the tip."],
        ["I've been trying to sell my old boat for months.",
         "Gil says it's not seaworthy, which is true.",
         "I might just keep it for the pond instead.",
         "Good chatting. Mind how you go on those planks."],
    ],
    "woman": [
        ["I'm meeting my sister at the ice cream stall in an hour.",
         "She's late again, she always is.",
         "I've counted every bench on the front while I wait.",
         "Oh, there she is! Thanks for keeping me company."],
        ["I've lost my bonnet to the wind.",
         "It blew over the wall onto the beach.",
         "Sam fetched it back for me, but it's soaked through.",
         "I'm going to buy a new one at the souvenir stall."],
    ],
    "child": [
        ["I lost my ball in the reeds this morning.",
         "Old Ray helped me look, but we could not find it.",
         "Then I saw a silver flash by the jetty. It was a fish!",
         "Mum says I can go back for the ball with a grown-up, so I'm going to ask Gil."],
        ["My kite got stuck in the big tree by the playground.",
         "Lou climbed up and got it down for me.",
         "Now I want to fly it off the sand, but Sam says the wind is too strong.",
         "Next week I'll try again, when the red flags are down."],
    ],
}


def make_person(kind, rng):
    """A first name and a story for a walker of this kind. Returns the name and the story's parts."""
    return rng.choice(NAMES[kind]), list(rng.choice(STORIES[kind]))


def line_pool(kind):
    """The greetings and small talk for a walker of this kind."""
    return LINES[kind]
