# Releasing Aussie Weather

## Version bump checklist

1. `metadata.json` → `KPlugin.Version`
2. `contents/ui/main.qml` → `_widgetVersion` (must match; no QML API exposes
   the package version at runtime — this also feeds the User-Agent)
3. `CHANGELOG.md` → new section
4. If strings changed: `./translate/merge.sh` and commit the updated
   `template.pot`

## Release

1. `./translate/build.sh` (compiles any `.po` into `contents/locale/`)
2. Package: `zip -qr net.tropism.plasma.aussieweather-<version>.plasmoid metadata.json contents/`
3. Tag `v<version>`, push the tag — the release workflow (Phase 6, pending)
   builds the package and attaches it to a GitHub Release. Until then, attach
   manually.

## KDE Store (manual until the publish workflow exists)

Initial listing (one-time):

1. Account on https://store.kde.org (Pling).
2. Add Product → category **Plasma 6 Applets / Plasma 6 Widgets**.
3. Upload the `.plasmoid`, screenshots, description (reuse README features +
   the BoM disclaimer — the disclaimer is mandatory in the listing).
4. Record the product content-ID here and as the `PLING_CONTENT_ID` repo
   variable (used by the future publish workflow).

**Product content-ID:** _not yet created_

Updates: edit the product → Files → upload the new `.plasmoid`, update the
changelog text.

## OCS API notes (for the future store-publish workflow)

- Endpoint: `https://api.pling.com/ocs/v1/` — basic auth with Pling username
  + API token (account settings → API). Secrets: `PLING_USERNAME`,
  `PLING_TOKEN`.
- Upload: `POST content/edit/<content-id>` with the file; lightly documented,
  treat failures as non-fatal in CI and fall back to manual upload.
