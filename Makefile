.PHONY: generate_client
generate_client:
	mvn clean install
	openapi-generator generate -i target/generated-sources/openapi/orchestrator-openapi.yml -g python -o python/generated

.PHONY: clean
clean:
	rm -rf python/generated
	rm -rf target
	rm -rf .openapi-generator
	pip uninstall openapi-client -y

.PHONY: install-requirements
install-requirements: generate_client
	# Make sure venv is activated
	pip install -r requirements.txt
	pip install -e .
