"""
Builds the KubeRay RayService manifest fragment from validated contract fields.

The returned dict is applied to the cluster by the serving orchestrator.
owning_team is injected as a metadata label — this is the field the Grafana
consumption dashboard queries to attribute GPU cost per team.
"""


def build_rayservice_manifest(
    model_name: str, model_version: str, tags: dict
) -> dict:
    """
    Return a RayService manifest dict for the given validated contract.
    All 11 contract fields must be present; callers must run validation first.
    """
    tp = int(tags["tensor_parallel_degree"])

    return {
        "apiVersion": "ray.io/v1",
        "kind": "RayService",
        "metadata": {
            "name": _k8s_name(model_name),
            "labels": {
                # Attribution: owning_team propagated to every metric label so
                # Grafana can break down GPU cost without any join.
                "owning_team": tags["owning_team"],
                "model_name": model_name,
                "model_version": model_version,
                "runtime": tags["runtime"],
            },
        },
        "spec": {
            "serveConfigV2": {
                "applications": [
                    {
                        "name": _k8s_name(model_name),
                        "route_prefix": f"/{_k8s_name(model_name)}",
                        "import_path": "vllm_deployment:deployment",
                        "runtime_env": {
                            "env_vars": {
                                "MODEL_NAME": model_name,
                                "RUNTIME": tags["runtime"],
                                "RUNTIME_VERSION": tags["runtime_version"],
                                "QUANTIZATION": tags["quantization_precision"],
                                "MAX_CONTEXT": tags["max_context"],
                                "EVALUATED_CONCURRENCY": tags["evaluated_concurrency"],
                                "ARTIFACT_DIGEST": tags["artifact_digest"],
                                "TOKENIZER": tags["preprocessing_tokenizer"],
                            }
                        },
                        "deployments": [
                            {
                                "name": "VLLMDeployment",
                                "num_replicas": 1,
                                "ray_actor_options": {
                                    "num_gpus": tp,
                                    "resources": {
                                        tags["accelerator"]: tp,
                                    },
                                },
                            }
                        ],
                    }
                ]
            }
        },
    }


def _k8s_name(name: str) -> str:
    """Normalise a model name to a valid Kubernetes resource name."""
    return name.lower().replace("/", "-").replace("_", "-").replace(".", "-")
