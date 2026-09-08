"""
Synthetic WhatsApp-style group chat generator.
Produces messages.json: 8 participants, 6 months, 4000+ messages, Hinglish/code-mixed,
with 3 embedded "decision threads" whose key messages are hand-authored (so we can
later build a ground-truth eval set by matching exact text, not by guessing IDs).
"""
import json
import random
from datetime import datetime, timedelta

random.seed(42)

PARTICIPANTS = ["Priya", "Rohan", "Aman", "Sneha", "Vikram", "Neha", "Karan", "Ishaan"]

START_DATE = datetime(2025, 3, 1)
END_DATE = datetime(2025, 8, 31)
TOTAL_DAYS = (END_DATE - START_DATE).days

# ---------------------------------------------------------------------------
# Filler / noise message banks (the "4000 messages" bulk)
# ---------------------------------------------------------------------------

GREETINGS = [
    "good morning guys", "gm", "subha subha kya scene hai", "kaisa hai sab",
    "aaj kya plan hai", "kya haal chaal", "hii", "yo", "sabko good morning",
    "uth gaye sab?", "aaj weather bahut acha hai yaar",
]

ONE_WORD = [
    "ok", "okay", "haan", "nahi", "lol", "😂", "haha", "sahi", "theek hai",
    "kya?", "sure", "done", "👍", "hmm", "acha", "achha", "bilkul", "yes",
    "no", "kab?", "kyu", "wait", "1 min", "😭", "💀", "lmao", "fr fr",
]

CHITCHAT = [
    "aaj bahut kaam tha yaar office mein",
    "movie dekhne chalein is weekend?",
    "maine wo naya cafe try kiya, decent hai",
    "traffic bahut zyada hai aaj",
    "kal exam hai mera, padhna padega",
    "yaar mujhe bahut neend aa rahi hai",
    "kisi ne notes bheje the wo bhejo dobara",
    "internet down tha mera 2 ghante",
    "aaj lunch mein kya khaya sabne",
    "weekend pe ghar ja raha hu",
    "naya phone liya maine finally",
    "gym chalu kiya wapas se",
    "assignment submit kar diya raat ko",
    "boss ne aaj bahut daata",
    "chai peene chalo koi",
    "wifi phir se down hai mere yaha",
    "kal raat ko movie dekhi, average thi",
    "kisi ke paas extra charger hai kya",
    "maine resignation de diya 😭",
    "naya restaurant khula hai mall ke paas",
    "kal se diet start karunga pakka",
    "cricket match dekh rahe ho kya sab",
    "mera laptop crash ho gaya suddenly",
    "long weekend aa raha hai next month",
    "kisi ko powerbank chahiye tha kya",
    "aaj bahut garmi hai bhai",
    "barish ho rahi hai yaha to",
    "office se late nikla aaj",
    "naya show dekh raha hu netflix pe, mast hai",
    "kal se metro fare badh gaya",
]

FORWARDED = [
    "*Forwarded*\nGood morning 🙏 Have a blessed day ahead. Share with 10 people for good luck.",
    "*Forwarded*\nBreaking: Petrol prices to change from next week, check details.",
    "*Forwarded*\nHilarious joke: Teacher se student bola sir aap bhi kabhi fail hue the? Teacher bola nahi, main bhi engineer nahi bana.",
    "*Forwarded*\nHealth tip: Drink warm water every morning for better digestion.",
    "*Forwarded*\nThis message was forwarded many times. Independence day quotes and wishes for the nation.",
    "*Forwarded*\nDiwali sale offers live now on all major apps, check karo.",
    "*Forwarded*\nMotivational quote: Success is not final, failure is not fatal.",
    "*Forwarded*\nWeather alert for the region, heavy rainfall expected this week.",
]

REACTIONS = ["😂😂😂", "lolll", "same energy", "true that", "bilkul sahi baat",
             "arre wah", "kya baat hai", "nice nice", "👏👏", "mood"]

