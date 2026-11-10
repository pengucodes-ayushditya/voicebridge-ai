from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, String

from .claims import unsupported_claims
from .store import Base, NotFound, Session, engine, lock

SCENARIOS = [
    {
        "id": "price",
        "name": "The price-sensitive buyer",
        "persona": "A small refurbishment operator watching costs.",
        "objective": "Discover budget and scope without inventing prices.",
        "questions": [
            "Our budget is tight. Why should we choose this?",
            "What would you include for our repair partners?",
            "Can you guarantee a price and unlimited monthly devices?",
        ],
    },
    {
        "id": "technical",
        "name": "The technical evaluator",
        "persona": "An operations lead validating integration and data access.",
        "objective": "Explain ERP prerequisites and preserve owner privacy.",
        "questions": [
            "Can you integrate with our legacy ERP?",
            "What API access do you need? Can every partner see owner details?",
            "What would you test before making a commitment?",
        ],
    },
    {
        "id": "skeptical",
        "name": "The skeptical buyer",
        "persona": "A buyer who was previously promised an integration that failed.",
        "objective": "Acknowledge concern and propose a scoped validation.",
        "questions": [
            "The last vendor overpromised. Why should I trust you?",
            "How do I know partner access will protect owner information?",
            "Can we validate compatibility before committing?",
        ],
    },
]


for existing in SCENARIOS:
    existing["domain_id"] = "synthetic-device-lifecycle"
SCENARIOS.extend(
    [
        {
            "id": "market-price",
            "domain_id": "marketplace",
            "name": "The value-conscious buyer",
            "persona": "A marketplace operator evaluating a small pilot.",
            "objective": "Discover scope and success criteria without inventing ROI or prices.",
            "questions": [
                "Why should we invest in recommendations for products with no history?",
                "What information would you need for a pilot?",
                "Can you guarantee higher conversions and a fixed price?",
            ],
        },
        {
            "id": "market-technical",
            "domain_id": "marketplace",
            "name": "The technical evaluator",
            "persona": "A marketplace product lead validating cold-start recommendations.",
            "objective": "Explain the candidate approach and clarify data and evaluation dependencies.",
            "questions": [
                "How can we recommend a new product without clicks or reviews?",
                "What if our catalogue images and metadata are incomplete?",
                "How will we decide whether recommendation relevance is good enough?",
            ],
        },
        {
            "id": "market-skeptical",
            "domain_id": "marketplace",
            "name": "The skeptical buyer",
            "persona": "A buyer whose previous recommendations pilot disappointed.",
            "objective": "Acknowledge concern and propose an evidence-based evaluation.",
            "questions": [
                "The previous vendor promised accuracy and failed. Why trust this approach?",
                "Can you promise every customer will see relevant new products?",
                "What should we review before committing to implementation?",
            ],
        },
    ]
)


class TrainingRecord(Base):
    __tablename__ = "training_sessions"
    id = Column(String, primary_key=True)
    payload = Column(JSON, nullable=False)


Base.metadata.create_all(engine)


class StartSession(BaseModel):
    scenario_id: str


class Turn(BaseModel):
    text: str = Field(min_length=1, max_length=3000)


def save(s):
    with Session.begin() as db:
        db.merge(TrainingRecord(id=s["id"], payload=s))


def get(sid):
    with Session() as db:
        r = db.get(TrainingRecord, sid)
        if not r:
            raise NotFound("Training session not found")
        return r.payload


def start(scenario_id):
    scenario = next((s for s in SCENARIOS if s["id"] == scenario_id), None)
    if not scenario:
        raise ValueError("Unknown scenario")
    s = {
        "id": str(uuid4()),
        "scenario": scenario,
        "domain_id": scenario.get("domain_id", "synthetic-device-lifecycle"),
        "turns": [],
        "question": scenario["questions"][0],
        "complete": False,
        "evaluation": None,
        "provider": "Scripted deterministic training fixture",
    }
    save(s)
    return s


def turn(sid, text):
    with lock:
        s = get(sid)
        if s["complete"]:
            raise ValueError("This session is complete. Start another scenario.")
        s["turns"].append({"customer": s["question"], "trainee": text})
        n = len(s["turns"])
        s["complete"] = n >= 3
        s["question"] = (
            s["scenario"]["questions"][n]
            if n < 3
            else "Session complete — review your coaching scorecard."
        )
        if s["complete"]:
            s["evaluation"] = evaluate(s)
        save(s)
        return s


