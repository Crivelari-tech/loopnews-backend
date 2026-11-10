# Read-only DB probe for text quality (entities, footers, null summaries, empty titles, 'O post' false-positives)
import sys
sys.path.insert(0, "/app/backend")
from dotenv import dotenv_values
from pymongo import MongoClient

env = dotenv_values("/app/backend/.env")
db = MongoClient(env["MONGO_URL"])[env["DB_NAME"]]
ent = "&quot;|&amp;|&#[0-9]|&gt;|&lt;|&nbsp;"
print("total news", db.news.estimated_document_count())
print("title entities", db.news.count_documents({"title": {"$regex": ent}}))
print("summary entities", db.news.count_documents({"summary": {"$regex": ent}}))
print("ai_summary entities", db.news.count_documents({"ai_summary": {"$regex": ent}}))
print("apareceu primeiro (summary)", db.news.count_documents({"summary": {"$regex": "apareceu primeiro"}}))
print("apareceu primeiro (ai_summary)", db.news.count_documents({"ai_summary": {"$regex": "apareceu primeiro"}}))
print("summary literal null", db.news.count_documents({"summary": {"$in": ["null", "None", "undefined"]}}))
print("empty title", db.news.count_documents({"$or": [{"title": ""}, {"title": None}]}))
print("empty summary", db.news.count_documents({"summary": ""}))
print("trailing &#", db.news.count_documents({"summary": {"$regex": "&#?[a-zA-Z0-9]{0,8}$"}}))
print("titles with 'O post '", [d["title"] for d in db.news.find({"title": {"$regex": "O post "}}, {"title": 1}).limit(5)])
print("summaries with 'O post ' (non-footer)", [d["summary"][-120:] for d in db.news.find({"summary": {"$regex": "O post (?!.*apareceu)"}}, {"summary": 1}).limit(3)])

from server import clean_news_text
samples = [
    "O post de Virginia no Instagram gerou polêmica entre fãs",
    "Tom &amp; Jerry voltam &quot;remasterizados&quot; &#8211; veja",
    "Novo game chega em março. O post Novo game apareceu primeiro em Flow Games.",
    "Ações da AT&T sobem",
    "Será que vem aí...",
    "Resumo cortado no meio &#82",
]
for s in samples:
    print(repr(s), "->", repr(clean_news_text(s)))
