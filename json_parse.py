import json
import flask

f = open("sample.txt", "r", encoding="utf-8")
json_str = f.read()
# print(json_str)

def parse_events_json(response):
