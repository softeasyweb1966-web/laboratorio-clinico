"""
Reference value checker service.
Given a Parameter, a value, the patient age and gender,
returns (out_of_range: bool, description: str).
"""


def check_parameter_value(parameter, value, age, gender):
    """
    Check whether *value* is within the reference range defined for
    *parameter*, considering patient *age* and *gender*.

    Returns:
        (out_of_range: bool, description: str)
    """
    if parameter.is_fixed:
        return False, ''

    if not value:
        return False, ''

    ref_values = parameter.reference_values.all()
    if not ref_values:
        return False, ''

    # Find the most specific matching reference value
    matching = [rv for rv in ref_values if rv.matches(age, gender)]
    if not matching:
        return False, ''

    # Use the first match (most-specific filtering happens in matches())
    rv = matching[0]
    out_of_range, description = rv.check_value(value)
    return out_of_range, description