def evaluate(s):
    turns = s["turns"]
    text = " ".join(t["trainee"] for t in turns).lower()
    claims = [t["trainee"] for t in turns if unsupported_claims(t["trainee"])]
    questions = sum("?" in t["trainee"] for t in turns)
    rubric = [
        (
            "Product accuracy",
            1 if claims else 3,
            "Unsupported claims lower this rule-based score.",
        ),
        (
            "Discovery quality",
            min(5, 1 + questions),
            "One point plus the number of turns containing a question.",
        ),
        (
            "Product placement",
            3
            if any(
                w in text
                for w in [
                    "qr",
                    "repair",
                    "lifecycle",
                    "erp",
                    "partner",
                    "product",
                    "catalogue",
                    "recommend",
                ]
            )
            else 1,
            "Checks for relevant documented capability terms.",
        ),
        (
            "Personalisation",
            3 if any(w in text for w in ["your", "aap", "budget", "legacy"]) else 1,
            "Checks for customer-context wording.",
        ),
        (
            "Objection handling",
            3
            if any(w in text for w in ["understand", "concern", "reasonable", "samajh"])
            else 1,
            "Checks for acknowledgement wording.",
        ),
        (
            "Clarity",
            3 if all(len(t["trainee"].split()) <= 100 for t in turns) else 2,
            "Checks length only, not actual clarity.",
        ),
        (
            "Honesty about limitations",
            4
            if any(
                w in text
                for w in ["depend", "compatib", "validate", "unknown", "not documented"]
            )
            else 1,
            "Checks explicit uncertainty/validation wording.",
        ),
        (
            "Avoiding unsupported claims",
            1 if claims else 4,
            "Checks a limited list of prohibited phrases.",
        ),
    ]
    return {
        "rubric": [
            {"category": a, "score": b, "out_of": 5, "rationale": c}
            for a, b, c in rubric
        ],
        "flagged_claims": claims,
        "examples": [
            {
                "quote": t["trainee"],
                "feedback": "Validate compatibility and avoid universal guarantees."
                if t["trainee"] in claims
                else (
                    "You asked a concrete discovery question. Tie the answer to an approved source and keep the documented conditions."
                    if "?" in t["trainee"]
                    else "Add a specific discovery question and cite an approved source."
                ),
                "alternative": marketplace_alternative(t["customer"])
                if s.get("domain_id") == "marketplace"
                else alternative(t["customer"]),
            }
            for t in turns
        ],
        "sources": ["kb-market-cold-start", "kb-market-relevance", "kb-market-playbook"]
        if s.get("domain_id") == "marketplace"
        else ["kb-erp", "kb-privacy", "kb-playbook"],
        "caveat": "Transparent keyword-based coaching on scripted synthetic scenarios. Not a validated assessment or employee-performance verdict.",
    }


def history():
    with Session() as db:
        return [
            {
                "id": row.id,
                "scenario": row.payload["scenario"]["name"],
                "domain_id": row.payload.get("domain_id", "synthetic-device-lifecycle"),
                "complete": row.payload["complete"],
                "turns": len(row.payload["turns"]),
            }
            for row in db.query(TrainingRecord).all()
        ]


def alternative(question):
    text = question.casefold()
    if any(w in text for w in ["price", "budget", "unlimited"]):
        return "Pricing and guaranteed capacity are not documented. What budget and monthly device volume should we validate with a product specialist?"
    if any(w in text for w in ["owner", "privacy", "partner"]):
        return "Partners should see assigned repair records only; owner personal details stay hidden. Which partner roles should we test with sample accounts?"
    if any(w in text for w in ["trust", "overpromis"]):
        return "Your concern is reasonable. Let us agree on a scoped validation, documented limitations and success criteria before making a commitment. What failed last time?"
    return "ERP support depends on API compatibility. Which vendor/version do you use, and can we validate access and a sandbox?"


def marketplace_alternative(question):
    text = question.casefold()
    if any(w in text for w in ["price", "conversions", "invest"]):
        return "Price and conversion uplift are not documented. What pilot scope and baseline would help you judge the value before a commitment?"
    if any(w in text for w in ["metadata", "images", "information"]):
        return "The approach depends on suitable catalogue metadata or images. Which fields and images are available for a newly listed product, and can we review a representative sample?"
    return "The cold-start approach uses available product information, but relevance must be evaluated. Which customer context, baseline and success criteria should we agree for a scoped pilot?"
