# AI Developer Memory: Conda Setup and Path Rules

## 1. Context
During the initial setup of the AOI System project, standard Python virtual environments (`venv`) created within WSL mapping caused Windows git client indexing errors during `git add .` due to symlink compatibility issues. In addition, the developer requested environment management using Anaconda/Miniconda to ensure cross-platform compatibility between Windows and Ubuntu.

## 2. Issues Encountered & Resolved
- **Git Indexing Failure:** Sourcing and committing absolute/virtual environments causes file-not-found errors on hosts.
  * *Resolution:* Excluded all `.venv/` and `.conda/` temporary paths in `.gitignore`.
- **Absolute Paths in Build files:** An absolute path `/include` was configured in `core/native/CMakeLists.txt`.
  * *Resolution:* Replaced with `${CMAKE_CURRENT_SOURCE_DIR}/include`.
- **Environment Incompatibility:** Python standard `venv` has symlink differences between WSL and Windows.
  * *Resolution:* Refactored setup, build, test, and run scripts to utilize Conda environment management under a unified environment name `aoi-app` using `conda run -n aoi-app`.

## 3. Key Rules Added
- **Relative Path Constraint:** Absolute paths (e.g. `/home/...`, `C:\...`) are forbidden to maintain project portability.
- **Vietnamese Companion Constraint:** Every `.md` documentation file created or updated must contain a companion `.md.vn` translation in Vietnamese.
- **AI Experience Memory:** Critical notes or bugs must be documented inside `.agents/experience/` as `memory.md` and `memory.md.vn`.