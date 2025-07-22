# 🔁 FLOWS README

Flows are composed YAML sequences of skill invocations.

Example:

```yaml
name: summarize_then_tweet
steps:
  - skill: summarize
  - skill: write_tweet
```

Each flow should live in `flows/` or `modules/*/flows/`.
