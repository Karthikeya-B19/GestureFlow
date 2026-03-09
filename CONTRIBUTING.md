# Contributing to GestureFlow

Thank you for considering contributing to GestureFlow!

## Development Setup

```bash
git clone https://github.com/Karthikeya-B19/gestureflow.git
cd gestureflow
pip install -e ".[dev]"
pre-commit install
```

## Branching Strategy (Git Flow)

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases only (protected) |
| `develop` | Integration branch for features |
| `feature/*` | Individual features (e.g., `feature/volume-control`) |
| `bugfix/*` | Bug fixes |
| `release/*` | Release preparation (e.g., `release/v1.0.0`) |
| `hotfix/*` | Emergency fixes to main |

## Commit Convention (Conventional Commits)

```
feat(hci): add volume control via rock-on gesture
fix(canvas): resolve brush size not persisting after color change
docs(readme): add gesture reference table
chore(ci): add PyInstaller build step to release workflow
test(controllers): add unit tests for scroll controller cooldown
refactor(core): extract finger extension logic to landmark_utils
```

## Pull Request Process

1. Create a feature branch from `develop`
2. Write tests for new functionality
3. Ensure `black` and `flake8` pass
4. Ensure all tests pass: `pytest tests/ -v`
5. Submit PR against `develop`
6. Await code review

## Code Quality Standards

- **Formatter:** `black` (line length 100)
- **Linter:** `flake8`
- **Type hints:** All public functions must have type annotations
- **Docstrings:** Google-style on all classes and public methods
- **Tests:** pytest, aim for >80% coverage on `core/` and `controllers/`
- **No magic numbers:** All thresholds/constants go in `config.py`
