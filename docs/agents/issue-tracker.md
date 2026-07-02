# Issue tracker: Local Markdown

Issues and PRDs for this repo live as markdown files in `.scratch/brainfusion-agents/`.

## Conventions

- The PRD is `.scratch/brainfusion-agents/PRD.md`.
- Implementation issues are `.scratch/brainfusion-agents/issues/<NN>-<slug>.md`, numbered from `01`.
- Triage state is recorded in both frontmatter (`status`) and a `Status:` line near the top of each issue file.
- Comments and conversation history append to the bottom of the file under a `## Comments` heading.

## When a skill says "publish to the issue tracker"

Create a new markdown file under `.scratch/brainfusion-agents/` or `.scratch/brainfusion-agents/issues/`.

## When a skill says "fetch the relevant ticket"

Read the referenced file path directly. If the user gives an issue number, map it to `.scratch/brainfusion-agents/issues/<NN>-*.md`.

