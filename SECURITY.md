# Security

Quorum is a security tool, so the honest thing is to say how it can be attacked and how to tell us.

## Reporting

Use GitHub's private vulnerability reporting on this repository (Security tab, "Report a vulnerability"). If that route is not enabled when you look, open a plain issue that says only "security report, please enable private reporting" and nothing else; we will enable it and reply there. Please do not put the details in a public issue or a post.

We answer within three days, say what we found within seven, and publish a fix or a written limit in the README's honesty table. The person who reported it is credited if they want to be.

## What is in scope

- The claim registry: any way to make a claim verify that was not paid for, to reuse one fee burn for more than one claim on another swarm's machine, or to make an imported pattern confirm a finding without two local lenses.
- The idiom signature: two lines that should not share a signature but do, so that retiring one silences the other.
- The GitHub action and workflows: any way for a pull request or an input to run code with more than a read-only token, or to write into someone's Security tab something they did not scan.
- The SARIF export: anything in a contract's source that changes what an alert renders as, beyond its own quoted text.
- Reading from the chain or from an explorer: a response that makes `verify`, `import` or `fetch` do something other than refuse.

Findings the lenses miss are not vulnerabilities in Quorum. They are measured in `bench/` and the misses are listed there; a new one is welcome as an issue with the contract attached.

## Known limits, already public

On chain, one fee burn can back more than one claim, because nothing ties a burn to a claim. A memory admits one import per burn, which bounds the damage per victim, but the global fix needs a contract. It is in the README honesty table and on the plan.

## What the tool never holds

The signing key is read from `DEPLOYER_PRIVATE_KEY` at call time and is never logged, printed or written. Memory is a local SQLite file; nothing is uploaded. Scanning, recall and retirement never touch the chain or the token.
