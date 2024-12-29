import sbbParser
import cvkeskusParser
import cvParser
import layboardParser
import arbeidsplassenParser
import stepstoneParser
import arbetsformedlingenParser
import werkParser

import os
import sys

def main():
    # Display welcome message
    print("Parser v1.1")
    input("Press Enter to continue...")

    # Available parsers
    parsers = {
        "1" : "SBB",
        "2" : "cvkeskus",
        "3" : "cv",
        "4" : "layboard",
        "5" : "arbeidsplassen",
        "6" : "stepstone",
        "7" : "arbetsformedlingen",
        "8" : "werk",
    }

    # Display available parsers
    for key, value in parsers.items():
        print(f"{key}. {value}")

    # Get main directory
    if getattr(sys, 'frozen', False):
        main_dir = os.path.dirname(sys.executable)
    else:
        current_dir = os.path.dirname(os.path.realpath(__file__))
        main_dir = os.path.dirname(current_dir)

    def get_parser():
        # Select parser
        parser_id = input("Select parser (enter number): ")

        # Validate parser
        if parser_id not in parsers:
            print("Invalid parser")
            print("Try again")
            return get_parser()
        parser_name = parsers[parser_id]
        print(f"Selected parser: {parser_name}")
        return parser_name
    
    parser_name = get_parser()

    def get_start_with_value():
        # Get start with value
        start_with = input("Press Enter to continue or enter a page number to start with: ")
        if start_with.strip() == "":
            return 1
        try:
            return int(start_with)
        except:
            print("Invalid value")
            print("Try again")
            return get_start_with_value()
    
    start_with = get_start_with_value()

    # Start parser
    if parser_name == "SBB":
        sbbParser.start(main_dir, start_with)
    elif parser_name == "cvkeskus":
        cvkeskusParser.start(main_dir, start_with)
    elif parser_name == "cv":
        cvParser.start(main_dir, start_with)
    elif parser_name == "layboard":
        layboardParser.start(main_dir, start_with)
    elif parser_name == "arbeidsplassen":
        arbeidsplassenParser.start(main_dir, start_with)
    elif parser_name == "stepstone":
        stepstoneParser.start(main_dir, start_with)
    elif parser_name == "arbetsformedlingen":
        arbetsformedlingenParser.start(main_dir, start_with)
    elif parser_name == "werk":
        werkParser.start(main_dir, start_with)

    input("Press Enter to exit...")
    


if __name__ == "__main__":
    main()