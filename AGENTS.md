# JUCE Agent Reference — Agent Execution Protocol

## 1. Mission

Your mission is to fully implement JUCE Agent Reference V1 as defined by:

1. `plan.md`
2. `implementation.md`

This is an implementation task, not a planning or advisory task.

You must create the source code, tests, fixtures, command-line tools, scripts, documentation, indexes, validation system, and publishing workflow required by the specifications.

Do not stop after creating a project skeleton, partial parser, demonstration implementation, or progress report.

The goal is complete only when all V1 requirements pass automated verification.

------

## 2. Document authority

The project documents have different areas of authority.

### `AGENTS.md`

Controls:

- execution workflow
- unattended operation
- progress persistence
- failure recovery
- Git behavior
- stopping conditions
- final completion reporting

### `plan.md`

Controls:

- project goals
- architecture
- V1 scope
- exclusions
- design principles
- Definition of Done

### `implementation.md`

Controls:

- modules
- interfaces
- data models
- implementation order
- commands
- tests
- validation details
- commit structure

When documents appear to conflict:

1. Use `plan.md` for architecture, scope, and acceptance requirements.
2. Use `implementation.md` for concrete implementation details.
3. Use `AGENTS.md` for execution, recovery, and stopping behavior.
4. Prefer an implementation that satisfies all three documents.
5. Do not weaken a requirement to resolve a conflict.
6. Only treat the conflict as an external blocker when the requirements are genuinely impossible to satisfy simultaneously.

Do not modify the core requirements in these documents merely to make implementation easier.

------

## 3. Required startup procedure

At the beginning of every execution or resumed execution:

1. Read this entire `AGENTS.md`.
2. Read the entire `plan.md`.
3. Read the entire `implementation.md`.
4. Inspect the Git log.
5. Inspect the Git working tree.
6. Read `.agent/progress.json`.
7. Check whether `.agent/blocker.json` exists.
8. Verify that progress state agrees with the repository and test results.
9. Run the environment doctor or bootstrap procedure.
10. Resume from the last verified implementation state.

Do not create another high-level implementation plan instead of beginning work.

You may maintain a short internal task list, but implementation must start immediately after the required repository and environment inspection.

------

## 4. Execution objective

Complete all implementation phases in `implementation.md`.

The required phases are:

1. Repository and execution framework
2. JUCE input and Doxygen generation
3. Canonical IR and XML parser
4. Path mapping and Markdown rendering
5. Symbol indexes and search
6. Official examples and source locations
7. Validation and atomic publishing
8. Unattended final verification

Complete the phases in order unless a narrowly scoped dependency requires preparatory work from a later phase.

Do not declare the overall goal complete after finishing an individual phase.

------

## 5. Definition of completion

The project is complete only when all of the following are true:

- Every implementation phase is complete.
- Every V1 Definition of Done item in `plan.md` is satisfied.
- Every Definition of Done item has machine-verifiable coverage.
- Unit tests pass.
- Integration tests pass.
- Real JUCE smoke tests pass.
- Ruff passes.
- Mypy passes.
- Markdown validation passes.
- Internal-link and anchor validation passes.
- Symbol and relationship index validation passes.
- Example index validation passes.
- Source-location validation passes.
- Search-quality tests pass.
- Determinism tests pass.
- Version verification passes.
- Atomic publishing tests pass.
- The final unified verification command returns exit code `0`.
- The goal-check script returns exit code `0`.
- `.agent/progress.json` contains `"completed": true`.
- `.agent/blocker.json` does not exist.
- The Git working tree is clean.
- There are no unexplained skipped tests.
- There are no core-path TODOs, placeholders, empty implementations, or `pass` statements.
- No mandatory V1 requirement has been reclassified as future work.

Passing only fixture-based tests is not sufficient. The real JUCE checkout must also pass the required smoke and generation tests.

------

## 6. Required execution behavior

You are authorized to:

- create and modify files in this repository
- create the Python package
- install project-local dependencies
- create and use a virtual environment
- run Git read commands
- create local Git commits
- execute Doxygen
- inspect generated XML
- inspect the configured JUCE checkout
- read JUCE source files and examples
- run tests repeatedly
- create regression fixtures
- refactor internal modules
- generate temporary build artifacts
- update project documentation
- update `.agent/progress.json`
- delete obsolete files created by your own implementation

You must not:

- modify the JUCE checkout
- commit the JUCE checkout
- automatically push commits
- force-push
- rewrite remote history
- change remote branches
- delete user-authored commits
- install administrator-level software without permission
- change operating-system security settings
- upload private source code to external services
- enable network crawling of JUCE documentation
- introduce an LLM API dependency
- weaken tests or acceptance requirements

------

## 7. Progress persistence

Maintain:

```text
.agent/progress.json
```

It must conform to the schema defined in `implementation.md`.

Update it when:

- beginning a phase
- completing a phase
- creating a verified phase commit
- encountering a command failure
- resolving a failure
- changing the next action
- beginning final verification
- completing the entire goal

At minimum, record:

