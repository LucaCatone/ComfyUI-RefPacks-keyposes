"""Shared RefPack container, metadata and reference grouping."""
import math
import torch

FORMAT = "bexplains.refpack"
VERSION = 1
ROLES = ("subject", "character", "item", "video", "motion", "keyposes", "outfit", "location", "reference", "audio", "style")
SUBJECT_ROLES = ("subject", "character", "item")


def validate_tensor(z, label="latent"):
    if not isinstance(z, torch.Tensor) or z.is_nested or z.ndim not in (4, 5):
        raise ValueError(f"{label} must be a plain 4D or 5D tensor.")
    if min(z.shape) < 1 or not z.is_floating_point() or not torch.isfinite(z).all():
        raise ValueError(f"{label} must have positive dimensions and finite floating-point values.")
    return z


def validate_pack(pack, require_vision=True):
    if not isinstance(pack, dict) or pack.get("format") != FORMAT or pack.get("version") != VERSION:
        raise ValueError("Not a supported BExplains RefPack.")
    if not isinstance(pack.get("target"), str) or not pack["target"].strip():
        raise ValueError("A RefPack must record its target model family.")
    entries = pack.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("A RefPack must contain at least one reference.")
    for e in entries:
        if e.get("kind") == "audio":
            validate_tensor(e.get("audio_latent"), "audio latent")
            continue
        if e.get("kind") not in ("image", "video"):
            raise ValueError("Unsupported reference kind.")
        z = validate_tensor(e.get("latent"))
        if z.shape[0] != 1:
            raise ValueError("Store one reference per entry; use separate entries for separate images.")
        v = e.get("vision")
        if require_vision and v is None:
            raise ValueError("This pack lacks reference pixels. Recreate it with the reference encoder.")
        if v is not None:
            if not isinstance(v, torch.Tensor) or v.ndim != 4 or v.shape[-1] != 3 or min(v.shape[:3]) < 1:
                raise ValueError("Vision data must be RGB frames [N,H,W,3].")
            if not v.is_floating_point() or not torch.isfinite(v).all() or v.min() < 0 or v.max() > 1:
                raise ValueError("Vision inputs must be finite floating-point RGB frames in [0,1].")
            if e["kind"] == "image" and v.shape[0] != 1:
                raise ValueError("Each image entry requires exactly one vision image.")
            if e["kind"] == "video":
                ts = e.get("timestamps", [])
                if len(ts) != v.shape[0] or any(not math.isfinite(float(t)) for t in ts):
                    raise ValueError("Each video vision frame needs a finite timestamp.")
                if any(float(b) < float(a) for a, b in zip(ts, ts[1:])):
                    raise ValueError("Video timestamps must be in chronological order.")
    return pack

def empty_set():
    return {"target": None, "groups": []}


def subject_numbers(references):
    """Stable subject IDs across generic subjects, characters and items.

    Legacy subject role IDs retain their meaning. New typed groups store a separate
    subject_id, while their role_id numbers Character/Item aliases independently.
    """
    groups = references.get("groups", [])
    numbers, used = {}, set()
    for gi, group in enumerate(groups):
        if group["role"] not in SUBJECT_ROLES:
            continue
        number = group.get("subject_id", group["role_id"] if group["role"] == "subject" else None)
        if number is None:
            continue
        if type(number) is not int or number < 1 or number in used:
            raise ValueError("Subject IDs must be positive and unique across subjects, characters and items.")
        if group["role"] == "subject" and number != group["role_id"]:
            raise ValueError("A generic Subject ID must match its role ID.")
        numbers[gi] = number
        used.add(number)
    for gi, group in enumerate(groups):
        if group["role"] in SUBJECT_ROLES and gi not in numbers:
            number = next(i for i in range(1, len(used) + 2) if i not in used)
            numbers[gi] = number
            used.add(number)
    return numbers


