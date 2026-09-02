# Reject boolean inventory quantities

`add_item` promises a positive integer quantity, but Python booleans currently
pass that validation because `bool` is a subclass of `int`.

Keep accepting ordinary positive integers. Reject `True` and `False` with the
same `ValueError` used for other invalid quantities. Preserve all existing name
validation, immutability, CLI behavior, and error messages. Add focused public
regression coverage. Do not introduce a validation library or refactor unrelated
inventory behavior.
