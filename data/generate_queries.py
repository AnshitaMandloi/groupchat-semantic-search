"""
Builds queries.json: 40 test queries with ground-truth answer message_id,
resolved by matching a unique substring against the generated corpus (so the
ground truth is always exactly correct, never guessed).

query_type: semantic | attributed | temporal
no_overlap: True if query and answer message share zero content words
"""
import json
import re

with open("data/corpus.json", encoding="utf-8") as f:
    CORPUS = json.load(f)

STOP = {"the","a","an","is","are","was","were","did","do","does","we","you","i",
        "what","when","who","said","say","says","about","on","in","last","month",
        "did","we","our","to","for","of","that","this"}


def find(substr, occurrence=0):
    """Return message id whose text contains substr (case-insensitive), nth match."""
    hits = [m for m in CORPUS if substr.lower() in m["text"].lower()]
    if not hits:
        raise ValueError(f"NOT FOUND: {substr!r}")
    return hits[occurrence]["id"]


def find_by_sender_and_substr(sender, substr):
    hits = [m for m in CORPUS if m["sender"] == sender and substr.lower() in m["text"].lower()]
    if not hits:
        raise ValueError(f"NOT FOUND for {sender}: {substr!r}")
    return hits[0]["id"]


def word_overlap(query, answer_text):
    def words(s):
        return set(re.findall(r"[a-zA-Z]+", s.lower())) - STOP
    return bool(words(query) & words(answer_text))


queries = []

def q(text, answer_id, qtype, note=""):
    ans_text = next(m["text"] for m in CORPUS if m["id"] == answer_id)
    overlap = word_overlap(text, ans_text)
    queries.append({
        "query": text,
        "answer_message_id": answer_id,
        "query_type": qtype,
        "no_word_overlap": not overlap,
        "note": note,
    })

# ---------------------------------------------------------------------------
# SEMANTIC queries (meaning-based; several deliberately share NO words with answer)
# ---------------------------------------------------------------------------
q("when did we decide on Manali", find("Manali fix hai"), "semantic",
  "classic paraphrase case - 'decide' never appears in answer")
q("what's our final vacation spot", find("Manali fix hai"), "semantic",
  "no overlap: 'vacation'/'spot' vs 'Manali fix hai'")
q("did we ever finalize the trip destination", find("Manali fix hai"), "semantic",
  "no overlap: 'finalize'/'destination'/'trip' absent from answer")
q("who suggested we go to a cold place instead of the beach",
  find("hill station chalte hain"), "semantic",
  "no overlap: 'cold place'/'beach' vs 'hill station chalte hain'")
q("what dates did we lock for the Manali trip", find("22-27 June"), "semantic")
q("has the trip booking been confirmed", find("Confirm ho gayi booking", 0) if False else find("confirm ho gayi booking"), "semantic")
q("where are we staying in Manali", find("Old Manali"), "semantic",
  "no overlap: 'staying' vs 'homestay ... Old Manali'")
q("what's the plan for Diwali this year", find("Diwali party is baar"), "semantic")
q("how much will the Diwali celebration cost each person",
  find("5k per head"), "semantic",
  "no overlap: 'celebration'/'cost'/'each person' vs '5k per head'")
q("which trek did we finally pick", find("Rajmachi it is"), "semantic")
q("was anyone scared to go on the trek", find("dar lagta hai"), "semantic",
  "no overlap: 'scared' vs 'dar lagta hai'")
q("where did we eat after the trek", find("dhaba pe rukte hain"), "semantic",
  "no overlap: 'eat'/'after' vs 'dhaba pe rukte hain'")
q("did someone's laptop stop working", find("laptop crash ho gaya"), "semantic",
  "no overlap: 'stop working' vs 'crash ho gaya'")
q("who quit their job", find("resignation de diya"), "semantic",
  "no overlap: 'quit'/'job' vs 'resignation de diya'")
