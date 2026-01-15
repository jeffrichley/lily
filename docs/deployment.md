# Deploying Lily Documentation

This guide explains how to deploy the Lily documentation site to GitHub Pages.

## Prerequisites

- GitHub repository set up
- MkDocs dependencies installed: `uv sync --group docs`
- Documentation site built: `just docs-build`

## GitHub Pages Deployment

### Option 1: Using mkdocs gh-deploy (Recommended)

The easiest way to deploy is using MkDocs' built-in GitHub Pages deployment:

```bash
# Build and deploy in one step
uv run mkdocs gh-deploy
```

This command:
1. Builds the documentation site
2. Creates/updates the `gh-pages` branch
3. Pushes to GitHub
4. GitHub Pages automatically serves from `gh-pages` branch

**Note**: Make sure `site_url` and `repo_url` in `mkdocs.yml` are configured correctly before deploying.

### Option 2: Manual Deployment

If you prefer manual control:

1. **Build the site**:
   ```bash
   just docs-build
   ```

2. **Copy to gh-pages branch**:
   ```bash
   git checkout --orphan gh-pages
   git rm -rf .
   cp -r site/* .
   git add .
   git commit -m "Deploy documentation"
   git push origin gh-pages
   git checkout main  # or your default branch
   ```

3. **Configure GitHub Pages**:
   - Go to repository Settings → Pages
   - Select source: `gh-pages` branch
   - Select folder: `/ (root)`
   - Save

### Option 3: GitHub Actions (Automated)

For automated deployment on every push:

1. Create `.github/workflows/docs.yml`:
   ```yaml
   name: Deploy Documentation
   
   on:
     push:
       branches:
         - main
       paths:
         - 'docs/**'
         - 'mkdocs.yml'
   
   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-python@v4
           with:
             python-version: '3.13'
         - uses: astral-sh/setup-uv@v1
         - run: uv sync --group docs
         - run: uv run mkdocs gh-deploy --force
           env:
             GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
   ```

2. Push to trigger deployment

## Configuration

### Update mkdocs.yml

Before deploying, update these settings in `mkdocs.yml`:

```yaml
site_url: https://yourusername.github.io/lily/  # Your GitHub Pages URL
repo_url: https://github.com/yourusername/lily  # Your repository URL
```

The `site_url` should match your GitHub Pages URL pattern:
- User/organization pages: `https://username.github.io/repository/`
- Project pages: `https://username.github.io/repository/`

## Troubleshooting

### Site not updating

- Clear browser cache
- Check GitHub Pages settings
- Verify `gh-pages` branch exists and has content
- Check GitHub Actions logs (if using Actions)

### Broken links

- Ensure `site_url` is correct in `mkdocs.yml`
- Use relative links in Markdown files
- Rebuild site after changing `site_url`

### 404 errors

- Verify GitHub Pages is enabled
- Check branch name matches Pages source
- Ensure `index.html` exists in root of `gh-pages` branch

## Local Testing

Before deploying, test locally:

```bash
# Serve locally
just docs-serve

# Open http://127.0.0.1:8000
# Verify all links work
# Check search functionality
# Test dark mode toggle
```

## Continuous Deployment

For automatic deployment on every documentation update:

1. Set up GitHub Actions workflow (see Option 3 above)
2. Configure to trigger on changes to `docs/` or `mkdocs.yml`
3. Push changes - documentation deploys automatically

## Related Documentation

- [Quickstart Guide](specs/002-docs-site-infrastructure/quickstart.md)
- [MkDocs Configuration](specs/002-docs-site-infrastructure/contracts/mkdocs-config.md)

