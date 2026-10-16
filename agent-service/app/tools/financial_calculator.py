from app.schemas.tools import (
    FinancialCalculationType,
    FinancialCalculatorInput,
    FinancialCalculatorOutput,
)


def financial_calculator_tool(
    tool_input: FinancialCalculatorInput,
) -> FinancialCalculatorOutput:
    calculation_type = tool_input.calculation_type

    if calculation_type == FinancialCalculationType.growth_rate:
        if tool_input.current_value is None or tool_input.previous_value is None:
            raise ValueError("current_value and previous_value are required.")

        if tool_input.previous_value == 0:
            raise ValueError("previous_value cannot be zero for growth rate.")

        result = (
            (tool_input.current_value - tool_input.previous_value)
            / abs(tool_input.previous_value)
        )
        return FinancialCalculatorOutput(
            calculation_type=calculation_type,
            result=result,
            result_percent=result * 100,
            explanation=(
                "Growth rate = (current value - previous value) "
                "/ absolute previous value."
            ),
        )

    if calculation_type == FinancialCalculationType.margin:
        if tool_input.numerator is None or tool_input.denominator is None:
            raise ValueError("numerator and denominator are required.")

        if tool_input.denominator == 0:
            raise ValueError("denominator cannot be zero for margin.")

        result = tool_input.numerator / tool_input.denominator
        return FinancialCalculatorOutput(
            calculation_type=calculation_type,
            result=result,
            result_percent=result * 100,
            explanation="Margin = numerator / denominator.",
        )

    if calculation_type == FinancialCalculationType.delta:
        if tool_input.current_value is None or tool_input.previous_value is None:
            raise ValueError("current_value and previous_value are required.")

        result = tool_input.current_value - tool_input.previous_value
        return FinancialCalculatorOutput(
            calculation_type=calculation_type,
            result=result,
            result_percent=None,
            explanation="Delta = current value - previous value.",
        )

    if calculation_type == FinancialCalculationType.percentage_of:
        if tool_input.numerator is None or tool_input.denominator is None:
            raise ValueError("numerator and denominator are required.")

        if tool_input.denominator == 0:
            raise ValueError("denominator cannot be zero for percentage_of.")

        result = tool_input.numerator / tool_input.denominator
        return FinancialCalculatorOutput(
            calculation_type=calculation_type,
            result=result,
            result_percent=result * 100,
            explanation="Percentage of = numerator / denominator.",
        )

    if calculation_type == FinancialCalculationType.cagr:
        if (
            tool_input.beginning_value is None
            or tool_input.ending_value is None
            or tool_input.periods is None
        ):
            raise ValueError(
                "beginning_value, ending_value, and periods are required."
            )

        if tool_input.beginning_value <= 0:
            raise ValueError("beginning_value must be greater than zero.")

        if tool_input.periods <= 0:
            raise ValueError("periods must be greater than zero.")

        result = (tool_input.ending_value / tool_input.beginning_value) ** (
            1 / tool_input.periods
        ) - 1

        return FinancialCalculatorOutput(
            calculation_type=calculation_type,
            result=result,
            result_percent=result * 100,
            explanation=(
                "CAGR = (ending value / beginning value) "
                "^(1 / periods) - 1."
            ),
        )

    raise ValueError(f"Unsupported calculation type: {calculation_type}")