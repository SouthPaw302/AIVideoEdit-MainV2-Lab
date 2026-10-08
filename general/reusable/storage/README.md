# GitHub Releases Media Storage

AIVideoEdit uses GitHub Releases as the durable binary store when no external object store is configured.

## Model

- `main` remains the AIVideoEdit OS.
- `song/<slug>` remains the production state.
- One release tag, `media-<slug>`, stores the large media for that song.
- The song branch keeps `STORAGE_MANIFEST.json` with hashes and asset names.
- Song productions do not need to merge into `main`.

Release assets are flat, so the adapter prefixes every uploaded filename with one of these categories:

- `source__`
- `generated__`
- `proofs__`
- `final__`
- `qc__`
- `archive__`

Example assets:

```text
source__Ironflame.wav
generated__shot_assets.zip
proofs__shot_proofs.zip
final__IronFlame_FINAL_720p24.mp4
qc__FINAL_QC.zip
archive__production_archive.zip
```

## Requirements

- GitHub CLI: `gh`
- Authenticated access to `SouthPaw302/AIVideoEdit`

Check auth:

```bash
gh auth status
```

## Initialize a song release

```bash
python general/reusable/storage/github_release_storage.py init ^
  --slug ironflamenew ^
  --branch song/ironflamenew ^
  --manifest projects/ironflamenew/STORAGE_MANIFEST.json
```

On Bash, replace `^` with `\`.

## Upload media

```bash
python general/reusable/storage/github_release_storage.py upload ^
  --slug ironflamenew ^
  --branch song/ironflamenew ^
  --category final ^
  --file IronFlame_FINAL_720p24.mp4 ^
  --manifest projects/ironflamenew/STORAGE_MANIFEST.json
```

The adapter computes SHA-256, uploads the asset as `final__<filename>`, and updates the branch-local storage manifest.

## Recover media

List remote assets:

```bash
python general/reusable/storage/github_release_storage.py list --slug ironflamenew
```

Download only final masters:

```bash
python general/reusable/storage/github_release_storage.py download ^
  --slug ironflamenew ^
  --pattern "final__*" ^
  --output recovered_media
```

## Limits

GitHub Releases allows individual assets up to 2 GiB. The adapter refuses larger files rather than silently failing. Large production archives should be split before upload.

Do not treat Releases as production authority. The song branch manifest is the index; the Release is the byte store.
