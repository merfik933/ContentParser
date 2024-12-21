import utils.config_util as config_util
import utils.df_util as df_util
import utils.helper as hp

import utils.playwright_manager as pm
import utils.requests_manager as rm

import time

def start(main_dir, start_with_page=1):
    print("Starting sbbParser...")

    # Read configuration
    url, xlsx_file_name, xlsx_sheet_name, save_file_interval = config_util.get_all("SBB", main_dir)
    save_file_interval = int(save_file_interval)

    # Launch the browser
    browser = pm.launch_playwright(main_dir)

    # Create a data frame
    columns = ["Name", "Turnover", "Workers", "Maineskoor", "Krediidiskoor", "Email main", "Email juhatuseliige", "Email tootajad", "Phone main", "Phone juhatuseliige", "Phone tootajad", "EMTAK"]
    df = df_util.create_df(columns)

    # First request
    page = rm.get_page(url)

    # Get the number of results
    number_of_results_text = rm.get_text(page, ".c-result-count .js-result-count", "0")
    number_of_results = hp.get_number(number_of_results_text)

    # Set first page
    page_size = int(hp.get_url_param(url, "size", 20))
    start_with_element = (start_with_page - 1) * page_size
    url = hp.update_url_param(url, "from", start_with_element)

    progress_counter = start_with_element
    while True:
        # Get page content
        page = rm.get_page(url)

        # Get results
        results = rm.get_elements(page, ".l-list__item .c-company-block")

        # Parse results
        for result in results:
            # Set start time to calculate the time it takes to parse the page
            start_time = time.time()

            # Get company name
            company_name = rm.get_text(result, "h2.c-company-block__heading a")

            # Get company turnover, workers, maineskoor, krediidiskoor
            info_box = rm.get_element(result, ".c-company-block__info-list")
            keys = ["Krediidiskoor", "Maineskoor", "Töötajaid", "Prognooskäive"]
            krediidiskoor, maineskoor, workers, turnover = rm.find_values_by_keys_in_box(info_box, "dt", "dd", keys)

            # Format values
            maineskoor = hp.get_number(maineskoor)
            workers = hp.get_number(workers)
            turnover = hp.get_number(turnover)
            
            # Get company url
            company_url = rm.get_attribute(result, "href", "h2.c-company-block__heading a", None)
            company_url = company_url.replace("/meedia-arvamuslood", "/tootajad-palgad")

            # Get company page
            pm.goto_page(browser, company_url)

            # Get company emtaks, emails, phones
            info_box = pm.wait_for(browser, ".js-meta_data")
            emtaks = (", ".join([rm.get_text(emtak) for emtak in rm.get_elements(info_box, "div.emtak_str + div li a")])).strip()
            emails = (", ".join([rm.get_attribute(email, "href").replace("mailto:", "") for email in rm.get_elements(info_box, "a[href^='mailto:']")])).strip()
            phones = (", ".join([rm.get_attribute(phone, "href").replace("tel:", "") for phone in rm.get_elements(info_box, "a[href^='tel:']")])).strip()

            # Get the juhatuseliige data
            info_box = pm.wait_for(browser, ".js-employee-contacts__contact-list")
            emails_juhatuseliige = (", ".join([rm.get_attribute(email, "href").replace("mailto:", "") for email in rm.get_elements(info_box, "a[href^='mailto:']")])).strip()
            phones_juhatuseliige = (", ".join([rm.get_attribute(phone, "href").replace("tel:", "") for phone in rm.get_elements(info_box, "a[href^='tel:']")])).strip()

            # Get the juhatuseliige name to handle when the list changes
            juhatuseliige_name = rm.get_text(info_box, "h2 a")
            name_case = pm.get_locator(browser, f".js-employee-contacts__contact-list h2:has-text(\"{juhatuseliige_name}\")", None)

            # Swich to tootajad list
            is_clicked = pm.click_element(browser, "[for='employee-contacts-option-2']")

            # Wait for the tootajad list
            is_detached = False
            if name_case and is_clicked:
                is_detached = pm.wait_for_detached(browser, name_case, 3000)

            # Get the tootajad data
            if is_detached:
                info_box = pm.wait_for(browser, ".js-employee-contacts__contact-list")
                emails_tootajad = (", ".join([rm.get_attribute(email, "href").replace("mailto:", "") for email in rm.get_elements(info_box, "a[href^='mailto:']")])).strip()
                phones_tootajad = (", ".join([rm.get_attribute(phone, "href").replace("tel:", "") for phone in rm.get_elements(info_box, "a[href^='tel:']")])).strip()
            else:
                emails_tootajad = ""
                phones_tootajad = ""

            # Determine the turnover type
            if turnover == "":
                turnover_type = ""
            elif turnover <= 500000:
                turnover_type = 1
            elif turnover <= 1000000:
                turnover_type = 2
            elif turnover <= 10000000:
                turnover_type = 3
            else:
                turnover_type = 4

            # Determine the workers type
            if workers == "":
                workers_type = ""
            elif workers <= 10:
                workers_type = 4
            elif workers <= 100:
                workers_type = 5
            else:
                workers_type = 6

            # Determine the maineskoor type
            if maineskoor == "":
                maineskoor_type = ""
            elif maineskoor >= 1:
                maineskoor_type = 7
            else:
                maineskoor_type = 0

            # Determine the krediidiskoor type
            if krediidiskoor == "":
                krediidiskoor_type = ""
            elif krediidiskoor == "Usaldusväärne":
                krediidiskoor_type = 8
            elif krediidiskoor == "Piiripealne":
                krediidiskoor_type = 9
            else:
                krediidiskoor_type = 0

            # Add the data to the DataFrame
            row = {
                "Name": company_name,
                "Turnover": turnover_type,
                "Workers": workers_type,
                "Maineskoor": maineskoor_type,
                "Krediidiskoor": krediidiskoor_type,
                "Email main": emails,
                "Email juhatuseliige": emails_juhatuseliige,
                "Email tootajad": emails_tootajad,
                "Phone main": phones,
                "Phone juhatuseliige": phones_juhatuseliige,
                "Phone tootajad": phones_tootajad,
                "EMTAK": emtaks
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
            turnover = ""
            workers = ""
            maineskoor = ""
            krediidiskoor = ""
            emails = ""
            phones = ""
            emails_juhatuseliige = ""
            phones_juhatuseliige = ""
            emails_tootajad = ""
            phones_tootajad = ""
            emtaks = ""

        # Get the next page
        start_with_element += page_size
        url = hp.update_url_param(url, "from", start_with_element)
        if start_with_element >= number_of_results:
            break

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



        
            