def add_pack(pack, references=None, role="subject", role_id=0):
    references = references or empty_set()
    if pack is None:  # disabled optional file loader
        return references
    validate_pack(pack)
    if role not in ROLES:
        raise ValueError("Unknown reference role.")
    if role in ("subject", "character", "item", "outfit", "location", "style") and any(e["kind"] != "image" for e in pack["entries"]):
        raise ValueError(f"A {role} pack must contain images, not a video.")
    if role in ("video", "motion") and any(e["kind"] != "video" for e in pack["entries"]):
        raise ValueError(f"The {role} role requires video references.")
    if role == "keyposes":
        if any(e["kind"] not in ("image", "video") for e in pack["entries"]):
            raise ValueError("The keyposes role requires image or video references.")
        if len({e["kind"] for e in pack["entries"]}) > 1:
            raise ValueError("A keyposes pack must hold either images or one video, not both.")
    if role == "audio" and any(e["kind"] != "audio" for e in pack["entries"]):
        raise ValueError("The audio role requires audio references.")
    subjects = set(subject_numbers(references).values())
    used = subjects if role == "subject" else {g["role_id"] for g in references["groups"] if g["role"] == role}
    if role_id == 0:
        role_id = next(i for i in range(1, len(used) + 2) if i not in used)
    if role_id < 1 or role_id in used:
        raise ValueError(f"Duplicate or invalid {role} ID {role_id}.")
    group = {"role": role, "role_id": role_id, "name": pack["name"], "entries": list(pack["entries"]),
             "source_target": pack.get("source_target", pack["target"]),
             "encoder_class": pack.get("encoder_class", "unspecified"),
             "source_file": pack.get("source_file"), "target": pack["target"]}
    if role in SUBJECT_ROLES:
        group["subject_id"] = role_id if role == "subject" else next(i for i in range(1, len(subjects) + 2) if i not in subjects)
    groups = list(references["groups"]) + [group]
    has_video = any(e["kind"] in ("video", "audio") for g in groups for e in g["entries"])
    families = {g.get("target", g["source_target"]) for g in groups}
    if all(t in ("h3", "h3_image", "h3_video") for t in families):
        family = "h3_video" if has_video else "h3"
    else:
        family = next(iter(families)) if len(families) == 1 else "mixed"
    return {"target": family, "groups": groups}



def validate_references(references):
    """Validate an assembled set without changing its group order or role IDs."""
    if not isinstance(references, dict) or not isinstance(references.get("groups"), list) or not references["groups"]:
        raise ValueError("Add at least one reference pack before saving a reference set.")
    seen = set()
    for group in references["groups"]:
        if not isinstance(group, dict) or not isinstance(group.get("name"), str):
            raise ValueError("Each reference group must have a name.")
        role, role_id = group.get("role"), group.get("role_id")
        if role not in ROLES:
            raise ValueError("Unknown reference role.")
        if type(role_id) is not int or role_id < 1 or (role, role_id) in seen:
            raise ValueError("Reference role IDs must be positive and unique within each role.")
        seen.add((role, role_id))
        target = group.get("target", group.get("source_target"))
        pack = {"format": FORMAT, "version": VERSION, "name": group["name"],
                "target": target, "entries": group.get("entries")}
        # Reuse normal pack/role checks, but never rebuild or renumber the saved set.
        add_pack(pack, role=role, role_id=role_id)
    subject_numbers(references)
    return references


def _copy_metadata(value):
    """Copy containers without duplicating potentially large cached tensors."""
    if isinstance(value, dict):
        return {key: _copy_metadata(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_copy_metadata(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_copy_metadata(item) for item in value)
    return value


def merge_bundles(bundles):
    """Append groups, retaining free IDs and remapping collisions in input order."""
    if len(bundles) < 2:
        raise ValueError("Connect at least two RefPack bundles to merge.")
    for bundle in bundles:
        validate_references(bundle)
    result = _copy_metadata(bundles[0])
    result["groups"] = []
    result["merged_from"] = [
        _copy_metadata({key: value for key, value in bundle.items() if key != "groups"})
        for bundle in bundles
    ]
    used_roles = {role: set() for role in ROLES}
    used_subjects = set()

    def available(preferred, used):
        if preferred not in used:
            return preferred
        return next(i for i in range(1, len(used) + 2) if i not in used)

    for bundle in bundles:
        subjects = subject_numbers(bundle)
        # Reserve IDs that can be retained, so an earlier collision cannot steal
        # a later group's otherwise unused ID within the same input bundle.
        reserved_subjects = set(subjects.values())
        reserved_roles = {
            role: {g["role_id"] for g in bundle["groups"] if g["role"] == role}
            for role in ROLES
        }
        for index, original in enumerate(bundle["groups"]):
            group = _copy_metadata(original)
            role = group["role"]
            if role in SUBJECT_ROLES:
                preferred = subjects[index]
                group["subject_id"] = (preferred if preferred not in used_subjects else
                    available(preferred, used_subjects | reserved_subjects))
                used_subjects.add(group["subject_id"])
            if role == "subject":
                group["role_id"] = group["subject_id"]
            elif group["role_id"] in used_roles[role]:
                group["role_id"] = available(group["role_id"], used_roles[role] | reserved_roles[role])
            used_roles[role].add(group["role_id"])
            result["groups"].append(group)
    families = {g.get("target", g.get("source_target")) for g in result["groups"]}
    if families <= {"h3", "h3_image", "h3_video"}:
        has_video = any(e["kind"] in ("video", "audio") for g in result["groups"] for e in g["entries"])
        result["target"] = "h3_video" if has_video else "h3"
    else:
        result["target"] = next(iter(families)) if len(families) == 1 else "mixed"
    return validate_references(result)
