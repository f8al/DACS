.PHONY: install validate test coverage detonate all clean

install:
	pip install -r tools/requirements.txt

validate:
	python tools/validate_rules.py

test:
	pytest tests/unit -q

coverage:
	python tools/coverage_report.py

# Local detonation. Requires the f8al/threatest fork build on PATH, from
# https://github.com/f8al/threatest/releases (upstream Threatest cannot parse
# the splunkLog and theHiveAlert keys), flightsim on the detonation host, and
# in the environment:
#   DETONATION_HOST, DETONATION_USER    an approved detonation host
#   THEHIVE_DETONATION_HOSTS            its addresses, for host correlation
#   SPLUNK_URL, SPLUNK_TOKEN            splunkLog
#   THEHIVE_URL, THEHIVE_API_KEY        theHiveAlert
#   SPLUNK_CA_CERT, THEHIVE_CA_CERT     only with a private CA
# Read docs/testing-strategy.md before running this anywhere that is not a lab.
detonate:
	mkdir -p build/threatest
	for f in $$(python tools/scenarios.py active); do \
		threatest lint $$f && \
		threatest run $$f --output build/threatest/$$(basename $$f .threatest.yaml).json || exit 1; \
	done
	python tools/detonate_flightsim.py

all: validate test coverage

clean:
	rm -rf build .pytest_cache
