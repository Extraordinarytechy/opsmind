.PHONY: test demo lint cluster deploy failure clean

test:
	python3 -m unittest discover -s tests -v

demo:
	python3 -m opsmind.cli examples/sample_alert.json

lint:
	python3 -m pyflakes opsmind || true

# --- Local Kubernetes (kind) ---
cluster:
	kind create cluster --config deploy/kind-cluster.yaml

deploy:
	kubectl apply -f deploy/app/namespace.yaml
	kubectl apply -f deploy/app/
	kubectl apply -f deploy/monitoring/

failure:
	bash scripts/inject_failure.sh error 0.6

clean:
	kind delete cluster --name opsmind
