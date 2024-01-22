import streamlit as st
from policyengine_us import Simulation
from policyengine_core.reforms import Reform
from policyengine_core.periods import instant
import datetime

def modify_parameters(parameters):
    parameters.gov.contrib.congress.wyden_smith.actc_lookback.update(start=instant("2023-01-01"), stop=instant("2025-12-31"), value=True)
    parameters.gov.contrib.congress.wyden_smith.per_child_actc_phase_in.update(start=instant("2023-01-01"), stop=instant("2025-12-31"), value=True)
    parameters.gov.irs.credits.ctc.refundable.individual_max.update(start=instant("2023-01-01"), stop=instant("2023-12-31"), value=1800)
    parameters.gov.irs.credits.ctc.refundable.individual_max.update(start=instant("2024-01-01"), stop=instant("2024-12-31"), value=1900)
    parameters.gov.irs.credits.ctc.refundable.individual_max.update(start=instant("2025-01-01"), stop=instant("2025-12-31"), value=2000)
    return parameters

class reform(Reform):
    def apply(self):
        self.modify_parameters(modify_parameters)

DEFAULT_ADULT_AGE = 40

def calculate_age(birthdate, year):
    return year - birthdate.year - ((datetime.date(year, 1, 1) - birthdate).days < 0)

num_dependents = st.number_input("Number of Dependents", min_value=0, max_value=10, value=0)
dependent_birthdates = []
for i in range(num_dependents):
    birthdate = st.date_input(f"Birthdate of Dependent {i + 1}", datetime.date(2020, 1, 1))
    dependent_birthdates.append(birthdate)

def get_household_info(year, is_married, dependent_birthdates, head_earned, spouse_earned):
    situation = {
        "people": {
            "you": {
                "age": {str(year): DEFAULT_ADULT_AGE},
                "employment_income": {str(year): head_earned},
            }
        }
    }
    members = ["you"]

    if is_married:
        situation["people"]["your partner"] = {
            "age": {str(year): DEFAULT_ADULT_AGE},
            "employment_income": {str(year): spouse_earned},
        }
        members.append("your partner")

    for i, birthdate in enumerate(dependent_birthdates):
        age = calculate_age(birthdate, year)
        situation["people"][f"dependent_{i + 1}"] = {
            "age": {str(year): age}
        }
        members.append(f"dependent_{i + 1}")

    situation["families"] = {"your family": {"members": members}}
    situation["marital_units"] = {"your marital unit": {"members": members if is_married else ["you"]}}
    situation["tax_units"] = {"your tax unit": {"members": members}}
    situation["spm_units"] = {"your spm_unit": {"members": members}}
    situation["households"] = {"your household": {"members": members}}

    simulation = Simulation(
        reform=reform,
        situation=situation,
    )

    household_net_income = simulation.calculate("household_net_income", year)
    refundable_ctc = simulation.calculate("refundable_ctc", year)

    return household_net_income, refundable_ctc

# Add a note about the assumption
st.write("Note: It is assumed that the earned income in 2021 was the same as in 2022.")

# Collecting earned income data for each year from 2021 to 2024
earned_income_data = {"head": {}, "spouse": {}}
for year in range(2022, 2026):
    earned_income_data["head"][year] = st.number_input(f"Head Earned Income in {year}", 0)
    earned_income_data["spouse"][year] = st.number_input(f"Spouse's Earned Income in {year}", 0)

# Assume 2021 income is the same as 2022
earned_income_data["head"][2021] = earned_income_data["head"][2022]
earned_income_data["spouse"][2021] = earned_income_data["spouse"][2022]

is_married = st.checkbox("Married")

for year in range(2022, 2026):
    head_earned = earned_income_data["head"][year]
    spouse_earned = earned_income_data["spouse"][year]
    household_net_income, refundable_ctc = get_household_info(year, is_married, dependent_birthdates, head_earned, spouse_earned)
    st.write(f"Refundable CTC for {year}: {refundable_ctc}")
