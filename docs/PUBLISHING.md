# Publish the actual repository on GitHub

The publicly audited `Alexispher/pocketport-anything` `main` initially contained only `README.md`, `LICENSE`, and `.gitignore` at commit `bb092ecdde16e0af547be7cc27717a86fdf5a91b`. The project expansion ZIP was built locally in a separate environment. The GitHub branch `pocketport-v0.2-engine-expansion` was created from `main` by authorized connector, **but the ZIP contents are not pushed automatically**.

## Linux/macOS / Git Bash

```bash
git clone https://github.com/Alexispher/pocketport-anything.git
cd pocketport-anything
git switch pocketport-v0.2-engine-expansion
# Extract pocketport-anything.zip to a temporary directory, then copy its
# pocketport-anything/ contents (including dotfiles) over this checkout.
cp -a /path/to/extracted/pocketport-anything/. .
python -m unittest discover -s tests -v
git status --short
git add .
git diff --cached --stat
git commit -m "Build evidence-driven PocketPort runtime and game demos"
git push origin pocketport-v0.2-engine-expansion
```

Then open a pull request from `pocketport-v0.2-engine-expansion` to `main`, review the diff and GitHub Actions host CI results, and merge only once you approve the changes. **Do not** force-push main, reset the branch, or commit local commercial assets.

## Windows PowerShell

Extract the ZIP with `Expand-Archive` into a fresh folder, then use `Copy-Item -Recurse -Force` on all extracted repository files including the hidden `.agents` and `.github` folders. Switch to the prepared branch in a freshly cloned repository before copying. Review `git status`, run tests and then commit/push as above. Alternatively run the Linux commands in Git Bash. Never copy the `.git` directory from an extracted package.

## Using the agent

```text
Read https://github.com/Alexispher/pocketport-anything and follow AGENTS.md.
I want to play <game> on Nintendo 3DS.
```

The agent must have a checkout of the **updated branch/merged release**; the initial `main` does not yet contain `AGENTS.md`. Give the agent explicit authorization only for files you own or may legally use. Use REA via its own correctly installed MCP integration if native binary analysis is needed, not by assuming a Python import automatically connects it.
