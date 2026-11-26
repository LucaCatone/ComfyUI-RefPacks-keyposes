"""Shared RefPack preparation, persistence and receiver nodes."""
import time
from pathlib import Path
import torch
import folder_paths
from .core import FORMAT, VERSION, ROLES, add_pack, validate_pack, merge_bundles
from .storage import load_pack, save_pack, load_references, save_references, REFERENCES_SUFFIX
from .diagnostics import log
CATEGORY = "BExplains/RefPacks"
PACK_TYPE = "BEXPLAINS_REFPACK"
SET_TYPE = "BEXPLAINS_REFERENCES"
ROOT = Path(folder_paths.models_dir) / "refpacks"
ROOT.mkdir(parents=True, exist_ok=True)
folder_paths.add_model_folder_path("bexplains_refpacks", str(ROOT))
REFERENCES_ROOT = ROOT / "references"
REFERENCES_ROOT.mkdir(parents=True, exist_ok=True)
folder_paths.add_model_folder_path("bexplains_refpacks_references", str(REFERENCES_ROOT))

def _path(name):
    if not name or Path(name).is_absolute():
        raise ValueError("Select a relative file name inside models/refpacks.")
    candidate = (ROOT / name).resolve()
    if not candidate.is_relative_to(ROOT.resolve()):
        raise ValueError("Reference paths must remain inside models/refpacks.")
    return candidate


def _files():
    return sorted({f for f in folder_paths.get_filename_list("bexplains_refpacks") if f.endswith(".safetensors") and not f.endswith(REFERENCES_SUFFIX)})


class BExplainsSaveRefPack:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"refpack": (PACK_TYPE,), "filename": ("STRING", {"default": "character", "tooltip": "RefPack name or relative path. The .safetensors extension is added automatically. Connect the same text to the encoder name and this input."}), "overwrite": ("BOOLEAN", {"default": False})}}
    RETURN_TYPES = (PACK_TYPE, "STRING")
    RETURN_NAMES = ("refpack", "filename")
    FUNCTION = "save"
    CATEGORY = CATEGORY
    OUTPUT_NODE = True
    DESCRIPTION = "Save a RefPack inside models/refpacks. The .safetensors extension is automatic; the same plain text can feed the encoder name and this filename. Existing filenames with the extension remain supported."

    def save(self, refpack, filename, overwrite):
        if not filename.endswith(".safetensors"):
            filename += ".safetensors"
        path = save_pack(refpack, _path(filename), overwrite)
        text = f"Saved {filename}: {len(refpack['entries'])} reference(s), {Path(path).stat().st_size:,} bytes."
        return {"ui": {"text": [text]}, "result": (refpack, filename)}


class BExplainsLoadRefPack:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"filename": (_files(),), "enabled": ("BOOLEAN", {"default": True})}}
    RETURN_TYPES = (PACK_TYPE,)
    RETURN_NAMES = ("refpack",)
    FUNCTION = "load"
    CATEGORY = CATEGORY

    def load(self, filename, enabled):
        if not enabled:
            return (None,)
        started = time.perf_counter()
        result = load_pack(_path(filename))
        result["source_file"] = filename
        log(f"Loaded {filename}: {time.perf_counter()-started:.3f}s")
        return (result,)

    @classmethod
    def IS_CHANGED(cls, filename, enabled):
        if not enabled:
            return "disabled"
        p = _path(filename)
        if not p.exists():
            return "missing"
        s = p.stat()
        return (s.st_mtime_ns, s.st_size)



def _references_path(name):
    if not name or Path(name).is_absolute():
        raise ValueError("Select a relative file name inside models/refpacks/references.")
    candidate = (REFERENCES_ROOT / name).resolve()
    if not candidate.is_relative_to(REFERENCES_ROOT.resolve()):
        raise ValueError("Reference-set paths must remain inside models/refpacks/references.")
    return candidate


def _reference_files():
    files = folder_paths.get_filename_list("bexplains_refpacks_references")
    return sorted({f for f in files if f.endswith(REFERENCES_SUFFIX)})


class BExplainsSaveRefPacksReferences:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"references": (SET_TYPE,),
            "filename": ("STRING", {"default": "scene", "tooltip": "Reference-set name or relative path. The .references.safetensors extension is automatic. All pack data, roles and ordering are embedded in one file."}),
            "overwrite": ("BOOLEAN", {"default": False})}}
    RETURN_TYPES = (SET_TYPE, "STRING")
    RETURN_NAMES = ("references", "filename")
    FUNCTION = "save"
    CATEGORY = CATEGORY
    OUTPUT_NODE = True
    DESCRIPTION = "Save the complete assembled reference set into one independent file in models/refpacks/references. Preserve group and entry order, names, role IDs, encoder metadata and all cached tensors. Overwriting requires the overwrite toggle."

    def save(self, references, filename, overwrite):
        if not filename.strip():
            raise ValueError("Enter a reference-set filename.")
        if not filename.endswith(REFERENCES_SUFFIX):
            filename = filename.removesuffix(".safetensors") + REFERENCES_SUFFIX
        path = save_references(references, _references_path(filename), overwrite)
        text = f"Saved {filename}: {len(references['groups'])} pack group(s), {sum(len(g['entries']) for g in references['groups'])} reference(s), {Path(path).stat().st_size:,} bytes."
        return {"ui": {"text": [text]}, "result": (references, filename)}


