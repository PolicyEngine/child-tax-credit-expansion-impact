import streamlit as st
from policyengine_us import Simulation
from policyengine_core.reforms import Reform
from policyengine_core.periods import instant
import datetime
import plotly.graph_objects as go
from policyengine_core.charts import format_fig  
import pandas as pd

# Main Streamlit interface
st.title("PolicyEngine Wyden-Smith CTC reform impact")
st.write("Analyzing the impact of the proposed Wyden-Smith Child Tax Credit reform for the years 2023 to 2025.")

def modify_parameters(parameters):
    parameters.gov.contrib.congress.wyden_smith.actc_lookback.update(start=instant("2023-01-01"), stop=instant("2025-12-31"), value=True)
    parameters.gov.contrib.congress.wyden_smith.per_child_actc_phase_in.update(start=instant("2023-01-01"), stop=instant("2025-12-31"), value=True)
    parameters.gov.irs.credits.ctc.refundable.individual_max.update(start=instant("2023-01-01"), stop=instant("2023-12-31"), value=1800)
    parameters.gov.irs.credits.ctc.refundable.individual_max.update(start=instant("2024-01-01"), stop=instant("2024-12-31"), value=1900)
    parameters.gov.irs.credits.ctc.refundable.individual_max.update(start=instant("2025-01-01"), stop=instant("2025-12-31"), value=2100)  
    parameters.gov.irs.credits.ctc.amount.base[0].amount.update(start=instant("2024-01-01"), stop=instant("2025-12-31"), value=2100)  
    return parameters

class reform(Reform):
    def apply(self):
        self.modify_parameters(modify_parameters)

DEFAULT_ADULT_AGE = 40


# Main Streamlit interface
# Note about CTC-eligible children
st.write("Note: CTC-eligible children should be under 17 years of age.")

# Collecting the number of CTC-eligible children
num_ctc_eligible_children = st.number_input("Number of CTC-Eligible Children", min_value=0, max_value=10, value=0)

# Collecting marital status
is_married = st.checkbox("Married")

# Collecting earnings for each year from 2023 to 2025
earned_income_data = {}
for year in range(2023, 2026):
    # Generate a unique key for each input to prevent duplicate widgets
    income_label = f"{'Household' if is_married else 'Your'} Earned Income in {year}"
    key = f"{'married' if is_married else 'single'}_earned_income_{year}"
    earned_income_data[year] = st.number_input(income_label, key=key, value=0)


# Function to construct the household situation
def get_household_info(year, is_married, num_ctc_eligible_children, employment_income, employment_income_last_year):
    situation = {
        "people": {
            "you": {
                "age": {str(year): DEFAULT_ADULT_AGE},
                "earned_income": {str(year): employment_income},
                "earned_income_last_year": {str(year): employment_income_last_year},

            }
        },
        "tax_units": {
            "your tax unit": {
                "members": ["you"],
                "ctc_qualifying_children": num_ctc_eligible_children,
            }
        }
    }
    members = ["you"]

    if is_married:
        situation["people"]["your partner"] = {
            "age": {str(year): DEFAULT_ADULT_AGE},
            "earned_income": {str(year): employment_income},  
        }
        members.append("your partner")

    # Update the rest of the situation entities accordingly
    situation["families"] = {"your family": {"members": members}}
    situation["marital_units"] = {"your marital unit": {"members": members if is_married else ["you"]}}
    situation["tax_units"]["your tax unit"]["members"] = members
    situation["spm_units"] = {"your spm_unit": {"members": members}}
    situation["households"] = {"your household": {"members": members}}

    baseline = Simulation(situation=situation)
    baseline_income = baseline.calculate("household_net_income", year)

    reform_simulation = Simulation(reform=reform, situation=situation)
    reform_income = reform_simulation.calculate("household_net_income", year)

    income_change = reform_income - baseline_income

    return income_change


# Initialize a dictionary to keep track of the last year's employment income
last_year_employment_income = {}

# Collecting earnings for each year from 2023 to 2025 and setting last year's income
for year in range(2023, 2026):
    if year > 2023:  # For years after 2023, set the last year's income
        last_year_employment_income[year] = earned_income_data[year - 1]
    else:
       last_year_employment_income[year] =  earned_income_data[year]



# Dictionary to store income changes for each year
income_changes = {}
last_year_income = 0  # Initialize last_year_income

for year in range(2023, 2026):
    earned_income = earned_income_data[year]
    # For the year 2023, there's no previous income, so use the current year's income
    if year == 2023:
        last_year_income = earned_income
    # Call the function with the correct arguments
    income_change = get_household_info(year, is_married, num_ctc_eligible_children, earned_income, last_year_income)
    # Store the income change for the year
    income_changes[year] = income_change
    # Update last_year_income with the current year's income for the next iteration
    last_year_income = earned_income


# Create a bar chart using Plotly
fig = go.Figure(data=[
    go.Bar(x=list(income_changes.keys()), y=list(income_changes.values()), marker_color='rgb(55, 83, 109)')
])

fig.update_layout(
    title='Income Changes from 2023 to 2025',
    xaxis=dict(
        type='category',  # Define x-axis type as category
        showgrid=False,   # Hides the vertical grid lines
        title=''          # Removes the x-axis title
    ),
    yaxis=dict(title='Income Change'))

# Styling the figure (assuming format_fig is a custom function for styling)
fig = format_fig(fig)

# Display the Plotly bar chart in Streamlit
st.plotly_chart(fig)


# Add a section for caveats at the bottom of the app
st.markdown("""
#### Caveats
Please note the following assumptions in this simplified simulation:
- All earnings are assumed to be from the primary's wages and salaries.
- There are no other sources of income considered.
- No deductions are taken into account.
- All children are assumed to be CTC-eligible for all three years.

For a more tailored impact analysis that takes into account more detailed household characteristics, please visit our [full application](https://policyengine.org/us).
""")
