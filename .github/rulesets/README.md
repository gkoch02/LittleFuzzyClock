# Repository rulesets

`main.json` is the source of truth for the live `Protect main` ruleset.

After changing it, find the live ruleset ID and replace it in place:

```bash
gh api /repos/gkoch02/LittleFuzzyClock/rulesets \
  --jq '.[] | select(.name=="Protect main") | .id'
gh api --method PUT /repos/gkoch02/LittleFuzzyClock/rulesets/<id> \
  --input .github/rulesets/main.json
```

The required status-check contexts must match the unconditional jobs emitted by
`.github/workflows/test.yml`. A context that never reports will block every merge.