class BExplainsLoadRefPacksReferences:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"filename": (_reference_files(),)}}
    RETURN_TYPES = (SET_TYPE,)
    RETURN_NAMES = ("references",)
    FUNCTION = "load"
    CATEGORY = CATEGORY
    DESCRIPTION = "Restore a complete reference set from one saved file. Connect directly to an encoder or inspector; original individual pack files are not needed."

    def load(self, filename):
        return (load_references(_references_path(filename)),)

    @classmethod
    def IS_CHANGED(cls, filename):
        path = _references_path(filename)
        if not path.exists():
            return "missing"
        stat = path.stat()
        return (stat.st_mtime_ns, stat.st_size)


class BExplainsAddRefPack:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"refpack": (PACK_TYPE,), "role": (list(ROLES),
                    {"tooltip": "character = person; item = object; subject = generic subject. These create subject definitions. motion/video require video references. H3 resolves Character/Item aliases to Subject IDs and Motion aliases to Video IDs. style = visual aesthetic, addressed as <Style N> by H3; reference = general-purpose pictures without prescribed semantics. keyposes = discrete key poses, as image frames or one video, spread over the shot; H3 resolves <Poses N> to their Picture/Video slots and emits per-pose timing."})},
                "optional": {"references": (SET_TYPE,)}}
    RETURN_TYPES = (SET_TYPE,)
    RETURN_NAMES = ("references",)
    FUNCTION = "add"
    CATEGORY = CATEGORY

    DESCRIPTION = "Append saved or temporary references. Use role reference for general-purpose pictures: style, objects, lighting or any other use. They become <Picture N> without prescribed semantics. Character, Item and Motion have their own alias counters. Subject IDs are shared across subject, character and item groups and remain stable when more packs are appended."

    def add(self, refpack, role, role_id=0, references=None):
        # Accept a stale role_id keyword from old API prompts for compatibility,
        # but never use it: all IDs exposed by this node are automatically assigned.
        return (add_pack(refpack,references,role,0),)


class BExplainsMergeRefPackBundles:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {f"bundle_{i}": (SET_TYPE,) for i in (1, 2)},
            "optional": {f"bundle_{i}": (SET_TYPE,) for i in range(3, 65)},
        }

    RETURN_TYPES = (SET_TYPE,)
    RETURN_NAMES = ("references",)
    FUNCTION = "merge"
    CATEGORY = CATEGORY
    DESCRIPTION = "Merge bundles in input-slot order. More slots appear as you connect bundles (up to 64). Retains all groups and cached media, preserving the first bundle's IDs and remapping later collisions. Inspect the merged references for the final prompt tags."

    def merge(self, bundle_1, bundle_2, **kwargs):
        bundles = [bundle_1, bundle_2]
        for i in range(3, 65):
            bundle = kwargs.get(f"bundle_{i}")
            if bundle is not None:
                bundles.append(bundle)
        return (merge_bundles(bundles),)


class BExplainsRefPacksPreviewText:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"text": ("STRING", {"forceInput": True})}}
    RETURN_TYPES = ("STRING",)
    FUNCTION = "show"
    CATEGORY = CATEGORY
    OUTPUT_NODE = True

    def show(self,text):
        return {"ui": {"text": [text]}, "result": (text,)}


from .shared_nodes import BExplainsEncodeImageReferences, BExplainsEncodeVideoReference, BExplainsRefPackToImage, BExplainsRefPackToVideo, BExplainsInspectReferences
CLASSES = [BExplainsMergeRefPackBundles, BExplainsSaveRefPacksReferences, BExplainsLoadRefPacksReferences, BExplainsSaveRefPack, BExplainsLoadRefPack, BExplainsAddRefPack, BExplainsRefPacksPreviewText,
           BExplainsEncodeImageReferences, BExplainsEncodeVideoReference, BExplainsRefPackToImage, BExplainsRefPackToVideo, BExplainsInspectReferences]
NODE_CLASS_MAPPINGS = {c.__name__: c for c in CLASSES}
NODE_DISPLAY_NAME_MAPPINGS = {
    "BExplainsMergeRefPackBundles": "BExplains Merge RefPack Bundles",
    "BExplainsSaveRefPacksReferences": "BExplains Save RefPack Bundles",
    "BExplainsLoadRefPacksReferences": "BExplains Load RefPack Bundles",
    "BExplainsSaveRefPack": "BExplains Save RefPack",
    "BExplainsLoadRefPack": "BExplains Load RefPack",
    "BExplainsAddRefPack": "BExplains Add RefPack",
    "BExplainsRefPacksPreviewText": "BExplains RefPacks Preview Text",
    "BExplainsEncodeImageReferences": "Encode Image Refpack",
    "BExplainsEncodeVideoReference": "Encode Video Refpack",
    "BExplainsRefPackToImage": "BExplains RefPack to Image Encoder",
    "BExplainsRefPackToVideo": "BExplains RefPack to Video Encoder",
    "BExplainsInspectReferences": "BExplains Inspect RefPack Metadata",
}
