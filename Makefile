
IMAGE=inosion/auto-telemetry

.PHONY: $(IMAGE)
$(IMAGE):
	docker build -t $(IMAGE) -f Dockerfile.obd2 .

.PHONY: all
all: $(IMAGE)