q("is anyone starting a new fitness routine", find("gym chalu kiya"), "semantic")
q("what mode of transport are we taking to Manali", find("Volvo dekha hai"), "semantic")

# ---------------------------------------------------------------------------
# ATTRIBUTED queries ("what did X say about Y")
# ---------------------------------------------------------------------------
q("what did Priya say about the budget",
  find_by_sender_and_substr("Priya", "45k mein sab ho gaya"), "attributed")
q("what did Priya say about the Manali budget",
  find_by_sender_and_substr("Priya", "10-12k per head"), "attributed")
q("what did Vikram suggest for the weekend",
  find_by_sender_and_substr("Vikram", "trek pe chalein"), "attributed")
q("what did Ishaan say about the homestay",
  find_by_sender_and_substr("Ishaan", "Old Manali"), "attributed")
q("did Priya agree to come on the trek",
  find_by_sender_and_substr("Priya", "nahi aa paungi"), "attributed",
  "no overlap: 'agree' vs 'nahi aa paungi' (she declines)")
q("what did Karan finalize about the trek plan",
  find_by_sender_and_substr("Karan", "Rajmachi it is"), "attributed")
q("what did Sneha say about her leave",
  find_by_sender_and_substr("Sneha", "leave milegi"), "attributed")
q("what did Rohan say about booking the bus tickets",
  find_by_sender_and_substr("Rohan", "bus tickets book"), "attributed")
q("what did Neha say about the trek being scary",
  find_by_sender_and_substr("Neha", "dar lagta hai"), "attributed")
q("what did Priya promise about lowering the party cost",
  find_by_sender_and_substr("Priya", "40k tak le aaungi"), "attributed",
  "no overlap: 'promise'/'lowering' vs 'main final number 40k tak le aaungi'")

# ---------------------------------------------------------------------------
# TEMPORAL queries (date/range filtering)
# ---------------------------------------------------------------------------
q("what did we discuss in April about a trip",
  find("Manali fix hai"), "temporal")
q("what plans were made in May", find("Rajmachi it is"), "temporal")
q("what happened with the trip booking in June",
  find("confirm ho gayi booking"), "temporal")
q("what was decided in August about Diwali",
  find("40k tak le aaungi"), "temporal")
q("what did the group talk about right after the trip was booked",
  find("finally"), "temporal")
q("what was discussed the week the Manali trip was finalized",
  find("dates decide karte hain"), "temporal")
q("what happened around the time everyone paid into the group fund",
  find("paise bhej diye"), "temporal")
q("what came up in the chat before the Diwali party venue was chosen",
  find("Diwali party is baar"), "temporal")

# ---------------------------------------------------------------------------
# Extra semantic/mixed queries to round out to 40
# ---------------------------------------------------------------------------
q("did anyone complain about traffic", find("Traffic bahut zyada"), "semantic")
q("did someone say the wifi was not working", find("wifi phir se down"), "semantic",
  "no overlap: 'not working' vs 'phir se down'")
q("who mentioned buying a new phone", find("naya phone liya"), "semantic")
q("is there any weather update forward in the chat",
  find("Weather alert"), "semantic")
q("what health advice was forwarded in the group",
  find("Drink warm water"), "semantic",
  "no overlap: 'health advice' vs 'Drink warm water every morning'")
q("who is planning to diet", find("diet start karunga"), "semantic")
q("what venue did we pick for Diwali", find("rooftop wala"), "semantic")

print(f"Total queries: {len(queries)}")
n_no_overlap = sum(1 for x in queries if x["no_word_overlap"])
print(f"No-word-overlap queries: {n_no_overlap}")
by_type = {}
for x in queries:
    by_type[x["query_type"]] = by_type.get(x["query_type"], 0) + 1
print("By type:", by_type)

with open("data/queries.json", "w", encoding="utf-8") as f:
    json.dump(queries, f, ensure_ascii=False, indent=1)
