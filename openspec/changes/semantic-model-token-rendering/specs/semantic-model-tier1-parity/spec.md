# Spec Delta

## REMOVED Requirements

### Requirement: The parity suite provably exercises the model path

**Reason**: After `semantic-model-cleanup` there is no feature flag and no legacy path left, so there is nothing to compare against.

**Migration**: None. The semantic-token regression tests run the only remaining path.

### Requirement: Model rendering descends into sub-tokens

**Reason**: It requires the same fragment sequence as the legacy path, which no longer exists. Variables now render differently.

**Migration**: See "Semantic tokens only add what the grammar cannot know" and "Variables get a token for their name only" in `semantic-highlighting`.

### Requirement: Inner keyword calls render as keywords

**Reason**: Its scenario requires output identical to the legacy path.

**Migration**: Carried over without the legacy comparison as "Inner keyword calls of Run Keyword variants render as keywords" in `semantic-highlighting`.

### Requirement: Context modifiers match the legacy path

**Reason**: It defines the modifiers by comparison with the legacy path.

**Migration**: Carried over as "Modifiers come from the analysis" in `semantic-highlighting`.

### Requirement: The model renderer is a declarative mapper

**Reason**: Its scenario requires output identical to the legacy path.

**Migration**: Carried over as "Rendering makes no semantic decisions of its own" in `semantic-highlighting`.

### Requirement: Full-corpus parity with documented exceptions only

**Reason**: There is no legacy path to be in parity with.

**Migration**: The semantic-token regression outputs are the reference. Every change to them is reviewed.
