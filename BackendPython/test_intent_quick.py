#!/usr/bin/env python3
from app.core.intent_mapper import IntentMapper

m = IntentMapper()
r = m.map_intent('tôi muốn mua gì đó ngọt ngào cho bạn gái')
print(f"Intent: {r.get('intent')}")
print(f"Categories: {r.get('categories')}")
print(f"Method: {r.get('method')}")
print(f"Confidence: {r.get('confidence')}")
