# Manifest Structural Audit Protocol (2025-12-23)

Apply these instructions to any LLM session to perform a deep-structure audit of the system JSON without biasing the agent with pre-defined solutions.

---

### **AI Audit Prompt**
"Analyze the provided JSON manifest for structural integrity and logical consistency using the following criteria:

1.  **Reference Integrity:** Scan all `steps` and `dependencies`. Flag any string referencing an engine `key` or protocol name that is not defined as a top-level object.
2.  **Dependency Flow:** Verify `stage` logic. Engines in `stage: 2` or higher must only depend on engines from a lower or equal stage. Flag circular dependencies or 'orphaned' engines.
3.  **I/O Handshake:** Cross-reference the `outputs` of listed `dependencies` against the functional requirements of the current engine's `steps`. List any missing data-payload requirements.
4.  **Terminological Consistency:** Identify 'ghost' fragments—legacy terms in `steps` that do not align with current `key` names (e.g., references to 'synthesis' when the engine is named 'orchestrator').
5.  **Hardcoding Audit:** Ensure no `rules` or `steps` contain hardcoded counts of protocols or engine objects. Logic must be count-agnostic.
6.  **Constraint Compliance:**
    * Confirm the total absence of any `"delta"` keys.
    * Verify every object has a `"key"` field identical to its top-level identifier.
    * Ensure the output is a single JSON block following the analysis."

---

```json
{
  "audit-protocol-metadata": {
    "version": "2025.12.23",
    "compliance-mode": "strict",
    "validation-targets": [
      "reference-integrity",
      "dependency-linearization",
      "io-sync",
      "zero-hardcoding"
    ]
  }
}