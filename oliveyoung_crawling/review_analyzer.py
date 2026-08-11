import pandas as pd
from sentiment_dict import POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS

def analyze_sentiment(text):
    text = text.lower()
    pos = [k for k in POSITIVE_KEYWORDS if k in text]
    neg = [k for k in NEGATIVE_KEYWORDS if k in text]

    if len(pos) > len(neg):
        sentiment = "positive"
    elif len(neg) > len(pos):
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return sentiment, pos, neg


df = pd.read_csv("data/reviews.csv")

df["sentiment"], df["positive_keywords"], df["negative_keywords"] = zip(
    *df["review"].apply(analyze_sentiment)
)

df.to_csv("data/review_analysis.csv", index=False)
