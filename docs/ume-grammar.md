# Universal Machine English (UME) Grammar

## BNF Specification for LLM Instructions

```
<instruction> ::= <context> <operation> <specification> <validation>

<context> ::= "Context:" <scope> | ""

<operation> ::= <verb> ":" <object>
            | <verb> "→" <object>

<verb> ::= "Read" | "Parse" | "Analyze" | "Extract" | "Generate"
         | "Validate" | "Transform" | "Synthesize" | "Compare"
         | "Set" | "Define" | "Establish" | "Identify"

<object> ::= <noun_phrase> | <description>

<specification> ::= "Input:" <input_type>
                  | "Output:" <output_type>
                  | "Process:" <steps>
                  | "Rules:" <constraints>

<steps> ::= <step> | <step> "→" <steps>

<step> ::= <number> "." <action>

<validation> ::= "Verify:" <checks>
               | "Success:" <criteria>
               | "Enforce:" <requirements>

<checks> ::= <check> | <check> "," <checks>

<number> ::= "1" | "2" | "3" | ... | "N"

<action> ::= <verb> <object>
```

## Core UME Vocabulary (Top 20 Terms)

1. **Read** - Receive/intake information
2. **Parse** - Extract structure from information
3. **Analyze** - Break down and examine
4. **Extract** - Pull specific elements
5. **Generate** - Create new content
6. **Validate** - Check against criteria
7. **Transform** - Change format/structure
8. **Synthesize** - Combine elements into whole
9. **Compare** - Identify differences/similarities
10. **Track** - Monitor and record
11. **Set** - Establish initial state
12. **Define** - Specify meaning/scope
13. **Identify** - Recognize and name
14. **Enforce** - Ensure compliance
15. **Output** - Return result
16. **Input** - Accept data
17. **Process** - Execute sequence
18. **Verify** - Confirm correctness
19. **Check** - Test for specific condition
20. **Rule** - Define constraint/requirement

## UME Protocol Template

```json
{
  "key": "protocol-name",
  "level": 0,
  "groups": ["group-name"],
  "steps": [
    "Read: {input description}",
    "Parse: {structure extraction}",
    "Analyze: {breakdown}",
    "Extract: {specific elements}",
    "Validate: {against criteria}",
    "Synthesize: {combine results}",
    "Output: {result format}"
  ],
  "required_outputs": [
    "output_field_1",
    "output_field_2",
    "verification_status"
  ],
  "context_only": ["output_field_1"],
  "log_only": ["output_field_2"]
}
```

## UME Instruction Examples

```
"Read: incoming request → Parse: extract components → Analyze: dependencies → Validate: constraints satisfied → Synthesize: action plan"

"Set: execution context → Define: scope and limits → Identify: required protocols → Process: in dependency order → Output: results with status"

"Extract: data fields → Transform: to standard format → Validate: against schema → Track: transformation steps → Verify: completeness"
```
