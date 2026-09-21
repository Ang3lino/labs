import json
import sys

# The eleven contract fields defined in INF-05
REQUIRED_FIELDS = [
    "runtime",
    "runtime_version",
    "quantization_precision",
    "tensor_parallel_degree",
    "accelerator",
    "max_context",
    "evaluated_concurrency",
    "preprocessing_tokenizer",
    "resource_profile",
    "artifact_digest",
    "owning_team"
]

MAX_TP_DEGREE = 2
VALID_PROMOTION_STATES = {"Production", "Promoted"}

def validate_model_contract(model_data):
    model_name = model_data.get("model_name", "Unknown")
    print(f"\n--- Validating Model: {model_name} ---")

    # 1. Promotion state gates deployment
    promotion_state = model_data.get("promotion_state", "")
    if not promotion_state:
        print(f"❌ REJECTED: Model '{model_name}' has no promotion_state. Cannot deploy an artifact without a known promotion state.")
        return False
    if promotion_state not in VALID_PROMOTION_STATES:
        print(f"❌ REJECTED: Model '{model_name}' is not promoted. Current state: '{promotion_state}'. Must be one of {sorted(VALID_PROMOTION_STATES)}.")
        return False

    tags = model_data.get("tags", {})

    # 2. Refuse artifacts that do not carry all 11 contract fields
    for field in REQUIRED_FIELDS:
        if field not in tags or not tags[field]:
            print(f"❌ REJECTED: Missing required contract field: '{field}'. Deployment attempt fails without falling back to a default.")
            return False

    # 3. Reject tensor-parallel degree above 2
    try:
        tp_degree = int(tags.get("tensor_parallel_degree", 1))
        if tp_degree < 1:
            print(f"❌ REJECTED: 'tensor_parallel_degree' must be at least 1, got {tp_degree}.")
            return False
        if tp_degree > MAX_TP_DEGREE:
            print(f"❌ REJECTED: Declared tensor-parallel degree is {tp_degree}. This exceeds the fleet ceiling of {MAX_TP_DEGREE} (due to L40S PCIe constraints).")
            return False
    except ValueError:
        print("❌ REJECTED: 'tensor_parallel_degree' must be an integer.")
        return False

    # 4. Success - propagate attribution
    owning_team = tags.get("owning_team")
    print(f"✅ ACCEPTED: Contract validation passed for '{model_name}'.")
    print(f"🔧 ACTION: Generating RayService manifest...")
    print(f"   -> Injecting metric label: 'owning_team: {owning_team}' to ensure consumption dashboard attribution.")
    
    return True

if __name__ == "__main__":
    try:
        with open("test-payloads.json", "r") as f:
            payloads = json.load(f)
    except FileNotFoundError:
        print("Error: test-payloads.json not found.")
        sys.exit(1)

    for key, model_data in payloads.items():
        validate_model_contract(model_data)
