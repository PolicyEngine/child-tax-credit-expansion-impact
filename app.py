import streamlit as st
from policyengine_us import Simulation
from policyengine_core.reforms import Reform
from policyengine_core.periods import instant
import plotly.express as px
from policyengine_core.charts import format_fig
import pandas as pd


# URL of the PolicyEngine logo
LOGO_IMAGE_URL = "https://github.com/PolicyEngine/policyengine-app/blob/master/src/images/logos/policyengine/blue.png?raw=true"

# Put the logo in the top centered.
col1, col2, col3 = st.columns(
    [1, 2, 1]
)  # The middle column is where the image will be

# Display the logo in the middle column
with col2:
    # Link for the clickable logo
    PE_LINK = "https://policyengine.org"

    # Create a clickable image with markdown
    st.markdown(
        f"<a href='{PE_LINK}' target='_blank'>"
        f"<img src='{LOGO_IMAGE_URL}' style='display: block; margin-left: auto; margin-right: auto; width: 150px;'>"
        "</a>",
        unsafe_allow_html=True,
    )

# Title and subtitle.
st.title("How would the TRAFWA Child Tax Credit impact you?")
st.markdown(
    "See how the Tax Relief for American Families and Workers Act would change your Child Tax Credit from 2023 to 2025. Powered by [PolicyEngine](https://policyengine.org)."
)


def modify_parameters(parameters):
    parameters.gov.contrib.congress.wyden_smith.actc_lookback.update(
        start=instant("2023-01-01"), stop=instant("2025-12-31"), value=True
    )
    parameters.gov.contrib.congress.wyden_smith.per_child_actc_phase_in.update(
        start=instant("2023-01-01"), stop=instant("2025-12-31"), value=True
    )
    parameters.gov.irs.credits.ctc.refundable.individual_max.update(
        start=instant("2023-01-01"), stop=instant("2023-12-31"), value=1800
    )
    parameters.gov.irs.credits.ctc.refundable.individual_max.update(
        start=instant("2024-01-01"), stop=instant("2024-12-31"), value=1900
    )
    parameters.gov.irs.credits.ctc.refundable.individual_max.update(
        start=instant("2025-01-01"), stop=instant("2025-12-31"), value=2100
    )
    parameters.gov.irs.credits.ctc.amount.base[0].amount.update(
        start=instant("2024-01-01"), stop=instant("2025-12-31"), value=2100
    )
    return parameters


class reform(Reform):
    def apply(self):
        self.modify_parameters(modify_parameters)


DEFAULT_ADULT_AGE = 40

# Collecting the number of CTC-eligible children
ctc_eligible_children = st.number_input(
    "How many CTC-eligible children do you have?",
    min_value=0,
    max_value=10,
    value=1,
)

# Collecting marital status
is_married = st.radio("Are you married?", ("Yes", "No")) == "Yes"


# Collecting earnings for each year from 2023 to 2025
# Function to format the input as a dollar amount
def format_dollar(amount):
    if amount is not None:
        return "${:,.0f}".format(amount)
    return ""


def get_earnings(year):
    # Ask how much you earned if in 2023, otherwise how much you expect to earn.
    if year == 2023:
        question = f"How much did you earn in {year}?"
    else:
        question = f"How much do you expect to earn in {year}?"
    earnings_input = st.text_input(question, value="$0")
    return int("".join(filter(str.isdigit, earnings_input)))


earnings = {}
for year in range(2023, 2026):
    earnings[year] = get_earnings(year)


