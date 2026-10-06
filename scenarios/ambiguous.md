# Ambiguous scenario

**Input:** “Build a shortener with analytics; retention and expiry are unclear.”

The requirements agent explicitly records unresolved decisions instead of silently inventing policy. The workflow can continue for low-risk planning, but release/high-impact execution requires human approval. After approval, the same stateful context resumes. If the requirement changes, `/replan` invalidates affected downstream stages and increments the context version.
