For our Python projects, when we want **Markdown-based documentation that turns into a clean, navigable site**, we almost always reach for one of these—ranked by how well they fit *our* style and workflows:

---

### **1. MkDocs (default choice)**

**This is the one we usually mean.**

**Why it fits us so well**

* Native **Markdown-first**
* Minimal configuration, fast to stand up
* Excellent for **architecture docs, ADRs, workflows, and specs**
* Plays nicely with GitHub Pages
* Clean sidebar navigation from `mkdocs.yml`

**Typical stack**

```text
docs/
  index.md
  architecture.md
  design.md
  roadmap.md
  api.md
mkdocs.yml
```

**Common theme**

* `mkdocs-material` (this is what gives it the polished look)

**Why I favor it**

* No ceremony
* Docs feel like “living design notes,” not academic papers
* Perfect for systems like Chrona / Petal / Lily where architecture evolves

---

### **2. MkDocs + Material Theme**

This is technically MkDocs, but it deserves its own callout.

**Adds**

* Versioned docs
* Search (excellent)
* Tabs, callouts, diagrams, admonitions
* Dark mode (important, obviously 😌)

**Bonus**

* Mermaid diagrams work cleanly
* Great for CLI + TUI documentation

If we say *“real docs site”*, this is usually what we mean.

---

### **3. Sphinx (only when API docs dominate)**

Still Markdown-capable via **MyST**, but…

**We use it when**

* Auto-generated API reference is the primary goal
* Heavy docstring extraction
* ReadTheDocs style expectations

**Why it’s not our default**

* Heavier mental overhead
* More config
* Feels slower for early-stage system design

I treat Sphinx as **API-first**, not **architecture-first**.

---

### **4. Docusaurus (rare for Python)**

Markdown-based, yes—but…

**Why we usually skip it**

* JS ecosystem overhead
* Better for product docs than dev architecture
* Less natural fit for Python repos

---

### **My recommendation (and what we “usually” mean)**

If you asked this instinctively, the answer is:

> **MkDocs + Material + Markdown**

It aligns perfectly with:

* Spec-Kit style thinking
* Incremental architecture evolution
* CLI/TUI tool documentation
* GitHub-native workflows

If you want, I can:

* Scaffold a **drop-in MkDocs setup**
* Propose a **docs IA** (information architecture)
* Or align it with the CLI/TUI split we were discussing earlier

Just say the word—I’ll make it neat and opinionated 💜
