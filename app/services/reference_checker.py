"""
Reference value checker service.
Given a Parameter, a value, the patient age and gender,
returns (out_of_range: bool, description: str).
"""


def _rv_matches(rv, age, gender):
    """Return True if this reference value applies to the given age/gender."""
    if rv.gender and gender and rv.gender.upper() != gender.upper():
        return False
    if rv.min_age is not None and age is not None and age < rv.min_age:
        return False
    if rv.max_age is not None and age is not None and age > rv.max_age:
        return False
    return True


def _rv_check(rv, value):
    """Return (out_of_range, description) for a single reference value."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False, ''

    if rv.ref_type == 'range':
        lo, hi = rv.min_value, rv.max_value
        out = (lo is not None and numeric < lo) or (hi is not None and numeric > hi)
        desc = f"{lo if lo is not None else ''} – {hi if hi is not None else ''} {rv.units or ''}".strip()
        return out, desc

    if rv.ref_type == 'exact':
        out = rv.exact_value is not None and numeric != rv.exact_value
        desc = f"= {rv.exact_value} {rv.units or ''}".strip()
        return out, desc

    return False, rv.text_value or ''


def check_parameter_value(parameter, value, age, gender):
    if parameter.is_fixed or not value:
        return False, ''

    ref_values = parameter.reference_values.all()
    if not ref_values:
        return False, ''

    matching = [rv for rv in ref_values if _rv_matches(rv, age, gender)]
    if not matching:
        return False, ''

    return _rv_check(matching[0], value)
