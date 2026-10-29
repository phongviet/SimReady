# M5 experiment tracker

Protocol frozen before blind-image evaluation.

|Stage|Runs|Status|Gate|
|---|---:|---|---|
|Read guards + curator|CPU|DONE|No candidate/test pixels in learner before seals|
|Base/calibration|3|DONE|50train;8fit/8check validation|
|Seal acquisition|9|DONE|K4 risk/random/farthest per seed|
|Fresh equal-budget arms|9|DONE|54frames;1200steps;common blind test|
|E1/E2/E4 analysis|all|TODO|Paired outputs, blocks, failure scope|

Actual study: `experiments/tum-recapture-1`, clean source6947fb8. All45pipeline
stages completed with zero recorded failures. Integrity audit and analysis remain
pending; no superiority or detection-accuracy finding is asserted here.
