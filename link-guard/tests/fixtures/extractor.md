---
title: Link rot is mostly self-inflicted
slug: link-rot-is-self-inflicted
source: https://example.com/frontmatter
---

The frontmatter above holds a URL. It must not be counted as a link.

[an inline link](https://example.com/inline)

![an image](img/cover.png)

[a reference link][ref]

[ref]: https://example.com/ref

A bare URL on its own line: https://example.com/bare

A URL in `inline code: https://example.com/not-a-link` is not a link.

```text
And neither is one in a fenced block: https://example.com/also-not-a-link
```
