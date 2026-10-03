# Retrospective methodological protocol

## Claims and estimands

R1: In the specified simulation, how often does a retained low-response label
hide a component exceeding a fixed meaningful-effect threshold?
R2: How does that error change with cancellation, observation noise, missingness,
stale responses, anticipation, and regime change?
R3: On the available retrospective stock-day panel, what range of incremental
forecasting benefit is compatible with the data?

No claim that emerging markets have no predictive signal is permitted. No claim
about semantic teacher ensembles follows from outcome-derived RDFL experiments.
Absence of net effect and absence of component effects are distinct estimands.

## Existing evidence

The original 0.9855 is a confidence-weighted, soft-low-response-weighted fraction
on selected TRAINING examples, averaged across legacy replications. It is not
the fraction of all market events and not held-out causal-classification accuracy.
Its component threshold was 0.35 * SD(training net effect), which shrinks under
cancellation. The new study reports fixed thresholds 0.2, 0.35, 0.5 in units of
the population SD of the first component, plus the legacy-style net-SD threshold.
Also report population component prevalence, label coverage, soft weight mass,
hard-low-response count, and false net-low-response labels. This checks whether
high error mostly reflects a world in which almost every case has a component.

## Simulation

100 independent seeds per scenario; 2,400 training and 1,200 test observations.
20 independent standard normal features. The first component is linear with
known population variance one; no scaling uses test data. The second component
is -c times the first plus an independent feature component when c > 0.
Net effect is the sum. Observed outcome adds independent noise and an explicit
response multiplier. Volume depends on net magnitude under the primary DGP.
These are stylized assumptions, not a calibrated model of the Thai market.

Scenarios: null; strong signal; high noise; cancellation c=0.5,0.85,1.0;
anticipation; stale price; informative training missingness; test regime shift.
An exact observational-equivalence demonstration holds observations fixed under
zero components versus equal and opposite components. It is a constructive
identifiability example, not an estimate of real-world cancellation prevalence.

Learners: ZERO, DIRECT ridge, HARD_RDFL, ORDINARY_SOFT, RDFL_SOFT, and an oracle
ridge trained on latent net effects. All fit on training only and use a common
test set. The label/classifier functions are snapshotted from P3 for traceability.
The oracle is a diagnostic using forbidden real-world information. The strong
signal direct learner must recover the planted signal; failure invalidates the
pipeline. Do not select only scenarios where RDFL loses.

Primary simulation outcome: held-out latent net-effect MSE. Secondary: observed
outcome MSE, weighted component-absence error and fixed-threshold sensitivity.
Primary contrasts: DIRECT minus RDFL and ZERO minus RDFL in each scenario.
Positive differences favor RDFL. Paired bootstrap unit is a complete simulation
replication; Holm correction spans all scenario/primary-comparator tests.
All diagnostics must report denominator and selection rules.

## Empirical rerun

Use existing P1 forward-generated labels and observed open-to-close stock return
targets. These are NOT verified abnormal returns or CAR. Character TF-IDF is
fitted within each expanding training fold. Remove five globally observed valid
sessions preceding each test block, then remove training bags sharing an exact
normalized text fingerprint with test articles (across stocks/sources). Test
labels/outcomes are never used to fit. This retrospective duplicate exclusion
establishes an exact-overlap-clean subset, not a deployed event detector.
Near duplicates and event identity remain unresolved. The observed session
calendar is provisional; it must not be called an official calendar.
Five fixed estimator seeds are averaged; they are not independent replicates.
Compare ZERO, DIRECT_HUBER, HARD_RDFL, ORDINARY_SOFT, RDFL_SOFT on identical bags.
No new transformer tuning and no use of legacy random-split PhaFin results.

## Empirical uncertainty

Use equal-date mean normalized squared errors, averaging stocks within each date.
Preserve cross-stock dependence by resampling complete dates in circular moving
blocks. Block lengths 10,20,40; 20 is primary. 10,000 bootstrap draws; resample
paired losses together. Relative improvement = 1 - mean(RDFL loss)/mean(baseline
loss). Ratio of means, not mean of daily ratios. Scale is training-fold stock
return SD; do not label this metric zero-normalized NMSE.

Four primary comparators: ZERO, DIRECT_HUBER, HARD_RDFL, ORDINARY_SOFT. Holm p-values
use centered paired-loss bootstraps, with a separate family for each empirical
dataset. Unadjusted 95% intervals and Bonferroni simultaneous intervals are both
reported. Exploratory equivalence: 90% relative-improvement interval contained
in [-0.02,0.02]; family-adjusted conservative interval is also required for an
across-comparator equivalence claim. This is a CI-based diagnostic, not an exact
finite-sample TOST. Do not equate p>0.05 with equivalence. Include 1%,2%,5% margin
sensitivity, by-stock and by-fold estimates. Previously examined P2c predictions
may be reanalyzed ONLY in a separately labeled historical exploratory table.

## Unresolved work before publication

Resolve source timestamps/availability, official SET calendar, price adjustment
and corporate actions, and near-duplicate events. Validate chronology and audit
label construction independently. Add external replication or narrow the empirical
claim to the eight banks. If claiming multi-teacher failure, run a separate,
temporally valid teacher/distillation experiment with independent evaluation.
Check related work before claiming novelty. Provide simulation code and allowed
data artifacts under their licenses. No guarantee of Q1 acceptance.
