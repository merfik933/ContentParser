import utils.config_util as config_util
import utils.df_util as df_util
import utils.helper as hp

import utils.playwright_manager as pm
import utils.requests_manager as rm

import time
import bs4

def start(main_dir, start_with_page=1):
    print("Starting werkParser...")

    # Read configuration
    url, xlsx_file_name, xlsx_sheet_name, save_file_interval, categories = config_util.get_all("werk", main_dir)
    save_file_interval = int(save_file_interval)
    categories = categories.split(",")

    # Create a dict with the categories
    categories_text = {
        "1" : "Metaal",
        "2" : "Bouw",
        "3" : "Vervoer",
        "4" : "Magazijn, opslag en bezorging",
        "5" : "Elektrotechniek",
        "6" : "Installatietechniek",
        "7" : "Planten",
        "8" : "Horeca",
        "9" : "Hout en meubileringsindustrie",
        "10" : "Textiel en mode",
        "11" : "Glas-, aardewerk en keramiek",
        "12" : "Schoonmaak",
        "13" : "Huishouding",
        "14" : "Industriële reiniging",
        "15" : "Agrarische ondersteuning",
        "16" : "Recreatie",
        "17" : "Dieren",
        "18" : "Visserij",
    }
    
    # Launch the browser
    browser = pm.launch_playwright(main_dir)
    
    # Create a data frame
    columns = ["Vacancy Name", "Company Name", "Language", "Mail", "Phone", "Website", "Category"]
    df = df_util.create_df(columns)

    for category in categories:
        category_text = categories_text[category]

        def goto_page(page_num=1):
            print(f"Getting the page {page_num} for the category {category_text}...")
            # Get the root page
            pm.goto_page(browser, url)

            # Wait for the page to load
            pm.wait_for(browser, "span.vacatures-zoeken__text")

            # Press the "Meer" button
            button = pm.click_element(browser, "[data-ta-id='vacature-zoeken__tegel-beroepsrichtingen'] [data-ta-id='vacature-zoeken__tegel-meer-minder-link']")

            # Wait for the page to load
            pm.wait_for(browser, "li.list__item:nth-child(15) .vacatures-zoeken__text")

            # Click on the category
            
            button = pm.get_locator(browser, "[data-ta-id='vacature-zoeken__tegel-beroepsrichtingen'] .vacatures-zoeken__text", search_text=category_text)
            pm.click_locator(button)

            # Wait for the page to load
            pm.wait_for(browser, "button.button.result-block__link")

            # Get the current page
            page = pm.get_current_page(browser)

            if page_num == 1:
                return page
            
            while True:
                # Go to the page
                last_page_num = int(rm.get_text(page, "li:nth-last-child(2) .pagination__button"))
                if page_num <= last_page_num:
                    # Click on the page button
                    page_button = pm.click_element(browser, f"li .pagination__button[aria-label='Ga naar pagina  {page_num}']")

                    # Wait for the page to load
                    pm.wait_for(browser, "button.button.result-block__link")
                    print(f"Page {page_num} loaded")

                    return pm.get_current_page(browser)

                # Click on the last page button
                page_button = pm.click_element(browser, "li:nth-last-child(2) .pagination__button")

                # Wait for the page to load
                pm.wait_for(browser, "button.button.result-block__link")
                print(f"Page {last_page_num} loaded")

                page = pm.get_current_page(browser) 

                time.sleep(1) 
            
        page = goto_page(start_with_page)
        current_page_num = start_with_page

        # Get the number of results
        number_of_results_text = rm.get_text(page, ".vacatures-zoeken__results-header h2")
        number_of_results = hp.get_number(number_of_results_text)

        progress_counter = 0
        while True:
            page = pm.get_current_page(browser)

            # Get results
            results = rm.get_elements(page, ".result-block__link")

            if not results:
                print(f"Error while getting results. Retrying... Get the page {current_page_num} again.")
                goto_page(current_page_num)
                continue

            results_len = len(results)

            # Parse results
            for i in range(results_len):
                # Set start time to calculate the time it takes to parse the page
                start_time = time.time()

                # Get vacancy page
                result_button = pm.get_elements(browser, "button.button.result-block__link")[i]
                pm.click_locator(result_button)

                # Wait for the page to load
                pm.wait_for(browser, "h2.vacature-detail__title")

                # Get the current page without scripts and styles to speed up the parsing
                browser.evaluate("""
                    Array.from(document.querySelectorAll('script, link[rel="stylesheet"], style')).forEach(el => el.remove());
                """)
                html = browser.content()
                soup = bs4.BeautifulSoup(html, "html.parser")
                vacancy_page = soup

                # Get vacancy name
                vacancy_name = rm.get_text(vacancy_page, "h2.vacature-detail__title")
                company_name = rm.get_text(vacancy_page, "div.vacature-detail > p")

                # Get the phone, mail and website
                info_box = rm.get_element(vacancy_page, ".box:has([labelid='titel-contact-gegevens'])")
                keys = ["Telefoonnummer", "E-mailadres", "Website"]
                phone, mail, website = rm.find_values_by_keys_in_box(info_box, "dt", "dd", keys)

                # Get the language
                language = rm.get_text(vacancy_page, "[groupid='taal']")

                # Add the row to the data frame
                row = {
                    "Vacancy Name": vacancy_name,
                    "Company Name": company_name,
                    "Language": language,
                    "Mail": mail,
                    "Phone": phone,
                    "Website": website,
                    "Category": category_text
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
                print(f"{vacancy_name} data parsed in {(elapsed_time):.2f} seconds. [{progress_counter}/{number_of_results}]")

                # Reset the variables
                vacancy_name = ""
                company_name = ""
                language = ""
                mail = ""
                phone = ""
                website = ""
                
                # Go back to the previous page
                browser.go_back()

                # Wait for the page to load
                pm.wait_for(browser, "button.button.result-block__link")


            # Get the next page
            print(f"Page {current_page_num} parsed. Getting the next page...")
            button = pm.click_element(browser, "li:has(.pagination__button--active) + li button")
            current_page_num += 1
            if button == None:
                break

            # Wait for the page to load
            time.sleep(3)
    
    # Save the data to the file
    df_util.save_df(df, main_dir, xlsx_file_name, xlsx_sheet_name)

    # Close the browser
    pm.close_playwright(browser)

    # Print the status
    print(f"Data parsing completed")

if __name__ == "__main__":
    import os

    current_dir = os.path.dirname(os.path.realpath(__file__))
    main_dir = os.path.dirname(current_dir)

    start(main_dir, 10)