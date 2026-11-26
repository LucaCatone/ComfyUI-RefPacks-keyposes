# RefPacks — keyposes fork

> Shared nodes for [BExplains MiniMax H3 RefPacks](https://github.com/BExplains/ComfyUI-MiniMax-H3-RefPacks).
> This fork adds the **`keyposes`** role to the role list, lets it accept image packs as well as a single
> pose video (not both in one pack), and documents it in the role tooltip. The package identity is
> `bexplains-refpacks-keyposes` so it does not collide with the upstream registry entry.
> Install alongside the H3 fork of the same name suffix.

---

**Prepare references once, save them as reusable assets, and reuse a complete scene setup across shots.**

RefPacks stores cached image, video and audio reference data together with the metadata needed to use it again. Save individual assets, assign roles such as Character, Item or Motion, and save the whole assembled reference set as a single file.

This is the shared package. Model-specific preparation and prompting belong in separate collections, starting with **[MiniMax H3 RefPacks](https://github.com/BExplains/ComfyUI-MiniMax-H3-RefPacks)**. Installing the H3 collection is optional unless you want to use H3 nodes or workflows.

**Version 1.0.1.** The included Flux 2 and LTXV 0.9.8 adapters are **experimental testing integrations, not officially supported model integrations**. Publishing the shared package does not change their validation status.

## Contents

- [Features](#features)
- [Requirements and installation](#requirements-and-installation)
- [Quick start](#quick-start)
- [Node reference](#node-reference)
- [Reference roles](#reference-roles)
- [Prompting and JSON](#prompting-and-json)
- [How it works](#how-it-works)
- [Compatibility](#compatibility)
- [Resolution and performance](#resolution-and-performance)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Reporting problems](#reporting-problems)
- [Credits](#credits)

## Features

- Save/load individual RefPacks without rerunning their source VAE encoding.
- Combine assets into an ordered reference set with named roles.
- Save/load the complete reference set in **one self-contained file**.
- Preserve group order, image/video/audio data, names, role IDs and encoder provenance.
- Keep individual assets separate from scene or segment collections.
- Refuse overwrites unless the **overwrite** toggle is enabled.
- Use atomic file replacement when overwriting is explicitly enabled.
- Add file extensions automatically; plain names and subdirectories are accepted.
- Inspect reference metadata before text encoding or sampling.
- Provide shared image/video receiver interfaces with model-specific adapters.

Reference preparation is not LoRA training. Saving a pack does not modify model weights, learn a trigger word or make one model's latent data compatible with another model.

## Requirements and installation

Requires ComfyUI, its normal PyTorch environment, and `safetensors`. Model-specific nodes also require a ComfyUI version with native support for that model family and its matching weights.

### Install from the Comfy Registry

Install with ComfyUI-Manager or Comfy CLI:

```bash
comfy node install bexplains-refpacks
```

[Registry listing](https://registry.comfy.org/publishers/bexplains/nodes/bexplains-refpacks). New releases must complete registry security processing before an active release is available.

The H3 collection requires the shared **BExplains RefPacks** custom-node package. Install it separately; Python dependency installation does not install the companion node pack. Keep only one installed copy of each package, then restart ComfyUI.

### Install from source

From your ComfyUI directory:

```bash
cd custom_nodes
git clone https://github.com/BExplains/ComfyUI-RefPacks.git BExplains_RefPacks
```

The command uses the legacy folder name **`BExplains_RefPacks`**. The H3 collection also discovers registry installs named `bexplains-refpacks` and source clones named `ComfyUI-RefPacks`, including configured custom-node directories.

If needed, install the requirements using ComfyUI's Python environment:

```bash
python -m pip install -r custom_nodes/BExplains_RefPacks/requirements.txt
```

Run that requirements command from the ComfyUI directory. For a portable installation, use its bundled Python rather than a different system environment.

Restart ComfyUI and refresh the browser. Shared nodes are under **BExplains / RefPacks**.

### Add the H3 collection

From `ComfyUI/custom_nodes/`:

```bash
git clone https://github.com/BExplains/ComfyUI-MiniMax-H3-RefPacks.git BExplains_H3_RefPacks
```

Install both folders as siblings. See the [H3 collection's README](https://github.com/BExplains/ComfyUI-MiniMax-H3-RefPacks#readme) for H3 weights, preparation and generation instructions.

### Install from an archive

Copy this package into `ComfyUI/custom_nodes/BExplains_RefPacks/`. Its `__init__.py` must be directly inside that folder, without another nested repository folder. For H3, also copy the H3 package into `ComfyUI/custom_nodes/BExplains_H3_RefPacks/`.

When upgrading from the earlier combined package, replace the old shared folder and install the separate H3 collection. Individual reference files remain in `models/refpacks/`; do not delete those assets when replacing the custom-node code.

## Quick start

### Save and reuse an individual asset

1. Prepare a reference with the appropriate collection's encoder. For H3, use **Encode H3 Image Refpack**, **Encode H3 Video Refpack** or **Encode H3 Audio Refpack** from the H3 collection.
2. Connect its `refpack` output to **BExplains Save RefPack**.
3. Enter a plain name such as `mai_concert`.
4. Queue the workflow.

The file is saved as `ComfyUI/models/refpacks/mai_concert.safetensors`. Save is an output node, so it can run without a sampler connected. It also passes the original `refpack` through for immediate use.

In another workflow, use **BExplains Load RefPack**, select the saved file, then connect it to **BExplains Add RefPack**. Choose its role and connect the resulting `references` to the appropriate receiving encoder.

**overwrite is off by default.** Use a new filename or explicitly enable overwriting to replace an asset. One STRING output can feed both the preparation node's name and Save's filename; the extension is automatic.

### Build a reference set

Chain **Add RefPack** nodes through their `references` inputs. For example:

| Asset | Add RefPack role |
| --- | --- |
| Woman's reference images | `character` |
| Microphone reference images | `item` |
| Concert outfit | `outfit` |
| Stage reference | `location` |
| Performance video | `motion` |

Each Add node returns the assembled set. Independent views within one image pack remain separate Picture entries while belonging to the same group.

### Save a complete scene or segment

1. Connect the final Add node's `references` output to **BExplains Save RefPack Bundles**.
2. Enter a name such as `concert_opening`.
3. Leave overwrite off to protect an existing collection.
4. Queue the save node.

This creates:

```text
ComfyUI/models/refpacks/references/concert_opening.references.safetensors
```

In another shot, use **BExplains Load RefPack Bundles** and connect its `references` output directly to the receiving encoder or inspector. You do not need the original individual pack files or the Add RefPack chain.

### Merge bundles into an existing reference chain

Connect two **Load RefPack Bundles** outputs (or existing reference chains) to **BExplains Merge RefPack Bundles**. Another input appears as you connect the last slot, up to 64 bundles. Connect its `references` output to Add RefPack, an encoder, an inspector, Save RefPack Bundles, or another Merge node.

Groups are appended in input-slot order, preserving their names, roles, entries and cached media. The first bundle retains its IDs. Later role or subject IDs are kept when available and reassigned when they collide; inspect the merged output for the final prompt tags. Identical inputs are included twice, not deduplicated. Prompt text outside the bundles is not rewritten. Merging does not re-encode media or convert model families, so the receiving encoder still needs compatible references.

The merger copies metadata containers without duplicating cached tensors or modifying its inputs. Bundle-level metadata is retained under `merged_from`; the first bundle's top-level metadata is also kept. Each connected input must contain at least one reference group. Empty trailing slots are ignored.

Loading restores the same ordered groups, entry order, roles and subject IDs. You can append more packs after loading without changing the stored file. Saving references does not save the prompt, sampler, model weights or the whole workflow.

## Node reference

### Asset and scene nodes

| Display name | Internal ID | Inputs | Outputs |
| --- | --- | --- | --- |
| BExplains Save RefPack | `BExplainsSaveRefPack` | `refpack`, `filename`, `overwrite` | Original `refpack`, complete `filename` |
| BExplains Load RefPack | `BExplainsLoadRefPack` | File selection, `enabled` | `refpack`; disabled returns no pack |
| BExplains Add RefPack | `BExplainsAddRefPack` | `refpack`, `role`, optional previous `references` | Assembled `references` |
| BExplains Merge RefPack Bundles | `BExplainsMergeRefPackBundles` | Two or more bundles (expanding input slots, up to 64) | Combined `references` |
| BExplains Save RefPack Bundles | `BExplainsSaveRefPacksReferences` | `references`, `filename`, `overwrite` | Original `references`, complete `filename` |
| BExplains Load RefPack Bundles | `BExplainsLoadRefPacksReferences` | File selection | Restored `references` |
| BExplains Inspect RefPack Metadata | `BExplainsInspectReferences` | `references`, optional `vae`, `audio_vae` | Original set, metadata `report`, `Images`, `Audio` |
| BExplains RefPacks Preview Text | `BExplainsRefPacksPreviewText` | `text` | Same STRING, displayed on the node |

The metadata inspector lists names, roles, model targets, source labels, encoder classes and tensor shapes. The H3 collection supplies a separate inspector for native Picture/Video/Audio addressing and compiled prompts.

### Experimental preparation nodes

| Display name / internal ID | Purpose |
| --- | --- |
| **Encode Image Refpack** / `BExplainsEncodeImageReferences` | Encode each input batch image separately with the chosen model family's VAE. Inputs: `vae`, `images`, `model_family`, `name`, `width`, `height`. Output: `refpack`. |
| **Encode Video Refpack** / `BExplainsEncodeVideoReference` | Prepare an LTXV video-prefix guide. Inputs: `vae`, `frames`, `model_family`, `name`, source `fps`, `width`, `height`. Pads the final frame to the adapter's temporal grid. Output: `refpack`. |

These shared preparation adapters currently target Flux 2 images and LTXV 0.9.8 image/video guides for testing. Use the separate H3 preparation nodes for H3 assets.

### Experimental receiving encoders

Both receivers take `model`, `clip`, decoding `vae`, `references`, `prompt`, `negative_prompt`, `width` and `height`.

| Node / internal ID | Additional inputs | Current testing target |
| --- | --- | --- |
| **BExplains RefPack to Image Encoder** / `BExplainsRefPackToImage` | `batch_size`, `guidance` | Flux 2 |
| **BExplains RefPack to Video Encoder** / `BExplainsRefPackToVideo` | Integer `length`, `frame_rate`, `strength` | Video-only LTXV 0.9.8 |

Outputs, in order: `model`, `positive`, `negative`, `latent`, `vae`, `reference_report`. Sampling remains downstream. Connect the VAE output to the decoder and use sampling settings appropriate to the actual checkpoint.

The image receiver attaches cached native `reference_latents`. The LTXV receiver currently accepts **one first-image or leading-video guide**, initializes the video prefix, and sets the corresponding noise mask and frame-rate conditioning. Multiple independently positioned guides are not implemented in this adapter.

### Extract media from an inspected RefPack

Connect **Load RefPack → Add RefPack → Inspect**, or connect **Load RefPack Bundles** directly to an inspector. Both the shared metadata inspector and **BExplains Inspect Refpacks** expose `Images` and `Audio` after their original outputs.

- **Images without `vae`:** returns the stored reference pixels without decoding. H3 video references contain sampled vision frames, not every frame of the source clip.
- **Images with `vae`:** reconstructs image/video latents using the matching visual VAE. A video entry stays together as one IMAGE batch, suitable for video preview or re-encoding. Use the VAE matching the entries; mixed model-family sets may require inspecting separate sets.
- **Audio with `audio_vae`:** reconstructs each audio entry through ComfyUI's native audio decoder. The waveform and output sample rate are returned as standard AUDIO data. This is a VAE reconstruction, not the original waveform.
- **Audio without `audio_vae`:** returns an empty audio list and explains in the report that an audio VAE is needed. Metadata inspection and image extraction still work.

Both VAE inputs are optional. Leave them disconnected for metadata-only inspection or when their decoded output is not needed. `Images` and `Audio` are list outputs: each visual entry retains its dimensions and each audio clip stays separate. Connect them to Preview Image/Preview Audio or the appropriate Refpack encoder; downstream nodes run for each list item. An absent media type produces an empty list, not a fabricated black image or silent clip. Pixels and decoded audio can be re-encoded, but do not recover detail discarded during the original preparation or VAE encoding.

## Reference roles

| Role | Required media | Meaning |
| --- | --- | --- |
| `subject` | Images | Generic subject, without assuming a person |
| `character` | Images | Person identity and appearance |
| `item` | Images | An object with its own subject definition |
| `outfit` | Images | Clothing reference |
| `location` | Images | Environment or architecture reference |
| `style` | Images | Visual aesthetic, colors, lighting and rendering style; addressed as `<Style n>` in H3 |
| `reference` | Images or other valid pack entries | General reference material without a prescribed subject definition |
| `video` | Video | General source-video reference |
| `motion` | Video | Motion, poses and temporal structure |
| `audio` | Audio | Audio reference |

Character and Item alias counters are independent, but their native Subject IDs share a stable namespace with generic subjects. Legacy Subject IDs remain reserved. Saved reference sets retain these IDs.

Roles describe the reference set. Their interpretation depends on the receiving integration: **H3 expands Character/Item/Motion aliases; the experimental Flux/LTX receivers do not run the H3 compiler**.

## Prompting and JSON

The shared Flux 2 and LTXV testing receivers pass the positive and negative prompt text directly to their text encoder. They do not insert H3 subject definitions or rewrite aliases. For Flux 2, describe the requested result and refer to images in reference order. For LTXV, describe the action and camera behavior appropriate to the first-image or prefix guide.

H3's receiving encoder adds role-aware compilation and an **Allow Raw Prompt** toggle. With that toggle enabled, recognized structured text or JSON passes through unchanged. For example:

```json
{
  "subject_definitions": "<Subject 1> is the woman shown in <Picture 1>.",
  "description": "<Subject 1> holds the microphone shown in <Picture 2>."
}
```

This example belongs in the H3 receiver. It is exact text passthrough, not a universal JSON schema for other models. See the [H3 prompting documentation](https://github.com/BExplains/ComfyUI-MiniMax-H3-RefPacks#prompting) for detection rules, accepted keys and native reference addressing.

### Style references

Prepare and load an image RefPack, then select **style** on **Add RefPack**. In an H3 shot instruction, write:

```text
<Character 1> dances in the style of <Style 1>.
```

If the character occupies Picture 1 and the style pack occupies Picture 2, this becomes `<Subject 1> dances in the style of <Picture 2>.` A style pack with several images expands to all its Picture slots, such as `<Picture 2> and <Picture 3>`. Style numbering is independent of character, item and other role counters. Inspect Refpacks shows the exact mapping. Style references do not create additional Subject IDs or participate in Auto Outfit's wearer selection.

The role accepts images only, uses the existing RefPack file format and survives scene save/load. It guides visual style; it does not train a style LoRA or guarantee a particular rendering. Raw structured prompt passthrough does not expand `<Style n>`; use native `<Picture n>` tags there. The experimental Flux/LTX receivers do not run H3 alias expansion.

## How it works

There are two data types:

| Data type | Represents | Typical file |
| --- | --- | --- |
| `BEXPLAINS_REFPACK` | One prepared asset with one or more reference entries | `character.safetensors` |
| `BEXPLAINS_REFERENCES` | Ordered groups of assets assigned to roles | `scene.references.safetensors` |

Individual assets contain cached tensors and metadata such as `target`, `source_target` and `encoder_class`. Add RefPack groups those assets and assigns roles and stable IDs. Receiving integrations validate their model-specific tensor layouts and conditioning protocols.

| Container | Metadata key | Format / version |
| --- | --- | --- |
| Individual pack | `bexplains_refpack` | `bexplains.refpack`, version `1` |
| Complete reference set | `bexplains_references` | `bexplains.references`, version `1` |

The scene container embeds the complete tensor data plus an ordered JSON manifest, including collection name, group names, roles, IDs, encoder provenance, source labels and entry metadata. No ZIP extraction, external pack links or separate sidecar file is needed. Tensors are saved losslessly on CPU without pickle.

The application version **1.0.1** is separate from the on-disk format versions.

## Compatibility

| Scenario | Status |
| --- | --- |
| Shared asset/set persistence and metadata inspection | Implemented; CPU serialization and ordering checks pass |
| H3 preparation and generation | Provided by the separate H3 collection |
| Existing version-1 H3 RefPacks | Remain readable; keep the H3 collection installed for H3 nodes |
| Earlier H3 node IDs | Retained by the H3 collection |
| Flux 2 | Experimental adapter for testing; not official model support |
| LTXV 0.9.8 | Experimental first-image/video-prefix adapter; not official model support |
| LTX-2 audio/video models | Not routed through the LTXV 0.9.8 adapter |
| Reusing H3 latents directly in Flux or LTX | Rejected; recreate with that model's VAE |
| Older RefMod bundles | Different format; see the H3 collection's limited importer |

Container compatibility is not latent-space compatibility. Copying, renaming or loading a file does not convert its encoding to another model.

## Resolution and performance

- Shared image preparation resizes and center-crops to its requested encoding dimensions. Each batch image becomes its own entry.
- The Flux 2 testing adapter uses multiples of 16; the LTXV testing adapter uses multiples of 32.
- For LTXV, prepare the reference at the final video resolution. A mismatch is rejected before text encoding. Output length rounds up to `8n + 1`; the source FPS is stored as provenance, not automatically retimed by the receiver.
- A saved pack avoids repeated source VAE encoding. Models still process reference conditioning during generation, so more or larger references can increase sampling cost.
- Scene files embed the data rather than linking to external assets; their size reflects the included tensors.
- Cached pixels are preprocessed reference pixels, not archival copies of the original PNG, JPEG or source video. Keep original media if you may need to recreate assets for another model.

### Example workflows

- [Flux 2 RefPack to Image](workflows/01_Flux2_RefPack_To_Image.json): preparation, save, reference conditioning, native Flux2Scheduler and image output.
- [LTXV 0.9.8 RefPack to Video](workflows/02_LTXV_098_RefPack_To_Video.json): minimal single-pass distilled testing example. It is not the official multi-scale upscaling pipeline.

Select local weights and media. For comparisons with earlier tutorials, retain their known-working model, sampler and decoder settings and replace the reference-preparation/conditioning portion.

## Troubleshooting

| Problem | Check |
| --- | --- |
| Nodes missing | Check startup errors, restart ComfyUI, refresh the browser and verify the folder layout. |
| H3 dependency cannot be found | Install the shared package as `bexplains-refpacks`, `ComfyUI-RefPacks` or `BExplains_RefPacks` in a configured custom-node directory, then restart ComfyUI. |
| New file absent from a loader | Refresh node definitions or the browser. Individual packs and complete reference sets have separate loader lists. |
| Existing-file error | Choose a new name or explicitly enable overwrite. Default saves preserve the original file. |
| Individual loader rejects a scene file | Use **Load RefPack Bundles**, not **Load RefPack**. |
| Wrong-model error | Recreate the asset with the intended model family's VAE; changing the filename is not conversion. |
| LTX reference resolution error | Match preparation width/height to output width/height. |
| Multiple LTX guide error | This adapter accepts one first image or video prefix, not an arbitrary set of identity/outfit guides. |
| Typed aliases appear literally in Flux/LTX | Those receivers do not use H3 prompt compilation. Use their model's native prompt conventions. |

## FAQ

### Is this a LoRA or a trained identity model?

No. RefPacks stores reference data; it does not train or modify diffusion weights.

### Can I save a whole scene setup?

Yes. Save the final references output with **Save RefPack Bundles**. The resulting file includes all underlying pack data and role ordering.

### Do the original individual files need to remain on disk?

Not for a saved reference set. Its tensor data is embedded. Keep source media for future re-encoding or another model family.

### Can I load a scene and add one extra asset?

Yes. Connect the loaded set to another Add RefPack node. Existing groups and subject IDs stay stable; the original saved file is unchanged until you explicitly save again.

### Can a character sheet be used?

Yes, through an appropriate image preparation node. A sheet remains one reference image; it is not automatically split into separate crops.

### Are Flux 2 and LTXV officially supported now that this is 1.0.0?

No. They remain experimental testing targets. Version 1.0.0 publishes the package; it does not establish validated production support for those model integrations.

### Can future model collections share these files?

They can share the container and metadata conventions. Each collection must validate compatible encodings or implement conversion; a common file extension alone is not sufficient.

## Reporting problems

Include:

- Package version and ComfyUI version/commit.
- Which collection and receiving model are in use.
- Exact checkpoint, text encoder and VAE filenames.
- Workflow JSON, prompt, seed, dimensions and sampling settings.
- Whether the input is an individual pack or saved reference set, its roles and source counts.
- Full traceback for execution errors, or representative outputs for visual failures.

Use the [shared package's issues](https://github.com/BExplains/ComfyUI-RefPacks/issues) for persistence or shared-node problems and the [H3 collection's issues](https://github.com/BExplains/ComfyUI-MiniMax-H3-RefPacks/issues) for H3 preparation/prompting behavior. Remove private information from shared workflows.

The current development checks comprise **101 passing CPU tests**, including serialization fidelity, reference addressing and native-source payload comparisons. They do not replace live frontend or pretrained-model GPU testing. See [VALIDATION.md](VALIDATION.md) and [CHANGELOG.md](CHANGELOG.md).

## Credits

- **[ComfyUI contributors](https://github.com/Comfy-Org/ComfyUI)** — native model integrations, VAE and conditioning infrastructure.
- **[MiniMax](https://github.com/MiniMax-AI)**, **[Black Forest Labs](https://github.com/black-forest-labs)** and **[Lightricks](https://github.com/Lightricks)** — model families used by the current integrations and testing adapters.
- **[BExplains](https://github.com/BExplains)** — RefPacks and the node collections.

The companion [H3 Image RefMods project](https://github.com/BExplains/ComfyUI-MiniMaxH3-Image-RefMods) documents the earlier RefMod approach. RefPacks uses its own format; the earlier creator and its upstream loader/Apply extension are not runtime dependencies of this shared package. Attribution does not imply endorsement.

## License

Released under the [MIT License](LICENSE). Model weights and third-party dependencies retain their own licenses.
