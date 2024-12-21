import utils.config_util as config_util
import utils.df_util as df_util
import utils.helper as hp

import utils.playwright_manager as pm
import utils.requests_manager as rm

import time
import re

def start(main_dir, start_with_page=1):
    print("Starting arbetsformedlingenParser...")

    # Read configuration
    url, xlsx_file_name, xlsx_sheet_name, save_file_interval = config_util.get_all("arbetsformedlingen", main_dir)
    save_file_interval = int(save_file_interval)

    # Launch the browser
    browser = pm.launch_playwright(main_dir)

    # Create a data frame
    columns = ["Vacancy Name", "Company Name", "Phone", "Email", "Website"]
    df = df_util.create_df(columns)

    # First request
    pm.goto_page(browser, url)

    # Wait for the page to load
    pm.wait_for(browser, "h3 a")

    # Get the current page
    page = pm.get_current_page(browser)

    # Get the number of results
    number_of_results_text = rm.get_text(page, "h2 strong", "0")
    number_of_results = hp.get_number(number_of_results_text)
    page_size = len(rm.get_elements(page, "h3 a"))
    last_page_text = rm.get_text(page, "li:last-child .digi-navigation-pagination__page-text")
    last_page = hp.get_number(last_page_text)
    if last_page * page_size < number_of_results:
        number_of_results = last_page * page_size

    # Set first page
    start_with_element = (start_with_page - 1) * page_size
    url = hp.update_url_param(url, "page", start_with_page)

    progress_counter = start_with_element
    while True:
        # Get page content
        pm.goto_page(browser, url)

        # Wait for the page to load
        pm.wait_for(browser, "h3 a")

        # Get the current page
        page = pm.get_current_page(browser)

        # Get results
        results = rm.get_elements(page, "pb-feature-search-result-card")

        # Parse results
        for result in results:
            # Set start time to calculate the time it takes to parse the page
            start_time = time.time()

            # Get vacancy name
            vacancy_name = rm.get_text(result, "h3 a")

            # Get the company name
            company_name = rm.get_text(result, ".pb-company-name")

            # Get vacancy URL
            vacancy_url = rm.get_attribute(result, "href", "h3 a")

            # Get the vacancy page
            pm.goto_page(browser, "https://arbetsformedlingen.se" + vacancy_url)

            # Wait for the page to load
            pm.wait_for(browser, "h1")

            vacancy_page = pm.get_current_page(browser)
            
            # Get the website
            website = rm.get_text(vacancy_page, ".employer-link span")

            # Get the mail
            try:
                mails = []
                elements = rm.get_elements(vacancy_page, "a.regular-link")
                for element in elements:
                    element_text = rm.get_text(element)
                    if "@" in element_text:
                        mails.append(element_text)
                mail = ", ".join(mails)
            except Exception as e:
                mail = ""

            # Get the phone
            try:
                phones = []
                content = rm.get_text(vacancy_page, "lib-pb-section-job-contact")
                phones = re.findall(r"\b(?:\d[\s-]?){5,13}\b", content)
                phone = ", ".join(phones)
            except Exception as e:
                print(f"Error: {e}")
                phone = ""

            # Add the data to the data frame
            row = {
                "Vacancy Name": vacancy_name,
                "Company Name": company_name,
                "Phone": phone,
                "Email": mail,
                "Website": website
            }
            df = df_util.add_row(df, row)

            # Save the data to the file
            progress_counter += 1
            if progress_counter % save_file_interval == 0:
                df_util.save_df(df, main_dir, xlsx_file_name, xlsx_sheet_name)

            # Print the status
            end_time = time.time()
            elapsed_time = end_time - start_time
            if elapsed_time < 1:
                time.sleep(1 - elapsed_time)
                elapsed_time = 1
            print(f"{company_name} data parsed in {(elapsed_time):.2f} seconds. [{progress_counter}/{number_of_results}]")

            # Reset the variables
            vacancy_name = ""
            company_name = ""
            phone = ""
            mail = ""
            website = ""

        # Go to the next page
        if start_with_element * page_size >= number_of_results:
            break
        start_with_element += 1
        url = hp.update_url_param(url, "page", start_with_element)

    # Save the data to the file
    df_util.save_df(df, main_dir, xlsx_file_name, xlsx_sheet_name)

    # Close the browser
    pm.close_playwright(browser)

    # Print the status
    print(f"Data parsing completed. {progress_counter} companies parsed.")

if __name__ == "__main__":
    import os

    current_dir = os.path.dirname(os.path.realpath(__file__))
    main_dir = os.path.dirname(current_dir)

    start(main_dir)

