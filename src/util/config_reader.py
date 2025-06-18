import json

def load_config(config_name: str, path: str = 'config/') -> dict:
    try:
        file_path = path + config_name
        data = None
        with open(file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as e: 
        raise

    except Exception as e:
        raise
    return data

def read_and_parse_config(config_name: str, path: str = 'config/') -> dict:
    config_data = load_config(config_name, path)
    return config_data


if __name__ == '__main__':
    import os
    print(os.getcwd())
    test = read_and_parse_config('logging.json')
    print(test['loggers'])