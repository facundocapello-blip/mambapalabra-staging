# Mambapalabra B1.12 STAGING

This repository is isolated from the existing Mambapalabra GitHub Pages site and Floot production.

Deployment requires these files at the repository root:
- `index.html`
- `CANDIDATE.json`
- `ASSETS_SHA256.json`
- `.nojekyll`
- all audio and other paths listed in `ASSETS_SHA256.json`

Source of truth: `facundocapello-blip/Mambapalabra`, branch `qa/b112-guest-voice-handoff`. The verified `dist/MAMBAPALABRA_B1_12_STAGING.zip` from `tools/package_release_b112.py` contains the files to copy into this repository.

Once populated, go to Settings > Pages > Build and deployment > Source and select **GitHub Actions**. Then run **Deploy B1.12 STAGING** under Actions. The workflow rejects any candidate whose HTML hash does not match or that references the production Supabase project.

Do not run deployment before copying the verified assets.