# ---------------------------------------------------------------------------
# Thread 1: Manali trip decision (spans ~April, resurfaces in June for booking)
# Deliberately designed so several eval queries have NO word overlap with the
# answer message.
# ---------------------------------------------------------------------------
THREAD_MANALI = [
    ("Rohan", "guys hume kahin trip plan karna chahiye is summer"),
    ("Sneha", "haanji bahut time se soch rahe the"),
    ("Aman", "Goa chalein?"),
    ("Neha", "Goa mein garmi bahut hogi is season mein"),
    ("Vikram", "hill station chalte hain, thanda rahega"),
    ("Priya", "Manali ya Kasol dono acche options hai"),
    ("Karan", "Manali better hai, stay options bhi zyada hai"),
    ("Ishaan", "budget kitna rakhna hai per person"),
    ("Priya", "10-12k per head reasonable rahega travel + stay ke saath"),
    ("Rohan", "sabko manali theek hai?"),
    ("Sneha", "haan mujhe theek hai"),
    ("Aman", "chalo fir, mujhe bhi thik hai"),
    ("Vikram", "ek kaam karte hain, poll bana lete hain"),
    ("Neha", "poll ki zarurat nahi, sab haan bol rahe hai"),
    ("Karan", "toh final?"),
    ("Rohan", "chalo Manali fix hai bhai, isi pe lock karte hain"),
    ("Ishaan", "great, dates decide karte hain ab"),
    ("Priya", "June ka last week best rahega sabke liye"),
    ("Sneha", "haan mujhe June mein leave milegi easily"),
    ("Karan", "ok toh 22-27 June rakh lete hain"),
]

THREAD_MANALI_BOOKING = [
    ("Rohan", "guys bus tickets book karne ka time aa gaya hai"),
    ("Priya", "haan wait mat karo, prices badh jayenge"),
    ("Vikram", "maine Volvo dekha hai, 1800 per seat"),
    ("Aman", "book kar do fir, sabke naam bhej raha hu"),
    ("Neha", "hotel bhi book kar lo saath mein"),
    ("Ishaan", "maine ek homestay dekha hai Old Manali mein, views mast hai"),
    ("Karan", "wahi book karte hain"),
    ("Sneha", "advance kitna dena hai"),
    ("Ishaan", "2000 advance per room"),
    ("Rohan", "sabne paise bhej diye group fund mein"),
    ("Priya", "confirm ho gayi booking, PDF bhej raha hu"),
    ("Vikram", "yesss finally"),
    ("Aman", "ab bas counting days"),
]

# ---------------------------------------------------------------------------
# Thread 2: Diwali party budget decision (August) — includes Priya-specific
# statements for "attributed" queries.
# ---------------------------------------------------------------------------
THREAD_DIWALI = [
    ("Neha", "Diwali party is baar hum log karte hain na office gang ke saath"),
    ("Karan", "haan bilkul, venue decide karna hai"),
    ("Priya", "rooftop wala jo pichli baar tha wo dobara book kar lete hain"),
    ("Rohan", "cost kitna aayega roughly"),
    ("Priya", "pichli baar 45k mein sab ho gaya tha, is baar inflation ki wajah se 55k tak jaa sakta hai"),
    ("Ishaan", "itna zyada? kam nahi kar sakte"),
    ("Priya", "decoration aur catering dono mein cut kar sakte hain, main negotiate karungi vendor se"),
    ("Sneha", "haan Priya tum handle kar lo budget wala part"),
    ("Priya", "theek hai, main final number 40k tak le aaungi, trust me"),
    ("Vikram", "per head kitna aayega tab"),
    ("Priya", "8 log split kare toh 5k per head, manageable hai"),
    ("Karan", "sounds good, chalo isi pe finalize karte hain"),
    ("Neha", "date kya rakhe"),
    ("Aman", "Diwali se ek din pehle rakhte hain, sabko free milega"),
    ("Rohan", "confirm, us din hi book karte hain venue"),
]

# ---------------------------------------------------------------------------
# Thread 3: Weekend trek / restaurant decision (May) — smaller thread, also
# used for a temporal "what did we discuss in May" query.
# ---------------------------------------------------------------------------
THREAD_TREK = [
    ("Vikram", "iss weekend trek pe chalein kya, bahut din ho gaye"),
    ("Karan", "kaunsa trek dekha hai"),
    ("Vikram", "Kalsubai ya Rajmachi, dono easy hai"),
    ("Ishaan", "Rajmachi better hai for beginners"),
    ("Neha", "mujhe height se dar lagta hai thoda"),
    ("Vikram", "Rajmachi mein aisa kuch nahi hai, chill trek hai"),
    ("Aman", "sunday early morning nikalte hain fir"),
    ("Priya", "main nahi aa paungi is weekend, ghar jana hai"),
    ("Rohan", "koi baat nahi, agli baar sahi"),
    ("Karan", "toh final, Rajmachi it is, sunday 5am departure"),
    ("Sneha", "wapas aake khana kaha khayenge"),
    ("Neha", "wapasi mein ghat ke us dhaba pe rukte hain, wahi bhutta acha milta hai"),
    ("Aman", "haanji wahi plan rakhte hain"),
]

