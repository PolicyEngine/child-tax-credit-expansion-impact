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
        use_column_width="always",
    )

# Title and subtitle.
st.title("How Would the TRAFWA Child Tax Credit Impact You?")
st.write(
    "See how the Tax Relief for American Families and Workers Act would change your Child Tax Credit from 2023 to 2025. Powered by PolicyEngine."
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


# Main Streamlit interface
# Note about CTC-eligible children
st.write(
    "Note: The US counts children as eligible for the Child Tax Credit if they are younger than 17 years of age."
)

# Collecting the number of CTC-eligible children
ctc_eligible_children = st.number_input(
    "How many eligible children do you have?",
    min_value=0,
    max_value=10,
    value=0,
)

# Collecting marital status
is_married = st.checkbox("Married")

# Collecting earnings for each year from 2023 to 2025
earned_income_data = {}
for year in range(2023, 2026):
    # Generate a unique key for each input to prevent duplicate widgets
    income_label = (
        f"{'Household' if is_married else 'Your'} Earned Income in {year}"
    )
    key = f"earned_income_{year}"
    earned_income_data[year] = st.number_input(income_label, key=key, value=0)


# Function to construct the household situation
def get_household_info(
    year, is_married, ctc_eligible_children, earned_income_data
):
    situation = {
        "people": {
            "you": {
                "age": {str(year): DEFAULT_ADULT_AGE},
                "employment_income": {str(year): earned_income_data[year]},
                "employment_income_last_year": {
                    str(year): 0
                    if year == 2023
                    else earned_income_data[year - 1]
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
    income_change = actc_change - tax_change

    return income_change


# Dictionary to store income changes for each year
income_changes = {}

for year in range(2023, 2026):
    income_change = get_household_info(
        year, is_married, ctc_eligible_children, earned_income_data
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
)

# Add the dollar sign to the bar text and set the text position
fig.update_traces(texttemplate="$%{text:.2s}", textposition="outside")

# Style the figure
fig = format_fig(fig)

# Display the Plotly bar chart in Streamlit
st.plotly_chart(fig)

# Add a section for caveats at the bottom of the app
st.markdown(
    """
#### Caveats
Please note the following assumptions in this simplified simulation:
- All earnings are assumed to be from the primary's wages and salaries.
- There are no other sources of income considered.
- No deductions are taken into account.
- All children are assumed to be CTC-eligible for all three years.
- [TRAFWA increases the maximum non-refundable CTC to $2,100 per child beginning in 2024.](https://github.com/PolicyEngine/policyengine-us/discussions/3726)

For a more tailored impact analysis that takes into account more detailed household characteristics, please visit our [full application](https://policyengine.org/us).
"""
)
