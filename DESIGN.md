# Design Notes

- Build depth before breadth: implement one class from levels 1-20, then support its table interactions, then support creation and level-up flows.
- Add new classes to the sheet editor only after their rule model is implemented enough to play.
- Rules live in Python code: enums, dataclasses, progression tables, and helper functions are the source of truth.
- Avoid stringly rule implementation. Identifiers such as classes, abilities, dice, damage types, rests, and actions should be enums or typed values.
- Avoid magic numbers in application logic. Put class progression, resource counts, dice, and level gates in named rule structures.
- JSON is storage and transport, not the rule engine. Load/save should generically encode and decode the Python model.
- UI text is a translation layer derived from code identifiers.

```python
UIStringFormatter.clean_name(AbilityType.STRENGTH.name)
```

- The DM has full control. Players control their own sheets and tokens.
- The system helps track resources and math, but it does not strictly enforce tabletop rules.
- The board remains independent from character movement rules; sheets are tools for play, not a rules cage.
