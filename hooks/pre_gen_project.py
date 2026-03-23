def validate(name: str, raw: str, allowed: set[str]) -> set[str]:
    selected = {x.strip().lower() for x in raw.split(",") if x.strip()}
    invalid = selected - allowed
    if invalid:
        print(f"ERROR: invalid {name}: {', '.join(sorted(invalid))}")
        print(f"Allowed values: {', '.join(sorted(allowed))}")
        raise SystemExit(1)
    return selected


def parse_pairs(name: str, raw: str) -> list[tuple[str, str]]:
    pairs = []
    for item in (x.strip().lower() for x in raw.split(",") if x.strip()):
        if ":" not in item:
            raise SystemExit(
                f"ERROR: {name} must be 'role:commodity' pairs, got: {item}"
            )
        r, c = (p.strip() for p in item.split(":", 1))
        pairs.append((r, c))
    return pairs


# ================= Definitions =======================
CONTROL_TYPES = {"pebc", "ombc", "ppbc", "frbc", "ddbc", "none"}
MEASUREMENTS = {"l1", "l2", "l3", "3phase", "temperature", "heat_flow_rate"}
ROLES = {"producer", "consumer", "storage"}
COMMODITIES = {"electricity", "heat", "gas", "oil"}


# ================= Validation ==========================
validate("control type", "{{ cookiecutter.available_control_types }}", CONTROL_TYPES)
validate("measurement", "{{ cookiecutter.measurement }}", MEASUREMENTS)

pairs = parse_pairs("roles", "{{ cookiecutter.device_role }}")
bad_roles = {r for r, _ in pairs} - ROLES
bad_comms = {c for _, c in pairs} - COMMODITIES
if bad_roles or bad_comms:
    if bad_roles:
        print(f"ERROR: invalid roles: {', '.join(sorted(bad_roles))}")
        print(f"Allowed roles: {', '.join(sorted(ROLES))}")
    if bad_comms:
        print(f"ERROR: invalid commodities: {', '.join(sorted(bad_comms))}")
        print(f"Allowed commodities: {', '.join(sorted(COMMODITIES))}")
    raise SystemExit(1)

if not pairs:
    raise SystemExit("ERROR: roles must not be empty (e.g. 'producer:electricity').")
