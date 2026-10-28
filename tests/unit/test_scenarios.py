"""Scenario parsing: which rule title each scenario asserts."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import scenarios  # noqa: E402


def write(tmp_path, body):
    path = tmp_path / "x.threatest.yaml"
    path.write_text(body)
    return path


def test_signal_names_reads_each_matchers_title_key(tmp_path):
    path = write(tmp_path, """
scenarios:
  - name: datadog
    detonate: {localDetonator: {commands: [true]}}
    expectations:
      - datadogSecuritySignal: {name: Rule A}
  - name: thehive
    detonate: {localDetonator: {commands: [true]}}
    expectations:
      - theHiveAlert: {title: Rule B, source: splunk, correlation: host}
""")
    assert scenarios.signal_names(path) == {"datadog": "Rule A", "thehive": "Rule B"}


def test_signal_names_ignores_telemetry_and_discovery(tmp_path):
    path = write(tmp_path, """
scenarios:
  - name: telemetry only
    detonate: {localDetonator: {commands: [true]}}
    expectations:
      - splunkLog: {query: index=main}
      - theHiveAlert: {title: Rule C}
        discover: true
""")
    assert scenarios.signal_names(path) == {}


def test_shipped_network_scenarios_assert_existing_titles():
    names = scenarios.signal_names(ROOT / "scenarios" / "network.threatest.yaml")
    assert names == {"DNS tunneling detected from egress host": "DNS Tunneling via High Volume Unique Subdomains"}
