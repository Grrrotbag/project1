import requests
res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "5hmm8TL0WdOEmWRajxg1w", "isbns": "9781632168146"})
print(res.json())