# Enable daily profile updates

Copy the contents of this folder into the root of ahmdchr/ahmdchr on the main branch. Preserve these paths:

```
README.md
dark_mode_v2.svg
light_mode_v2.svg
scripts/update_profile.py
.github/workflows/update-profile.yml
```

If uploading through GitHub's website, upload the README and two SVG files. Then use **Add file → Create new file** for each of the two nested files, typing its full path above into the filename box and pasting its contents. This avoids accidentally missing the hidden .github folder. Commit both files to main.

Go to **Actions → Update profile stats → Run workflow** for the first run. It also runs when these files are committed and daily at 05:23 UTC (06:23 in Tunis). GitHub may delay scheduled runs.

The workflow uses GitHub's built-in token; no personal access token or added secret is required. It updates public owned repository count (including forks), stars received across those repositories, followers, following, and the UTC update date. It preserves the portrait and all other SVG content. These counts are live after a successful run; the bundled images initially contain the prior snapshot.

This version does not calculate Andrew's historical commit or lines-of-code totals, which need a different, more extensive collection process.

If a run cannot push, check that repository rules allow the workflow to commit to main. If organization policy restricts write permissions, the policy must permit this workflow's contents: write permission. Do not disable branch protection just to enable this; use a pull-request workflow if required.

GitHub may disable schedules on public repositories after 60 days without activity. Re-enable the workflow from the Actions tab if that occurs. The workflow must be present on the default branch; this package assumes it is main.
