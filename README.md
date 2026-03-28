# UofA CS Wiki Source

This repository contains the build configuration for the [UofA CS Wiki](https://uofa-cs.github.io/uofa-cs-wiki/) website.

## How it works

- **Content source**: [uofa-cs/uofa-cs-wiki](https://github.com/uofa-cs/uofa-cs-wiki) (pure markdown, human-readable)
- **Build repo**: This repository (contains MkDocs config, GitHub Actions, styling)
- **Output**: GitHub Pages site at [uofa-cs.github.io/uofa-cs-wiki](https://uofa-cs.github.io/uofa-cs-wiki)

## Automatic updates

The site rebuilds automatically:

- **Every 10 minutes**: GitHub Actions checks for new commits in the main wiki repo
- **Manual trigger**: Use the "Actions" tab to trigger a rebuild
- **On config changes**: Pushes to this repo trigger a rebuild

## Local development

```bash
# Install dependencies
pip install mkdocs-material mkdocs-git-revision-date-localized-plugin

# Clone the wiki content
git clone https://github.com/uofa-cs/uofa-cs-wiki.git wiki-content

# Start development server
mkdocs serve

# Build static site
mkdocs build
```

## Architecture

```
uofa-cs-wiki-source/           # This repo (build config)
├── mkdocs.yml                 # MkDocs configuration
├── .github/workflows/         # Auto-sync and deploy
├── overrides/                 # Theme customizations
│   └── stylesheets/
│       └── extra.css          # UofA branding
└── wiki-content/              # Auto-pulled content (gitignored)
```

## Theme

Uses Material for MkDocs with University of Alberta branding:

- **Colors**: UofA Green (#007C41) and Gold (#FFDB05)
- **Features**: Search, dark mode, navigation tabs, code highlighting
- **Responsive**: Works on mobile and desktop

## Contributing

**Content changes**: Edit files in [uofa-cs/uofa-cs-wiki](https://github.com/uofa-cs/uofa-cs-wiki) — changes appear automatically within 10 minutes.

**Site/theme changes**: Edit this repo:
- Update `mkdocs.yml` for navigation or config changes
- Edit `overrides/stylesheets/extra.css` for styling
- Modify `.github/workflows/deploy.yml` for build process changes

## Why separate repos?

1. **Clean content**: Main wiki stays readable markdown without build artifacts
2. **Build complexity**: All MkDocs config, CI/CD, and styling lives here
3. **Automatic sync**: Content updates don't require manual rebuilds
4. **Contributor-friendly**: Writers edit markdown, developers handle builds

The main wiki repository remains accessible to students who just want to read the content on GitHub, while this repo provides the polished website experience.