# Known limitations

- Kaggle dataset is a historical catalog snapshot; no timestamped series or live Google Play data is included.
- Installs are coarse lower-bound bands, not exact counts or precise market shares.
- Listing presence, ratings, reviews, and install bands do not measure retention, revenue, acquisition costs, unmet needs, or future success.
- Ratings and reviews have missingness and selection effects; average ratings omit uncertainty and may not reflect current satisfaction.
- Duplicate names may represent distinct products; retained rows may include source duplicates pending record-level investigation.
- Category scoring is relative, weight-sensitive, and heuristic. Feasibility is neutral pending independent engineering estimates.
- Kaggle access can require user authentication. Credentials must remain local and must never be committed.
- Windows App Control initially blocked a native extension in the newest Pandas wheel; Pandas 2.3.3 imports after reinstall and pytz installation. Avoid altering security policy.
- The downloaded `license.txt` specifies CC BY 3.0 Unported, conflicting with the brief's CC BY-SA 4.0 statement; current Kaggle listing terms must be confirmed before redistribution.
- No GitHub remote or deployment has been configured.
