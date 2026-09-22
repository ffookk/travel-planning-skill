PYTHON ?= python3
PLUGIN_DIR ?= plugins/travel-planning
PACKAGE_OUTPUT ?= output/travel-planning-marketplace.zip
BUNDLE_NAME ?= travel-planning-marketplace

.PHONY: frontend package
frontend:
	cd plugins/travel-planning/web && npm ci && npm run build

package:
	$(PYTHON) scripts/package_plugin.py \
		--plugin-dir "$(PLUGIN_DIR)" \
		--output "$(PACKAGE_OUTPUT)" \
		--bundle-name "$(BUNDLE_NAME)"
