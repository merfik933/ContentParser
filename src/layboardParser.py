import utils.config_util as config_util
import utils.df_util as df_util
import utils.helper as hp

import utils.playwright_manager as pm
import utils.requests_manager as rm

import time

def start(main_dir, start_with_page=1):
    print("Starting layboardParser...")

    # Read configuration
    url, xlsx_file_name, xlsx_sheet_name, save_file_interval = config_util.get_all("layboard", main_dir)
    save_file_interval = int(save_file_interval)

    # Launch the browser
    browser = pm.launch_playwright(main_dir)

    # Create a data frame
    columns = ["Company Name", "Type", "Location", "Vacancy Count", "Feedback count", "Website", "Phone"]
    df = df_util.create_df(columns)

    # First request
    pm.goto_page(browser, url)

    # Wait for the page to load
    pm.wait_for(browser, ".js-card")

    # Get the current page
    page = pm.get_current_page(browser)

    # Get the number of results
    number_of_results_text = rm.get_text(page, "p:has(.count-badge)", "0")
    number_of_results = hp.get_number(number_of_results_text)

    # Set first page
    url = hp.update_url_param(url, "page", start_with_page)

    page_size = len(rm.get_elements(page, ".js-card"))
    progress_counter = (start_with_page - 1) * page_size
    while True:
        # Get page content
        pm.goto_page(browser, url)

        # Wait for the page to load
        pm.wait_for(browser, ".js-card")

        # Get the current page
        page = pm.get_current_page(browser)

        # Get results
        results = rm.get_elements(page, ".js-card")

        # Parse results
        for result in results:
            # Set start time to calculate the time it takes to parse the page
            start_time = time.time()

            # Get company name, vacancy count, feedback count
            company_name = rm.get_text(result, ".job-card__title")
            vacancy_text = rm.get_text(result, "a.simple-blue-link:last-child")
            vacancy_count = hp.get_number(vacancy_text)
            feedback_text = rm.get_text(result, "a.simple-blue-link:nth-last-child(2)")
            feedback_count = hp.get_number(feedback_text)

            # Get the company url
            company_url = rm.get_attribute(result, "href", "a:has(.job-card__title)")
            
            # Get the company page
            company_page = rm.get_page("https://layboard.com" + company_url)

            # Get the company type, location, website, phone
            info_box = rm.get_element(company_page, ".col-lg-3 .soc-side-body")
            company_type = rm.get_text(info_box, ".soc-text-block-1 p:first-child span")
            location = rm.get_text(info_box, "p:has(.fa-map-marker-alt)")
            phone = rm.get_text(info_box, "p:has(.fa-phone-alt)")
            website = rm.get_text(info_box, "p:has(.fa-link)")

            # Add the data to the DataFrame
            row = {
                "Company Name": company_name,
                "Type": company_type,
                "Location": location,
                "Vacancy Count": vacancy_count,
                "Feedback count": feedback_count,
                "Website": website,
                "Phone": phone
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
            company_name = ""
            vacancy_count = ""
            feedback_count = ""
            company_type = ""
            location = ""
            phone = ""
            website = ""

        if start_with_page * page_size >= number_of_results:
            break
        start_with_page += 1
        url = hp.update_url_param(url, "page", start_with_page)

    # Save the data to the file
    df_util.save_df(df, main_dir, xlsx_file_name, xlsx_sheet_name)

    # Print the status
    print(f"Data parsing completed. {progress_counter} companies parsed.")


if __name__ == "__main__":
    import os

    current_dir = os.path.dirname(os.path.realpath(__file__))
    main_dir = os.path.dirname(current_dir)

    start(main_dir)
