"""
One-time production data bootstrap: `python -m app.bootstrap_production`
(run from the backend/ directory).

Reuses the existing schema init, GTFS importer, and curated-data seed
scripts. Safe to re-run: each agency's import is skipped once it already
has rows, and the curated-scenario seeds always replace-all.

Recovery note: if a run is killed mid-import, an agency can be left with
some but not all GTFS tables populated, and a later run would wrongly treat
it as done since it only checks gtfs_routes -- call
gtfs_repository.delete_agency_data(agency_source) for that agency and re-run.
"""

from app.config import get_cta_gtfs_zip_path, get_dart_gtfs_zip_path
from app.database import DB_PATH, init_db
from app.repositories import gtfs_repository, route_repository
from scripts.import_gtfs import import_gtfs
from scripts.seed_db import seed as seed_curated_scenarios
from scripts.seed_scenario_gtfs_links import seed as seed_scenario_gtfs_links

# Maps each agency this app knows about to the config getter for its local
# GTFS zip path. Add an entry here (and a matching env var) to bootstrap a
# third agency later -- no other code in this file is agency-specific.
AGENCY_ZIP_PATH_GETTERS = {
    "CTA": get_cta_gtfs_zip_path,
    "DART": get_dart_gtfs_zip_path,
}


def _agency_already_imported(agency_source: str) -> bool:
    return gtfs_repository.count_rows("gtfs_routes", agency_source) > 0


def _bootstrap_agency(agency_source: str) -> None:
    if _agency_already_imported(agency_source):
        print(f"{agency_source} GTFS already imported, skipping.")
        return

    env_var = f"GTFS_{agency_source}_ZIP_PATH"
    zip_path = AGENCY_ZIP_PATH_GETTERS[agency_source]()

    if zip_path is None:
        raise SystemExit(
            f"{env_var} is not set and no {agency_source} GTFS data exists yet. "
            f"Set {env_var} to a local static GTFS zip and re-run."
        )
    if not zip_path.exists():
        raise SystemExit(f"{env_var} points to {zip_path}, which does not exist.")

    print(f"Importing {agency_source} GTFS from {zip_path} ...")
    import_gtfs(agency_source, zip_path)


def _verify_ready() -> None:
    """Refuses to report success with a half-bootstrapped database."""
    if len(route_repository.list_routes()) == 0:
        raise SystemExit("Bootstrap finished but trip_scenarios is empty.")
    for agency_source in AGENCY_ZIP_PATH_GETTERS:
        if not _agency_already_imported(agency_source):
            raise SystemExit(f"Bootstrap finished but {agency_source} has no GTFS routes.")


def main() -> None:
    print(f"Bootstrapping database at {DB_PATH}")
    init_db()

    for agency_source in AGENCY_ZIP_PATH_GETTERS:
        _bootstrap_agency(agency_source)

    print("Seeding curated trip scenarios...")
    seed_curated_scenarios()

    print("Seeding scenario <-> GTFS route links...")
    seed_scenario_gtfs_links()

    _verify_ready()
    print(f"Database ready at {DB_PATH}")


if __name__ == "__main__":
    main()
