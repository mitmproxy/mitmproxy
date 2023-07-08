import json
from pathlib import Path
from test_readhar import file_to_flows


def requests_to_flows(file_list):
    for path_name in file_list:
        print(path_name)
        
        
        flows = file_to_flows(path_name)
        
        with open(f"har_files/{path_name.stem}.json", "w") as f:
            json.dump(flows, f, indent=4)


if __name__ == "__main__":
    here = Path(__file__).parent.absolute()
    file_list = here.glob("har_files/*.har")

    requests_to_flows(file_list)

