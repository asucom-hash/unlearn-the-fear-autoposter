"""Search-friendly captions for the 180 original Unlearn The Fear quotes.

Instagram currently permits up to five hashtags per post (2026). Keep them
relevant; use descriptive natural-language keywords rather than tag stuffing.
"""
import re

# The original quote bank is organized into ten themes of eighteen quotes.
# Rotating a larger topic-specific tag bank makes tags more varied and precise.
TOPICS = (
    ("Overcome Fear", (
        "Building courage starts with one manageable step. You can face uncertainty, develop self-belief and keep moving forward without waiting to feel fearless.",
        "Confidence often follows action, not the other way round. This motivational reminder is about overcoming fear with small, brave decisions.",
        "Personal growth happens when you make room for courage alongside fear. Every step forward is a chance to strengthen your confidence.",
    ), ("#OvercomeFear", "#BuildCourage", "#SelfBelief", "#FaceYourFears", "#ConfidenceBuilding", "#BraveChoices", "#TakeTheFirstStep", "#MindsetGrowth")),
    ("Letting Go and Healing", (
        "Emotional healing is not about erasing the past. Letting go can help you move forward with self-compassion and more peace of mind.",
        "A fresh chapter can begin when you release what you no longer need to carry. Healing and inner peace are built one gentle choice at a time.",
        "Finding peace after change takes patience. This reminder is for anyone learning to let go, recover and choose a calmer future.",
    ), ("#LettingGo", "#EmotionalHealing", "#HealingJourney", "#InnerPeace", "#MovingForward", "#SelfCompassion", "#PeaceOfMind", "#EmotionalGrowth")),
    ("Calm Your Mind", (
        "Overthinking can make an uncertain moment feel bigger than it is. Mindfulness helps you notice difficult thoughts without letting them decide your next step.",
        "Finding inner calm begins with a little space between a thought and a reaction. Give yourself permission to slow down and return to the present.",
        "When your mind feels noisy, small moments of awareness can help you respond with care. This is a reminder to practise a calmer mindset.",
    ), ("#CalmYourMind", "#Overthinking", "#MindfulLiving", "#MindsetMatters", "#PresentMoment", "#InnerCalm", "#ThoughtAwareness", "#MindfulMoments")),
    ("Know Your Worth", (
        "Self-worth is not a competition or a deadline. Build confidence by honouring your own pace instead of comparing your path with someone else's.",
        "You do not need external approval to keep growing. Remember your value, trust your journey and practise healthy self-belief.",
        "Comparison can distract you from your own progress. Personal growth becomes more meaningful when you recognise the strengths you already have.",
    ), ("#SelfWorth", "#StopComparing", "#SelfConfidence", "#KnowYourValue", "#YourOwnJourney", "#SelfAcceptance", "#PersonalGrowth", "#BelieveInYourself")),
    ("Live in the Moment", (
        "A meaningful life is made from ordinary moments. Mindful living and gratitude help you notice what matters instead of always chasing what comes next.",
        "Slow down enough to enjoy the life happening around you. Being present can turn small moments into lasting memories.",
        "Joy is not something you have to postpone. Practising gratitude and presence can change how you experience everyday life.",
    ), ("#LiveInTheMoment", "#PracticeGratitude", "#MindfulLife", "#FindYourJoy", "#EnjoyTheLittleThings", "#BePresent", "#EverydayJoy", "#MeaningfulLife")),
    ("Self-Care and Boundaries", (
        "Self-care includes protecting your energy, making time to rest and setting healthy boundaries. You can care for others without forgetting your own needs.",
        "Rest and personal growth can belong in the same life. Respect your limits and remember that slowing down does not mean giving up.",
        "Being kind to yourself is part of building a sustainable, confident mindset. Healthy boundaries make room for both care and self-respect.",
    ), ("#SelfCare", "#HealthyBoundaries", "#ProtectYourPeace", "#RestIsProductive", "#SelfRespect", "#EmotionalWellbeing", "#GentleGrowth", "#ChooseYourself")),
    ("Growth Mindset and Resilience", (
        "Mistakes are part of learning, not proof you should stop. A growth mindset turns setbacks into opportunities to practise courage and resilience.",
        "Progress is built through imperfect attempts. Keep learning, believe in your ability to improve and allow yourself to begin again.",
        "Resilience is the decision to try another way after a difficult moment. Your personal growth is bigger than any single setback.",
    ), ("#GrowthMindset", "#KeepTrying", "#BuildResilience", "#LearnAndGrow", "#ProgressNotPerfection", "#RiseAfterFailure", "#KeepMovingForward", "#CourageToGrow")),
    ("Healthy Relationships", (
        "Healthy relationships leave room for honesty, respect and individuality. Choosing boundaries can strengthen connection without sacrificing your own peace.",
        "You deserve connections where you can be yourself. Self-respect and emotional wellbeing matter in every friendship and relationship.",
        "Personal growth sometimes changes the relationships around you. Kindness, clear boundaries and authenticity help you move forward.",
    ), ("#HealthyRelationships", "#RelationshipBoundaries", "#AuthenticConnections", "#SelfRespectMatters", "#EmotionalWellbeing", "#ChooseHealthyLove", "#RespectYourself", "#TrueFriendship")),
    ("Hope and New Beginnings", (
        "Hope does not mean every day will be easy. It means recognising that new beginnings and brighter moments remain possible.",
        "Difficult chapters are not the whole story. Hold on to hope, keep moving forward and allow yourself to imagine new possibilities.",
        "A positive mindset can begin with the belief that change is possible. Small signs of hope are worth noticing, even on hard days.",
    ), ("#ChooseHope", "#NewBeginnings", "#HopefulMindset", "#BetterDaysAhead", "#KeepTheFaith", "#PositiveChange", "#DailyHope", "#FindYourLight")),
    ("Gratitude and Positivity", (
        "Practising gratitude helps you notice the good already present in your life. Mindful appreciation can make an ordinary day feel more meaningful.",
        "A positive mindset is not about ignoring hard things. It is about making space for joy, kindness and thankfulness alongside them.",
        "Little moments of gratitude and connection deserve your attention. Celebrate everyday joy and the people who make life meaningful.",
    ), ("#DailyGratitude", "#PositiveMindset", "#EverydayHappiness", "#MindfulGratitude", "#SmallJoy", "#ChooseKindness", "#PresentMoment", "#AppreciateLife")),
)

