import utils.config_util as config_util
import utils.df_util as df_util
import utils.helper as hp

import utils.playwright_manager as pm
import utils.requests_manager as rm

import time
import re

def start(main_dir, start_with_page=1):
    print("Starting stepstoneParser...")

    # Read configuration
    url, xlsx_file_name, xlsx_sheet_name, save_file_interval = config_util.get_all("stepstone", main_dir)
    save_file_interval = int(save_file_interval)

    # Launch the browser
    browser = pm.launch_playwright(main_dir)

    # Create a data frame
    columns = ["Vacancy Name", "Company", "Phone", "Email", "Website"]
    df = df_util.create_df(columns)

    # First request
    pm.goto_page(browser, url)

    # Wait for the page to load
    pm.wait_for(browser, "h2 a")

    # Get the current page
    page = pm.get_current_page(browser)

    # Get the number of results
    number_of_results_text = rm.get_text(page, ".at-facet-header-total-results", "0")
    number_of_results = hp.get_number(number_of_results_text)

    # Set first page
    url = hp.update_url_param(url, "page", start_with_page)

    page_size = len(rm.get_elements(page, "h2 a"))
    progress_counter = (start_with_page - 1) * page_size
    while True:
        # Get page content
        pm.goto_page(browser, url)

        # Wait for the page to load
        pm.wait_for(browser, "h2 a")

        # Get the current page
        page = pm.get_current_page(browser)

        # Get results
        results = rm.get_elements(page, "article[data-testid='job-item']")

        # Parse results
        for result in results:
            # Set start time to calculate the time it takes to parse the page
            start_time = time.time()

            # Get vacancy name
            company_name = rm.get_text(result, "[data-at='job-item-company-name'] span[data-genesis-element='BASE'] [data-genesis-element='TEXT']")

            # Get the company name
            vacancy_name = rm.get_text(result, "h2 a")

            # Get the vacancy url
            vacancy_url = rm.get_attribute(result, "href", "h2 a")

            # Get the vacancy page
            pm.goto_page(browser, "https://www.stepstone.de" + vacancy_url)

            # Wait for the page to load
            pm.wait_for(browser, "[data-at='job-ad-content']")

            vacancy_page = pm.get_current_page(browser)

            # Get the phone, email, website
            content = rm.get_text(vacancy_page, "[data-at='job-ad-content']")

            try:
                emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", content)
                email = ", ".join(emails)

                phones = re.findall(r"\b(?:\d[\s-]?){5,13}\b", content)
                phone = ", ".join(phones)

                websites = re.findall(r"(https?://[^\s]+|www\.[^\s]+)", content)
                website = ", ".join(websites)
            except:
                email = ""
                phone = ""
                website = ""

            # Add the data to the data frame
            row = {
                "Vacancy Name": vacancy_name,
                "Company": company_name,
                "Phone": phone,
                "Email": email,
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
            email = ""
            website = ""

        # Get the next page
        if start_with_page * page_size >= number_of_results:
            break
        start_with_page += 1
        url = hp.update_url_param(url, "page", start_with_page)

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