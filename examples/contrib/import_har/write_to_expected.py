import glob
import json

from test_readhar import file_to_flows


def requests_to_flows(file_list):
    for path_name in file_list:
        print(path_name)
        pathname = path_name.split("/")[2]
        expected_json = {"outcome": []}
        flows = file_to_flows(path_name)
        expected_json["outcome"] = flows
        with open(f"expected/{pathname}", "w") as f:
            json.dump(expected_json, f, indent=4)


if __name__ == "__main__":
    file_list = glob.glob("./har_files/*.har")
    print(file_list)
    requests_to_flows(file_list)

    # nested_tuple = ((1,2),(2,3),(3,4))
    # nested_list = [[1,1],[2,3],[3,4]]
    # print(nested_list == nested_tuple)

    # for i in range(10):
    #     flow = file_to_flows("./test.json")
    #     print(flow[0]['response']['contentHash'])
