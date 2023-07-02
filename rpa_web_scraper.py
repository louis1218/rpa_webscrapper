from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import requests
from bs4 import BeautifulSoup
import pandas as pd



class WebScaper():
    
    def __init__(self) -> None:
        # Set up the browser
        self.driver = webdriver.Chrome()

        # Navigate to the webpage
        self.driver.get("http://medicarestatistics.humanservices.gov.au/statistics/mbs_group.jsp")

        self.driver.implicitly_wait(10)


        
        
    def createReport(self):
        
        self.report_on_dropdown = Select(self.driver.find_element(By.NAME, 'GROUP'))
        self.report_on_dropdown.select_by_visible_text("Category 5 - Diagnostic Imaging Services")
            
        # Find the "Create Report" button and click it
        self.create_report_button = self.driver.find_element(By.XPATH, '//input[@value="Create Report"]')
        self.create_report_button.click()

        new_url = self.driver.current_url

        page = requests.get(new_url)

        self.soup = BeautifulSoup(page.text, 'lxml')

        table = self.soup.find_all('table')
        table1 = table[0]
        table2 = table[1]
        table3 = table[2]
        
        return table1, table2, table3


    def removeItem(self, list, redun1, redun2):
        
        # Remove Redundant item - Subgroup and Total
        while redun1 in list:
            list.remove('Subgroup')
        while redun2 in list:
            list.remove('Total')
            
        return list
            
            
    def scrappingEssentialGroupData(self): 
        
        # Find all State data from the source page
        state_list = []
        state = False
        table1, table2, table3 = self.createReport()
        for i in table1.find_all('th'):
            if i.text == "State":
                state = True
            if i.text == 'Services':
                state = False
            if state:
                state_list.append(i.text)
                
        state_list = state_list[2:]
        state_list = [state.strip(' ') for state in state_list]

        # Find all Group data from the source page
        group_list = []
        group1 = False
        group2 = False
        first_group = False
        group3 = False
        for i in table1.find_all('th'):
            if i.text == "Group":
                group1 = True
            if i.text == "Subgroup":
                group2 = True
            if group1 and group2:
                group_list.append(i.text)
                if len(group_list)>1:
                    group1 = False
                    group2 = False
                    first_group = True
            if first_group and i.text == "Total":
                group3 = True
            if group3 == True and i.text == "Subgroup":
                group3 = False
            if group3 == True:
                group_list.append(i.text)
            
        group_list = self.removeItem(group_list, 'Subgroup', 'Total')
        
        sub_group_list = []
        group1 = False
        group2 = False
        first_group = False
        group3 = False
        for i in table1.find_all('th'):
            if i.text == "Group":
                group1 = True
            if i.text == "Subgroup":
                group2 = True
            if group1 and group2:
                sub_group_list.append(i.text)            
            
        sub_group_list = self.removeItem(sub_group_list, 'Subgroup', 'Total')
            
        # Create dictionary to store Group and subgroups
        data_dict = {}
        current_key = ''

        for item in sub_group_list:
            item = item.strip()
            if item.startswith('I'):
                current_key = item
                data_dict[current_key] = []
            else:
                data_dict[current_key].append(item)
        

        num_of_services_per_group = {}
        for key, value in data_dict.items():
            num_of_services_per_group[key] = len(value)
            
        for key, value in data_dict.items():
            value.append("Total")
            
        df_subgroup_list = []
        df_group_list = []
        for key, value in data_dict.items():
            df_subgroup_list.append(value)
            for i in range(len(value)):
                df_group_list.append(key)
                
        flat_list = []
        for sublist in df_subgroup_list:
            for item in sublist:
                flat_list.append(item)
        
        # Create an inital df to store Group and Subgroup
        initial_df = pd.DataFrame(
            {'Group': df_group_list,
            'Subgroup': flat_list,
            })

        total_row = {'Group':'Total', 'Subgroup':'Total'}

        new_df = pd.DataFrame([total_row])
        initial_df = pd.concat([initial_df, new_df], axis=0, ignore_index=True)

        state_list.append("Total")


        return initial_df, state_list, num_of_services_per_group
    
    def scrappingEssentialNumberOfService(self):
        
        initial_df, state_list, num_of_services_per_group = self.scrappingEssentialGroupData()

        num_of_services = []
        for tr in self.soup.find_all('table'):
            tds = tr.find_all('td')
            for td in tds:
                num_of_services.append((td.text))
                
        num_of_services = [num.strip(' ') for num in num_of_services]

        num_of_services = [num.replace(",", "") for num in num_of_services]

        for i in range(len(num_of_services)):
            if num_of_services[i] == 'NB: The following groups are also part of this category':
                index = i

        num_of_services = num_of_services[:index]


        num_of_services = [eval(i) for i in num_of_services]

        sublists = [num_of_services[i:i+len(state_list)] for i in range(0, len(num_of_services), len(state_list))]


        df_state_service = pd.DataFrame(columns=state_list)

        for i in range(len(sublists)):
            df_state_service.loc[i] = sublists[i]
            
        return initial_df, df_state_service,num_of_services_per_group
    
        
        
if __name__ == "__main__":
    
    web_scrapper = WebScaper()
    
    initial_df, df_state_service,num_of_services_per_group = web_scrapper.scrappingEssentialNumberOfService()
    
    final_df = pd.merge(initial_df, df_state_service, left_index=True, right_index=True)

    final_df.to_csv("final_csv.csv", index=False)

    print(num_of_services_per_group)