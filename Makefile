.PHONY: install validate test coverage detonate all clean

install:
	pip install -r tools/requirements.txt

validate:
	python tools/validate_rules.py

test:
	pytest tests/unit -q

coverage:
	python tools/coverage_report.py

# Local detonation. Requires threatest on PATH, flightsim on the detonation
# host, and DETONATION_HOST set to an approved host. Read
# docs/testing-strategy.md before running this anywhere that is not a lab.
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
