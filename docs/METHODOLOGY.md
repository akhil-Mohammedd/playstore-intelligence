# Methodology

## Source and scope
Kaggle dataset `lava18/google-play-store-apps`: https://www.kaggle.com/datasets/lava18/google-play-store-apps. Kaggle-provided files include an app catalog and translated user reviews; this application currently analyzes catalog data. The downloaded `license.txt` says Creative Commons Attribution 3.0 Unported (CC BY 3.0), which conflicts with the CC BY-SA 4.0 reference in the initial brief. The Kaggle listing was not textually verifiable in this session. Preserve the included notice and attribution; verify the current Kaggle listing terms before redistribution. Retrieval timestamp records when this project pipeline ran, not when each app observation was collected.

## Cleaning
The raw source is read-only. String fields are trimmed, numeric parsing uses coercion to missing for malformed values, ratings are retained only in [1,5], install bands are represented as numeric lower bounds while source text is preserved, sizes are normalized to MB, and dates are parsed without interpreting them as release dates. Duplicate app names are reported, never automatically dropped based on name alone. Exact duplicate source rows are flagged and retained in the processed audit output, but only the first exact row is eligible for category aggregation. A category that does not match the source category convention (uppercase letters/underscores) is also retained and flagged but excluded from aggregates. Blank/unparseable values are not imputed.

## Metrics
Category total lower-bound installs and median per-app lower bounds are both shown to expose category size effects. Rating coverage is rated rows / category rows. Concentration HHI is calculated from parsed install lower-bound proportions, so it is only approximate. Summary comparisons are descriptive, not causal. No inference intervals or p-values are reported.

## Opportunity screening
Heuristic features are min-max normalized across observed categories: log median lower-bound demand, inverse app count, category mean rating gated by a minimum rated sample, inverse lower-bound install HHI, and neutral 0.5 feasibility. Default weights 30/25/20/15/10 are judgmental research priorities, not trained or validated predictors. Alternative scenarios support sensitivity checks. Product concepts are category research prompts, not inferred unmet needs. Interview, prototype, and willingness-to-pay validation are required.
