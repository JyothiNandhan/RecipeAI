from rag import retrieve_recipes
from models import RecipeRequest
class DummyTrace:
    def __init__(self):
        self.data = {}
    def update(self, key, val):
        self.data[key] = val

req = RecipeRequest(mode="ingredients", ingredients=["chicken", "rice"], navigator_token="dummy")
trace = DummyTrace()
res = retrieve_recipes(req, n_results=10, trace=trace)
print(f"Kept: {len(res)}")
for f in trace.data.get("vector_db", {}).get("filtered_out", []):
    print(f)
