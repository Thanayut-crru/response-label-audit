# A constructive limit on causal-absence inference

Let the observed response be Y = A + B + epsilon. Let V depend only on |A+B|
and independent noise, and let available text/features X have the same law in
both worlds. Consider:

- World 0: A = B = 0.
- World 1: A = g(X), B = -g(X), with g nonzero with positive probability.

Both worlds have exactly the same joint distribution of (X,Y,V). However,
the event max(|A|,|B|) > delta differs. Therefore any rule measurable only with
respect to (X,Y,V), including a low-return/normal-volume labeling rule, has
identical output distributions in the two worlds and cannot identify the
absence of component effects in both without additional assumptions/information.

This does NOT preclude predicting the net response. In both worlds the net
signal is zero; zero is the correct net forecast. A rule targeting NET absence
may be correct while being invalid as a COMPONENT-absence rule. Components in
the simulation are structural latent quantities; calling them real-world causal
effects requires a separate causal model and intervention interpretation.

If text identifies components, or volume responds to gross component activity
rather than net activity, the premise may fail. The result must not be generalized
to all text models, all observables, or all weak-supervision methods. This basic
counterexample supports a diagnostic framework; by itself it is not a claim of
a new general impossibility theorem.