- current phase
- completed phases
- last verified commit
- last successful command
- current failure
- next action
- completion state

Write progress updates atomically.

Do not rely solely on conversation context or memory. The repository is the persistent execution state.

When the progress file conflicts with the repository:

1. Treat Git state and actual test results as authoritative.
2. Repair the progress file.
3. Continue from the verified state.

------

## 8. Failure-recovery loop

Ordinary implementation failures must be handled autonomously.

For every ordinary failure:

1. Capture the exact command.
2. Capture complete stdout and stderr.
3. Update `progress.current_failure`.
4. Reduce the failure to the smallest reproducible case.
5. Add or update a regression test or fixture.
6. Correct the implementation.
7. Run the narrowest relevant test.
8. Run the current phase test suite.
9. Clear the failure state.
10. Update the next action.
11. Continue execution.

Examples of ordinary failures include:

- test failures
- lint failures
- type-checking failures
- unsupported Doxygen XML nodes
- invalid Markdown links
- missing anchors
- Windows path conflicts
- output ordering differences
- search-ranking failures
- malformed fixture data
- Doxygen warnings caused by project handling
- parser or renderer bugs
- incorrect source locations
- incomplete example associations
- deterministic-output mismatches
- atomic-publishing bugs

These failures are not reasons to ask the user for implementation decisions.

------

## 9. New Doxygen XML nodes

When real JUCE XML contains an unsupported node:

1. Identify the compound and member containing it.
2. Preserve the smallest representative XML fragment as a fixture.
3. Add a failing regression test.
4. Determine whether the node is semantic or presentational.
5. Extend the canonical IR when necessary.
6. Extend the parser.
7. Extend the Markdown renderer or indexer.
8. Verify that no official semantic information is lost.
9. Run parser and renderer regression tests.
10. Resume the real JUCE generation.

Do not:

- discard the node silently
- replace structural parsing with unconditional `itertext()`
- downgrade semantic loss to a warning
- ask the user how an ordinary Doxygen construct should be handled
- remove the affected API from output to make validation pass

------

## 10. Testing rules

Every bug fix must include a regression test when reasonably possible.

Tests must not be weakened to match an incorrect implementation.

Do not:

- mark a failing mandatory test as skipped
- delete a difficult acceptance test
- lower search Top-K requirements
- replace real JUCE smoke tests with fixtures
- replace integration tests with mocked success
- catch and ignore unexpected exceptions
- convert semantic errors into warnings
- use empty documents to satisfy validators
- use fake symbols or paths in final smoke tests

Tests should be deterministic and independent of network access wherever possible.

Temporary generated JUCE XML and output should remain outside committed source unless a small fixture is specifically required for a regression test.

------

## 11. Scope control

Implement all V1 requirements.

Do not expand V1 to include:

- JUCE tutorial website crawling
- `docs.juce.com` HTML scraping
- JUCE forum ingestion
- vector databases
- embeddings
- MCP servers
- HTTP servers
- web interfaces
- Clang-based full-project indexing
- Tree-sitter full semantic indexing
- deep `JUCE/extras` analysis
- AI-generated summaries
- AI-generated examples
- translation
- multi-version JUCE hosting

Provider interfaces may be added only when they simplify the current implementation and do not leave required V1 behavior incomplete.

Avoid speculative abstractions with no V1 caller.

------

## 12. Architectural invariants

The following decisions are fixed:

- The JUCE checkout is the version source of truth.
- The full JUCE commit SHA identifies a document release.
- JUCE API HTML pages are not crawled.
- The official JUCE Doxyfile is not modified in place.
- Doxygen configuration changes use an overlay.
- `XML_PROGRAMLISTING = NO`.
- Doxygen XML is validated before conversion.
- XML is converted into a canonical IR before Markdown rendering.
- Main types receive individual Markdown pages.
- Members remain on their owning type page.
- Member anchors are explicit and stable.
- Documentation code snippets are preserved.
- Complete source files are not copied into API Markdown.
- Official examples remain source files and receive indexes and navigation.
- Source definition locations are never guessed.
- Plain-text indexes remain usable without SQLite.
- SQLite FTS5 is a rebuildable cache.
- Internal unresolved references fail the build.
- Formal releases are atomically published.
- Dirty JUCE builds cannot replace the stable current release.

Do not change these invariants without explicit user authorization.

------

## 13. Git protocol

Create at least one local commit for each implementation phase.

Each commit must:

- have a focused scope
- include relevant tests
- pass the current phase verification
- exclude temporary build artifacts
- exclude the JUCE checkout
- exclude full generated Doxygen XML
- exclude local environment secrets
- leave the repository in a coherent state

Recommended commit sequence:

```text
chore: initialize JUCE reference generator
feat: validate JUCE checkout and generate Doxygen XML
feat: parse Doxygen XML into canonical model
feat: render linked JUCE Markdown reference
feat: build deterministic symbol and search indexes
feat: index JUCE examples and source locations
feat: validate and atomically publish references
feat: add unattended final verification workflow
```

The exact number of commits may be larger when meaningful, but do not combine unrelated phases into one unreviewable commit.

