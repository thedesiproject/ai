
# PROTOCOL INSTRUCTIONS

## CORE DEFINITIONS & FORMAT
* **Format:** $\{"key": "...", "stage": X, "steps": [...], "dependencies": ["..."], ...\}$
* **Goal:** Minimal size, concise machine-English.
* **Content:** Protocol files contain **key, stage, steps** (required) and optionally **dependencies, config, metadata, rules, tags**.
* **Naming:** All protocol **values** (key, dependencies) must be **kebab-case**. Steps allow flexible syntax.
* **Output:** $\text{Raw JSON only}$, in a **code block**. Field names unchanged. No compactification.
* **System-Rules Location:** All global configuration, safety rules, or framework control logic must be stored in the separate `system-rules` file, never inside protocols.

## SCHEMA VALIDATION
* **Load:** `config/protocol-schema.json` when creating new protocols.
* **Validate:** Field names, stage numbers (0-5), kebab-case naming in key and dependencies.
* **No Extra Metadata:** Fields outside the allowed schema MUST trigger Fast-Reject (e.g., `summary`, `description`, `notes`, `rationale`, `comment`, `examples`, etc.).

## STAGES & FLOW RULES
* **Stages:** $\text{Stage 0}$ (system/init) $\rightarrow$ $\text{Stage 1}$ (extraction/validation) $\rightarrow$ $\text{Stage 2}$ (analysis) $\rightarrow$ $\text{Stage 3}$ (synthesis) $\rightarrow$ $\text{Stage 4}$ (formatting) $\rightarrow$ $\text{Stage 5}$ (governance).
* **Stage Rule:** $\text{Protocol's stage} \geq \text{Max dependency stage}$.
* **Dependencies:** Must be **minimal**; add **only** when execution order requires them.
* **Structure:** $\text{AUDIT/QUALITY}$ must remain distinct. $\text{Synthesis}$ (combining analysis) must be in **Stage 3**.
* **Stage 3 Boundary:** Stage 3 protocols must focus exclusively on verification, quality assurance, synthesis, and confidence assessment. They **MUST NOT** include any final output formatting or I/O delivery logic (which belongs to Stage 4).
* **Stage 4 Boundary:** Stage 4 is strictly limited to output formatting, message construction, and I/O assembly. No reasoning, no synthesis, no validation, and no new analysis steps are allowed.
* **Stage 5 Boundary:** Stage 5 is reserved exclusively for governance, evolutionary monitoring, and framework audit. It cannot execute, modify, or interact with data flowing through Stages 1–4.
    * Stage 5 may request structural changes but cannot directly apply them; it must issue proposals consumed by Stage 0.
* **Governance Protocol Constraint:** Protocols tagged with `config: {type: "governance"}` must be restricted to Stage 0 or Stage 5, and are **forbidden** from modifying data-flow, reasoning logic (Stage 1-3), or output formatting/I/O logic (Stage 4).
* **Anti-Circularity:** Circular dependencies (A requires B which requires A) are an **automatic Fast-Reject violation**.

## STEP & CONTENT GUIDANCE
* **Step Minimalism:** Merge steps if semantics are identical. Split **only** for failure isolation/logging.
* **No-Silent-Reduction:** LLM must **NEVER** remove, shrink, or merge any key or step unless explicitly justified using the Divergence Hierarchy. Any reduction without explicit reasoning is a **Fast-Reject** violation.
* **Skip-Guard:** Omit step **only if** zero functional value. **Keep step if in doubt.**
* **Step Expansion Rule:** LLMs may add new steps only when needed to restore correctness or completeness, and must justify them under the Divergence Hierarchy.
* **Efficiency Definition:** Efficiency = **step-level compression** (2-5 tokens), **NOT** protocol consolidation. Protocol count/structure is non-negotiable for auditability.
* **Optional Pattern:** Use $\text{ingest-validate}, \text{normalize-clean}, \text{core-*}, \text{verify-idempotency}, \text{store-*-metadata}$ when helpful.
* **Governance Config Rule:** The `config: {type: "governance"}` tag is reserved **only** for framework-managing or evolutionary protocols (i.e., those subject to the Governance Protocol Constraint).
* **New Protocols:** Propose **only** when existing ones can't fit the functionality.
* **Rule Precedence:** Rules defined in the global `system-rules.json` file **ALWAYS** override any conflicting rules or instructions defined locally within a protocol's optional `rules` field.

## LLM CONVERGENCE & ARBITRATION (Final)
* **Semantic Convergence:** Must agree on $\text{keys}$, $\text{stages}$, $\text{dependencies}$, and $\text{steps}$. Step order does not matter unless it encodes a logic sequence.
* **Semantic-Equivalence Rule:**  Two steps/keys count as converged **only if their functional scope is identical**, not merely similar.  When equivalence is confirmed, the shorter token MUST be selected **only if it remains unambiguous and audit-safe** (no loss of meaning).  Models must explicitly justify semantic equivalence; otherwise tokens are considered distinct.
* **Key-Renaming Rule:** LLMs may propose renaming a key only when: 1. The new name is strictly more minimal and unambiguous, 2. Semantic equivalence is proven, 3. All dependent protocols are updated consistently. Silent renaming is forbidden. 4. Renaming must not create a stage violation; all updated dependencies must still comply with the Stage Rule.
* **Divergence Hierarchy:** Resolve based on: **Correctness** $\rightarrow$ **Completeness** $\rightarrow$ **Minimalism** $\rightarrow$ **Consistency}$.
* **Fast-Reject:** Reject immediately for **wrong field names**, **unauthorized fields (schema/metadata)**, **stage violations**, **mixed naming**, **non-existent dependencies**, **duplicates**, or **unjustified config/rules**.
* **Uncertainty:** State assumption and ask for clarification.
* **Defensive Steps:** Extra defensive steps (improving robustness but seeming redundant) are **not** considered waste and should be kept.
* **Regression Protection:** Once 66%+ multi-LLM agreement on structure is achieved, that structure is **FROZEN**. Reversion to previously-rejected structures (e.g., merging Stage 2 engines) is an automatic **Fast-Reject** violation.
* **Minimalism Enforcement:** The governance concept of eliminating redundant keys or steps is a core **Fast-Reject** requirement. All functional redundancy must be removed immediately using the Semantic-Equivalence Rule.

