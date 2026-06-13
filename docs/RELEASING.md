# Releasing Aussie Weather

## Version bump checklist

1. `metadata.json` → `KPlugin.Version`
2. `contents/ui/main.qml` → `_widgetVersion` (must match; no QML API exposes
   the package version at runtime — this also feeds the User-Agent)
3. `CHANGELOG.md` → new section with date
4. If strings changed: `./translate/merge.sh` and commit the updated
   `template.pot`

## Release

1. Commit and push all changes to `main`.
2. Tag `v<version>` and push the tag:

   ```sh
   git tag v1.x
   git push origin v1.x
   ```

3. The release workflow runs automatically: builds the `.plasmoid` (with
   compiled translations), extracts the CHANGELOG section, and creates a
   GitHub Release with the artifact attached.
4. Upload to the KDE Store manually (see below).
5. Bump the submodule pointer in the `plasmoids` repo.

## KDE Store upload (manual)

The automated store-publish workflow exists but the OCS v1 API authentication
does not work with username + account password — opendesktop.org appears to
require a separate API key that is not exposed in the account UI. Until that
is resolved, upload manually after each release:

1. Go to the [product page](https://www.opendesktop.org/p/2362509/).
2. **Files** tab → **Upload a new file** → pick the `.plasmoid` from the
   [GitHub Release assets](https://github.com/hamsolodev/plasma-aussieweather/releases/latest).
3. Update the changelog / description text if needed.

**Product content-ID:** `2362509`

## OCS API (automated publish — currently non-functional)

- `PLING_CONTENT_ID` repo variable: `2362509`
- Secrets `PLING_USERNAME` / `PLING_TOKEN`: set in repo secrets.
- The workflow (`store-publish.yml`) triggers on release published and can
  also be dispatched manually (`workflow_dispatch`, `tag` input).
- As of 2026-06-13, all OCS v1 endpoints return `statuscode: 999 — unknown
  request` for content operations, and `person/self` returns
  `102 Not Authorized` with Basic Auth. The API may require an API key
  separate from the account password; check account settings → API if
  opendesktop.org adds this in future.
- The workflow has `continue-on-error: true` — a failed store publish never
  blocks the GitHub Release.
