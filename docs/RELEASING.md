# Releasing Aussie Weather

## Version bump checklist

1. `metadata.json` → `KPlugin.Version`. The widget reads its version from
   here at runtime (`Plasmoid.metaData.version`) for its User-Agent.
2. `CHANGELOG.md` → a new `## <version> — <date>` section. The release
   workflow fails without one.
3. If strings changed: `./translate/merge.sh`, and commit the updated
   `template.pot`. CI fails while it is out of date.

## Release

1. Commit and push all changes to `main`, and wait for CI to pass.
2. Tag `v<version>` and push the tag:

   ```sh
   git tag v1.x
   git push origin v1.x
   ```

3. The release workflow runs automatically. It first runs all of CI's
   checks (the tests, the QML compiled and rendered against real Plasma,
   the translation template); then it builds the `.plasmoid` (with
   compiled translations) with `scripts/package.sh`, checks the tag
   matches `metadata.json` and extracts the CHANGELOG section, all with a
   read-only token; a separate job, which runs no code from the
   repository, creates the GitHub Release with the `.plasmoid` and
   `SHA256SUMS` attached.
4. Upload to the KDE Store manually (see below).
5. Bump the submodule pointer in the `plasmoids` repo.

## KDE Store upload (manual)

opendesktop.org's OCS API offers no working way to upload a file (as of
2026-06-13 its content endpoints answered `statuscode: 999 — unknown
request`), so the store is updated by hand after each release:

1. Go to the [product page](https://www.opendesktop.org/p/2362509/).
2. **Files** tab → **Upload a new file** → pick the `.plasmoid` from the
   [GitHub Release assets](https://github.com/hamsolodev/plasma-aussieweather/releases/latest),
   after checking it against the release's `SHA256SUMS`.
3. Update the changelog / description text if needed.

**Product content-ID:** `2362509`