Do not push commits automatically.

At final completion:

```text
git status --porcelain
```

must produce no output.

------

## 14. Blocker policy

Only an unrecoverable external condition may stop execution before completion.

Permitted blockers are limited to:

1. The configured JUCE checkout does not exist.
2. The checkout is not a usable JUCE repository.
3. A required executable is absent and cannot be installed with current permissions.
4. A required action needs administrator privileges that are unavailable.
5. Required dependencies cannot be obtained because network access is unavailable and no cache exists.
6. The repository or output filesystem is not writable.
7. Disk space or memory is insufficient and cannot be recovered.
8. A security policy explicitly prevents a mandatory operation.
9. `plan.md` and `implementation.md` contain genuinely irreconcilable mandatory requirements.

The following are not blockers:

- implementation complexity
- multiple test failures
- unfamiliar Doxygen nodes
- a need for refactoring
- slow full-JUCE generation
- poor initial search ranking
- platform-specific bugs
- Doxygen warnings
- a failing determinism test
- incomplete example associations
- uncertainty that can be resolved from JUCE source, Doxygen XML, tests, or documentation

------

## 15. Blocker reporting

When and only when a permitted blocker is reached, create:

```text
.agent/blocker.json
```

It must include:

- schema version
- phase
- failing command
- complete error summary
- diagnostic evidence
- attempted recovery actions
- completed phases
- last verified commit
- exact external action required to resume

Before stopping:

1. Commit all coherent verified work when safe.
2. Ensure the working tree does not contain unrelated half-written changes.
3. Update `.agent/progress.json`.
4. Write `.agent/blocker.json`.
5. Provide a concise blocker report.

Once the blocker is resolved:

1. Delete `.agent/blocker.json`.
2. Run the relevant doctor check.
3. Resume from the stored state.

------

## 16. Machine verification

The final implementation must expose the unified verification command defined in `implementation.md`.

Its semantic sequence must include:

```text
doctor
→ unit tests
→ integration tests
→ lint
→ type checking
→ real JUCE generation
→ generated-output validation
→ real JUCE smoke tests
→ search-quality tests
→ determinism tests
→ version verification
→ Git cleanliness check
→ progress completion check
→ blocker absence check
```

The expected final entry point is:

```text
juce-doc all
```

The accompanying goal-check script must also pass.

Do not manually mark the goal complete when either command fails.

------

## 17. Definition of Done mapping

Maintain a machine-readable mapping from each mandatory `plan.md` Definition of Done requirement to one or more:

- unit tests
- integration tests
- smoke checks
- validation commands
- final verification checks

The expected file is:

```text
tests/definition-of-done.yml
```

Every mandatory V1 requirement must appear in this mapping.

The unified final verifier must reject:

- missing Definition of Done entries
- entries with no verification mechanism
- references to nonexistent tests or commands
- mandatory checks marked informational only

------

## 18. Documentation requirements

Before final completion, ensure:

### `README.md`

Explains:

- project purpose
- supported Python version
- Doxygen requirement
- JUCE checkout requirement
- bootstrap procedure
- generation command
- query commands
- verification command
- output structure
- known V1 exclusions

### Generated reference `AGENTS.md`

Explains to downstream coding Agents:

- exact-symbol lookup first
- concept search second
- official examples next
- source inspection when necessary
- version verification
- prohibition on inventing absent JUCE APIs

### CLI help

Every public command must have useful:

- description
- parameter help
- exit behavior
- JSON-mode behavior where applicable

Do not claim unsupported features in documentation.

------

## 19. Final verification procedure

After implementation:

1. Run the complete unified verification command.
2. Run the goal-check script.
3. Inspect `.agent/progress.json`.
4. Confirm `.agent/blocker.json` is absent.
5. Confirm the Git working tree is clean.
6. Confirm all phase commits exist.
7. Confirm the generated release matches the configured JUCE commit.
8. Confirm the final report contains no unmet V1 requirement.
9. Mark progress complete only after every preceding step passes.

Do not set:

```json
"completed": true
```

before final verification succeeds.

------

## 20. Final report

When the goal is complete, report:

- overall result
- JUCE commit
- JUCE dirty state
- Python version
- Doxygen version
- generator version
- all completed phases
- local commit list
- test counts
- lint result
- type-check result
- smoke-test result
- search-quality result
- determinism result
- verification result
- generated release location
- document count
- symbol count
- example count
- known non-blocking V1 exclusions
- Git cleanliness
- blocker absence
- progress completion state

Only limitations explicitly outside V1 may be listed as non-blocking.

An unmet V1 requirement must be reported as failure, not as a limitation.

------

## 21. Completion rule

You may declare JUCE Agent Reference V1 complete only when:

```text
juce-doc all returns 0
AND
goal-check returns 0
AND
progress.completed is true
AND
blocker.json does not exist
AND
the Git working tree is clean
AND
every mandatory V1 Definition of Done item is verified
```

Until then, continue implementing, testing, debugging, and committing.

Do not stop merely because substantial progress has been made.