## FLOW RULES & STRUCTURE
* **Core Analytical Layer Structure:** Protocols responsible for core analysis functions must be structurally distinct for auditability:
    1.  `hypothesis-generation-testing-bayesian` (Hypothesis/Probabilistic Analysis)
    2.  `causal-inference-dag-reasoning` (Causal Analysis)
    3.  `cognitive-bias-detection-mitigation` (Contextual/Bias/Uncertainty Audit)
* **Structural Isolation:** These core analytical protocols must **NOT** be unified into a single engine.

---

## OPERATIONAL RULES (System Behavior)
* **Proactive Decision:** Identify divergence type immediately; apply $\text{Divergence Hierarchy}$ without waiting for clarification.
* **Coordination:** When LLM observes divergence, generate feedback. For multi-LLM consensus, merge toward that consensus unless a $\text{Fast-Reject}$ violation occurs.
* **Merging Heuristics:** $\text{Stage 0}$ protocols stay separate. $\text{Stage 1}$ merges if isolated domain. $\text{Stage 2}$ merges if domain is identical and isolation is not mandatory. $\text{Stage 3}$ merges if dependencies overlap significantly.
* **Iteration Limits:** Allow refinement through $\text{Iteration 3}$. Declare convergence $\text{good enough}$ at $\text{Iteration 4+}$, or escalate to user after $\text{Iteration 5+}$ with clear reasoning.

## MULTI-LLM CONVERGENCE (When Using Multiple LLMs)
* **LLM Iteration Window:** Before judging a model as non-convergent, allow a **minimum of 2 return-iterations** for it to ingest and adjust to other LLM outputs. Early divergence is not grounds for penalty.
* **Fairness Enforcement:** A **minimum of 2 return-iterations** must pass before a model may judge another model as divergent, incorrect, or unstable. No convergence judgment or criticism is allowed until this two-iteration fairness window has passed.
* **Agreement Check:** If all LLMs propose same $\text{key}$, $\text{stage}$, $\text{steps}$ → convergence achieved.
* **Disagreement Resolution:** Apply $\text{Divergence Hierarchy}$ to each differing element. If hierarchy produces tie, use **Correctness** tiebreaker (does it pass Fast-Reject?).
* **Confidence:** Report convergence % (e.g., "2/3 LLMs agree on stage, 3/3 agree on steps").
* **Convergence Messaging Rule:** Convergence reports must be **≤3 sentences**: (1) convergence %, (2) which LLM is lagging after the 2-iteration window, (3) optional ≤1-sentence advisory message if strongly warranted.
* **Escalation:** If after Iteration 3 you have < 66% agreement, escalate to user with each LLM's reasoning.