PROMPTS = (
    "Save this reminder for the days you need it. What small step can you take today?",
    "Which part of this message speaks to you? Share your thoughts in the comments.",
    "Share this with someone who could use encouragement today.",
    "Take a moment to reflect: what would this look like in your own life?",
)

def build_post(quote, index):
    """Return an SEO-oriented headline and one shared IG/FB photo caption.

    Photo posts do not have a separate SEO title field on both Meta platforms;
    the headline is therefore placed visibly at the top of the caption.
    """
    if index < 0:
        raise ValueError("Quote index cannot be negative")
    topic, descriptions, tag_bank = TOPICS[(index // 18) % len(TOPICS)]
    excerpt = re.split(r"(?<=[.!?])\s+", quote.strip(), maxsplit=1)[0].rstrip(".!?")
    if len(excerpt) > 55:
        excerpt = excerpt[:55].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    headline = f"{topic}: {excerpt}"
    tags = ["#UnlearnTheFear"] + [tag_bank[(index * 3 + offset) % len(tag_bank)] for offset in range(4)]
    description = descriptions[index % len(descriptions)]
    prompt = PROMPTS[index % len(PROMPTS)]
    caption = (
        f"{headline} 🖤💛\n\n"
        f"“{quote}”\n\n"
        f"{description}\n\n"
        f"{prompt}\n\n"
        "Follow Unlearn The Fear for thoughtful motivation, mindset tips and personal growth.\n\n"
        + " ".join(tags)
    )
    if len(caption) > 2200:
        raise ValueError("Instagram caption exceeds 2,200 characters")
    return headline, caption
