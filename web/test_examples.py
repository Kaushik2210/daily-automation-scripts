import pytest
from dashboard import discover
from run_examples import load_json, run_example

TOOLS = discover()
SAMPLES = load_json("samples.json")
EXAMPLES = load_json("examples.json")


def test_every_tool_has_an_example_and_no_example_is_stale():
    assert sorted(set(TOOLS) - set(EXAMPLES)) == [], "add these tools to web/examples.json"
    assert sorted(set(EXAMPLES) - set(TOOLS)) == [], "remove these from web/examples.json"


@pytest.mark.parametrize("tool_id", sorted(TOOLS))
def test_example_produces_results(tool_id):
    result = run_example(TOOLS[tool_id], EXAMPLES[tool_id], SAMPLES)
    assert result["ok"], f"{tool_id}: {result['detail']}\n{result['out']}"
