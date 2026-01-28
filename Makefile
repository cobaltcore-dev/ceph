# --- Ceph container build for Rook (CobaltCore) ---

REGISTRY        ?= ghcr.io/cobaltcore-dev
IMAGE_NAME      ?= ceph
# upstream v19.2.3 + CobaltCore build 1
IMAGE_TAG       ?= v19.2.3-cc1

# This is the Ceph/container build script described in ContainerBuild.md
# In recent Ceph it is build-with-container.py; if the CLI differs in your branch,
# just adjust the command here.
CEPH_CONTAINER_BUILD ?= ./src/script/build-with-container.py

.PHONY: ceph-image-build
ceph-image-build:
	$(CEPH_CONTAINER_BUILD) \
	  --image-repo $(REGISTRY)/$(IMAGE_NAME) \
	  --tag $(IMAGE_TAG)

.PHONY: ceph-image-push
ceph-image-push: ceph-image-build
	docker push $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "Pushed $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)"

