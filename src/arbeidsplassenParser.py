import utils.config_util as config_util
import utils.df_util as df_util
import utils.helper as hp

import utils.playwright_manager as pm
import utils.requests_manager as rm

import time
import re

def start(main_dir, start_with_page=1):
    print("Starting arbeidsplassenParser...")

    # Read configuration
    url, xlsx_file_name, xlsx_sheet_name, save_file_interval = config_util.get_all("arbeidsplassen", main_dir)
    save_file_interval = int(save_file_interval)

    # Create a data frame
    columns = ["Title", "Vacancy Name", "Company Name", "Language", "Phone", "Email", "Website"]
    df = df_util.create_df(columns)

    # First request
    page = rm.get_page(url)

    # Get the number of results
    number_of_results_text = rm.get_text(page, "h2[aria-live='polite']", "0")
    number_of_results = hp.get_number(number_of_results_text)
    page_size = len(rm.get_elements(page, "h2 a.navds-link"))
    last_page_text = rm.get_text(page, "li:nth-last-child(2) .navds-pagination__item .navds-label")
    last_page = hp.get_number(last_page_text)
    if last_page * page_size < number_of_results:
        number_of_results = last_page * page_size

    # Set first page
    start_with_element = (start_with_page - 1) * page_size
    url = hp.update_url_param(url, "from", start_with_page)

    progress_counter = start_with_element
    while True:
        # Get page content
        page = rm.get_page(url)

        # Get results
        results = rm.get_elements(page, "article.navds-hstack")

        # Parse results
        for result in results:
            # Set start time to calculate the time it takes to parse the page
            start_time = time.time()

            # Get vacancy title
            title = rm.get_text(result, "h2 a.navds-link")

            # Get vacancy URL
            company_url = rm.get_attribute(result, "href", "h2 a.navds-link")

            # Get the vacancy page
            vacancy_page = rm.get_page("https://arbeidsplassen.nav.no/" + company_url)

            # Get company name
            company_name = rm.get_text(vacancy_page, ".navds-hstack:first-child .navds-typo--semibold")

            info_box = rm.get_element(vacancy_page, ".ad-description-list.mb-8")
            keys = ["Stillingstittel", "Arbeidsspråk"]
            language = rm.find_values_by_keys_in_box(info_box, "dt", "dd", keys)

            # Get email
            main = rm.get_element(vacancy_page, "main#main-content")
            emails = (", ".join(rm.get_attribute(email, "href").replace("mailto:", "") for email in rm.get_elements(main, "a[href^='mailto']"))).strip()

            # Get the phone
            try:
                phones = rm.get_elements(main, ".navds-body-long .navds-hstack")
                phones_filtered = []
                for phone in phones:
                    if "@" not in phone.text:
                        phone = re.sub(r"\D", "", phone.text).strip()
                        phones_filtered.append(phone)
                if phones_filtered:
                    phone = ", ".join(phones_filtered)
                else:
                    phone = ""
            except:
                phone = ""
            phones = phone

            websites = rm.get_elements(main, ".ad-description-list .navds-body-long--medium .navds-link.navds-link--action")
            websites = [website["href"] for website in websites]
            websites = ", ".join(websites)


            # Add the row to the DataFrame
            row = {
                "Title": title,
                "Vacancy Name": title,
                "Company Name": company_name,
                "Language": language,
                "Phone": phones,
                "Email": emails,
                "Website": websites
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

        # Get the next page
        start_with_element += page_size
        if start_with_element >= number_of_results:
            break
        url = hp.update_url_param(url, "from", start_with_element)

    # Save the data to the file
    df_util.save_df(df, main_dir, xlsx_file_name, xlsx_sheet_name)

    # Print the status
    print(f"Data parsing completed. {progress_counter} companies parsed.")

if __name__ == "__main__":
    import os

    current_dir = os.path.dirname(os.path.realpath(__file__))
    main_dir = os.path.dirname(current_dir)

    start(main_dir)