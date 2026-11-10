"""Limited, inspectable prohibited-claim rules, not semantic entailment."""

import re

PHRASES = (
    "any erp",
    "every erp",
    "har erp",
    "हर ईआरपी",
    "unlimited",
    "guaranteed",
    "guarantee",
    "every partner can see",
)


def unsupported_claims(text: str) -> list[str]:
    flagged = []
    for clause in re.split(r"[.!?;\n।]+", text.casefold()):
        for phrase in PHRASES:
            position = clause.find(phrase)
            if position < 0:
                continue
            prefix = clause[:position]
            # Recognise only common explicit denials; unfamiliar constructions still need review.
            negated = (
                bool(
                    re.search(
                        r"\b(no|not|never|cannot|can't|don't|isn't|aren't|wasn't|won't|avoid|without)\b",
                        prefix,
                    )
                )
                or "नहीं" in prefix
            )
            suffix = clause[position + len(phrase) :]
            negated = negated or bool(re.match(r"\s+(nahi|nahin|नहीं)(?:\s|$)", suffix))
            if not negated:
                flagged.append(phrase)
    return list(dict.fromkeys(flagged))
