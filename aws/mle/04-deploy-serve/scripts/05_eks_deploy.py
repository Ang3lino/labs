from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deploy fraud model manifests to EKS and run a smoke test")
    parser.add_argument("--k8s-dir", default="aws/mle/04-deploy-serve/k8s", help="Directory containing manifests")
    parser.add_argument("--deployment-name", default="fraud-model", help="Kubernetes deployment name")
    parser.add_argument("--service-name", default="fraud-model", help="Kubernetes service name")
    parser.add_argument("--namespace", default="default", help="Kubernetes namespace")
    return parser


def _kubectl(command: list[str]) -> str:
    completed = subprocess.run(["kubectl", *command], check=True, text=True, capture_output=True)
    return completed.stdout.strip()


def main() -> int:
    args = _build_parser().parse_args()
    k8s_path = Path(args.k8s_dir)

    for file_name in ("deployment.yaml", "service.yaml", "hpa.yaml"):
        _kubectl(["apply", "-f", str(k8s_path / file_name), "-n", args.namespace])

    _kubectl(["rollout", "status", f"deployment/{args.deployment_name}", "-n", args.namespace, "--timeout=300s"])

    endpoint_ip = ""
    for _ in range(30):
        output = _kubectl(["get", "svc", args.service_name, "-n", args.namespace, "-o", "json"])
        data = json.loads(output)
        ingress = data.get("status", {}).get("loadBalancer", {}).get("ingress", [])
        if ingress:
            endpoint_ip = ingress[0].get("ip") or ingress[0].get("hostname", "")
            if endpoint_ip:
                break
        time.sleep(10)

    if not endpoint_ip:
        raise RuntimeError("Service external IP/hostname not available yet")

    request_body = json.dumps({"features": {**{f"V{i}": 0.0 for i in range(1, 31)}, "Amount": 0.0}}).encode("utf-8")
    request = urllib.request.Request(
        url=f"http://{endpoint_ip}/invocations",
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            print("EKS test response:", response.read().decode("utf-8"))
    except urllib.error.URLError as error:
        print(f"EKS test request failed: {error}")
        raise

    print(f"Service endpoint: http://{endpoint_ip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