# Function to construct the household situation
def get_household_info(year, is_married, ctc_eligible_children, earnings):
    situation = {
        "people": {
            "you": {
                "age": {str(year): DEFAULT_ADULT_AGE},
                "employment_income": {str(year): earnings[year]},
                "employment_income_last_year": {
                    str(year): 0 if year == 2023 else earnings[year - 1]
                },
            }
        },
        "tax_units": {
            "your tax unit": {
                # Zero out some quantities that won't change between baseline and reform
                # This will improve performance.
                "premium_tax_credit": {str(year): 0},
                "tax_unit_itemizes": {str(year): False},
                "taxable_income_deductions_if_itemizing": {str(year): 0},
                "alternative_minimum_tax": {str(year): 0},
                "net_investment_income_tax": {str(year): 0},
                "eitc": {str(year): 0},
            }
        },
        "households": {"your household": {"state_code_str": "TX"}},
    }
    members = ["you"]

    if is_married:
        situation["people"]["spouse"] = {"age": {str(year): DEFAULT_ADULT_AGE}}
        members.append("spouse")
    for i in range(ctc_eligible_children):
        situation["people"][f"child{i}"] = {"age": {str(year): 0}}
        members.append(f"child{i}")

    # Update the rest of the situation entities accordingly
    situation["families"] = {"your family": {"members": members}}
    situation["marital_units"] = {
        "your marital unit": {"members": members if is_married else ["you"]}
    }
    situation["tax_units"]["your tax unit"]["members"] = members
    situation["spm_units"] = {"your spm_unit": {"members": members}}
    situation["households"]["your household"]["members"] = members

    # Avoid computing benefits by only computing taxes and credits.
    # This will speed up the simulation.
    baseline = Simulation(situation=situation)
    baseline_tax = baseline.calculate(
        "income_tax_before_refundable_credits", year
    )[0]
    baseline_actc = baseline.calculate("refundable_ctc", year)[0]

    reform_simulation = Simulation(reform=reform, situation=situation)
    reform_tax = reform_simulation.calculate(
        "income_tax_before_refundable_credits", year
    )[0]
    reform_actc = reform_simulation.calculate("refundable_ctc", year)[0]

    actc_change = reform_actc - baseline_actc
    tax_change = reform_tax - baseline_tax
    return actc_change - tax_change


# Dictionary to store income changes for each year
income_changes = {}

for year in range(2023, 2026):
    income_change = get_household_info(
        year, is_married, ctc_eligible_children, earnings
    )
    income_changes[year] = income_change

total_income_change = sum(income_changes.values())

# Create a DataFrame from the income_changes dictionary
df_income_changes = pd.DataFrame(
    list(income_changes.items()), columns=["Year", "Income Change"]
)

# Convert 'Year' to string if it isn't already, to ensure it displays correctly on the x-axis
df_income_changes["Year"] = df_income_changes["Year"].astype(str)

# Sum the total benefit over the three years
total_ctc_benefit = sum(df_income_changes["Income Change"])

# Update the chart title to include the total CTC benefit
chart_title = f"TRAFWA would raise your Child Tax Credit by ${total_ctc_benefit:,.0f} from 2023 to 2025"

# Create a bar chart using Plotly Express with a single color for all bars
fig = px.bar(
    df_income_changes,
    x="Year",
    y="Income Change",
    text="Income Change",
    color_discrete_sequence=["#003f5c"],
)

# Update the layout to remove the legend and add the total to the title
fig.update_layout(
    title=chart_title,
    showlegend=False,
    xaxis=dict(title="", showgrid=False),
    yaxis=dict(
        title="TRAFWA CTC Impact",
        tickprefix="$",
        tickformat=",",
        showgrid=False,
    ),
    font=dict(family="Roboto, sans-serif"),
)

# Add the dollar sign to the bar text and set the text position
fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")

# Style the figure
fig = format_fig(fig)

# Display the Plotly bar chart in Streamlit
st.plotly_chart(fig)

# Add a section for caveats at the bottom of the app
st.markdown(
    """
#### Notes
This simulation assumes that:
- All earnings are from the tax filer's wages and salaries.
- The filer has no other taxable income.
- The filer takes the standard deduction.
- All children are eligible for the Child Tax Credit in each of 2023, 2024, and 2025.
- Married couples file jointly.
- [TRAFWA increases the maximum non-refundable CTC to $2,100 per child beginning in 2024.](https://github.com/PolicyEngine/policyengine-us/discussions/3726)

To estimate how TRAFWA would affect you with more flexibility, describe your household in the [full PolicyEngine app](https://policyengine.org/us/household?reform=46315&focus=intro).
            
We do not store any personal data entered into this app.
"""
)
