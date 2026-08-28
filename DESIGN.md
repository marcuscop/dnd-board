# Design Notes

- Build depth before breadth: implement one class from levels 1-20, then support its table interactions, then support creation and level-up flows.
- Add new classes to the sheet editor only after their rule model is implemented enough to play.
- Rules live in Python code: enums, dataclasses, progression tables, and helper functions are the source of truth.
- Avoid stringly rule implementation. Rule identifiers and categories should be enums or typed dataclass fields.
- Strings are acceptable for free-form content and boundaries: names, descriptions, filenames, URLs, external message types, and raw JSON field names.
- Convert rule-bearing strings at the boundary. Once data is loaded, gameplay code should work with dataclasses, enums, and typed collections.

```python
# Boundary code can parse strings.
class_type = enum_value(ClassType, raw_class_name)

# Rule code should receive typed values.
if character_class.name == ClassType.FIGHTER:
    ...
```

- Prefer adding a typed field to a dataclass over encoding a rule in a string, dict shape, or description.

```python
if WeaponProperty.THROWN in attack.properties:
    ...
```

- UI labels should be derived from typed identifiers when possible; descriptive copy should explain rules, not drive them.
- Avoid magic numbers in application logic. Put class progression, resource counts, dice, and level gates in named rule structures.
- JSON is storage and transport, not the rule engine. Load/save should generically encode and decode the Python model.
- UI text is a translation layer derived from code identifiers.

```python
UIStringFormatter.clean_name(AbilityType.STRENGTH.name)
```

- The DM has full control. Players control their own sheets and tokens.
- The system helps track resources and math, but it does not strictly enforce tabletop rules.
- The board remains independent from character movement rules; sheets are tools for play, not a rules cage.
- Add or update focused backend and frontend tests for every gameplay or UI feature change.
