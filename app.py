import streamlit as st



from policyengine_us import Simulation

from policyengine_core.reforms import Reform

from policyengine_core.periods import instant


def modify_parameters(parameters):
    parameters.gov.contrib.congress.wyden_smith.ctc_expansion.update(start=instant("2023-01-01"), stop=instant("2023-12-31"), value=True)
    parameters.gov.irs.credits.ctc.refundable.individual_max.update(start=instant("2023-01-01"), stop=instant("2023-12-31"), value=1800)
    return parameters


class reform(Reform):
    def apply(self):
        self.modify_parameters(modify_parameters)

DEFAULT_ADULT_AGE = 40


def get_household_info(is_married, tax_unit_dependents, head_earned, spouse_earned):
    situation = {
        "people": {
            "you": {
            "age": {
                "2023": DEFAULT_ADULT_AGE
            },
            "employment_income": {
                "2023": head_earned},
            }
        }
    }
    members = ["you"]
    if is_married is True:
        situation["people"]["your partner"] = {
            "age": {"2023": DEFAULT_ADULT_AGE},
            "employment_income": {"2023": spouse_earned},
        }
        members.append("your partner")
    situation["families"] = {"your family": {"members": members}}
    situation["marital_units"] = {"your marital unit": {"members": members}}
    situation["tax_units"] = {"your tax unit": {"members": members}}
    situation["spm_units"] = {"your spm_unit": {"members": members}}
    situation["households"] = {
        "your household": {"members": members}
    }

    simulation = Simulation(
        reform=reform,
        situation=situation,
    )

    return simulation.calculate("household_net_income", 2023)


def get_net_income(head_earned, spouse_earned):
    total_net_income = get_household_info(is_married, tax_unit_dependents, head_earned, spouse_earned)
    net_income_head = get_household_info(head_earned)
    net_income_spouse = get_household_info(spouse_earned)
    return total_net_income, net_income_head + net_income_spouse



head_earned_income_2022 = st.number_input("Head Earned Income in 2022", 0)
head_earned_income_2023 = st.number_input("Head Earned Income in 2023", 0)
head_earned = max(head_earned_income_2022, head_earned_income_2023)
is_married = st.checkbox("Married")
tax_unit_dependents = 0

spouse_earned_income_2022 = st.number_input("Spouse's Earned Income in 2022", 0)
spouse_earned_income_2023 = st.number_input("Spouse's Earned Income in 2023", 0)
spouse_earned = max(spouse_earned_income_2022, spouse_earned_income_2023)




net_income = get_net_income(head_earned, spouse_earned)


st.write(net_income)
