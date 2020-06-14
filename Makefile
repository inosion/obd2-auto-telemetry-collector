
IMAGE=inosion/auto-telemetry

.PHONY: $(IMAGE)
$(IMAGE):
	docker build -t $(IMAGE) -f Dockerfile.obd2 .

.PHONY: all
all: $(IMAGE)

prepare:
	mkdir -p data/grafana-storage
	sudo chown -R 472:472 data/grafana-storage