DECISION_THREADS = [THREAD_MANALI, THREAD_MANALI_BOOKING, THREAD_DIWALI, THREAD_TREK]

# ---------------------------------------------------------------------------
# Message generation
# ---------------------------------------------------------------------------

def random_time_on_day(day):
    hours = list(range(7, 24))
    weights = [1,2,3,4,5,4,3,5,6,7,8,7,6,8,9,8,5,3,2][:len(hours)]
    while len(weights) < len(hours):
        weights.append(2)
    hour = random.choices(population=hours, weights=weights, k=1)[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return day.replace(hour=hour, minute=minute, second=second)


def build_messages():
    messages = []
    msg_id_counter = [0]

    def add(sender, text, ts, reply_to=None, thread_tag=None):
        msg_id_counter[0] += 1
        mid = f"m{msg_id_counter[0]:05d}"
        messages.append({
            "id": mid,
            "sender": sender,
            "text": text,
            "timestamp": ts.isoformat(),
            "reply_to": reply_to,
            "thread_tag": thread_tag,  # explicit tag for known decision threads; None for noise
        })
        return mid

    # Place the 4 decision threads at fixed points in the timeline.
    thread_anchor_days = {
        "manali": 40,          # mid April
        "manali_booking": 95,  # mid June
        "diwali": 175,         # late August
        "trek": 65,            # late April / May
    }

    def emit_thread(thread, anchor_day, tag):
        day = START_DATE + timedelta(days=anchor_day)
        t = random_time_on_day(day)
        last_id = None
        for sender, text in thread:
            t = t + timedelta(minutes=random.randint(1, 6))
            reply = last_id if random.random() < 0.3 else None
            last_id = add(sender, text, t, reply, thread_tag=tag)

    emit_thread(THREAD_MANALI, thread_anchor_days["manali"], "manali_decision")
    emit_thread(THREAD_TREK, thread_anchor_days["trek"], "trek_decision")
    emit_thread(THREAD_MANALI_BOOKING, thread_anchor_days["manali_booking"], "manali_booking")
    emit_thread(THREAD_DIWALI, thread_anchor_days["diwali"], "diwali_decision")

    # Fill the rest of the timeline with noise, ~ (4000 - len(decision msgs)) messages
    target_total = 4200
    remaining = target_total - len(messages)
    per_day_budget = remaining / TOTAL_DAYS

    for day_offset in range(TOTAL_DAYS + 1):
        day = START_DATE + timedelta(days=day_offset)
        # skip days already dense with a decision thread to keep it readable
        n_msgs = max(0, int(random.gauss(per_day_budget, per_day_budget * 0.6)))
        n_msgs = min(n_msgs, 45)
        last_id = None
        for _ in range(n_msgs):
            t = random_time_on_day(day)
            roll = random.random()
            if roll < 0.12:
                text = random.choice(GREETINGS)
            elif roll < 0.35:
                text = random.choice(ONE_WORD)
            elif roll < 0.42:
                text = random.choice(FORWARDED)
            elif roll < 0.55:
                text = random.choice(REACTIONS)
            else:
                text = random.choice(CHITCHAT)
            sender = random.choice(PARTICIPANTS)
            reply = last_id if random.random() < 0.15 else None
            last_id = add(sender, text, t, reply)

    messages.sort(key=lambda m: m["timestamp"])
    return messages


if __name__ == "__main__":
    msgs = build_messages()
    with open("data/corpus.json", "w", encoding="utf-8") as f:
        json.dump(msgs, f, ensure_ascii=False, indent=1)
    print(f"Generated {len(msgs)} messages from {msgs[0]['timestamp']} to {msgs[-1]['timestamp']}")
