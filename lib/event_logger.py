# coding=utf-8
import os
import json


def log_event(oms_event_to_log):
    # Переменная с именем файла журнала в формате .json
    log_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'log',
                            oms_event_to_log['oraEMNGEventSequenceId'] + '.json')

    if os.path.isfile(log_file) and os.path.getsize(log_file) > 0:
        # Если файл существует и непустой, считываем данные и добавляем новую информацию
        with open(log_file, 'r') as json_file:
            data = json.load(json_file)
            next_element = str(len(data) + 1)
            data[next_element] = oms_event_to_log

        with open(log_file, 'w') as json_file:
            json.dump(data, json_file, indent=3, sort_keys=True)
            json_file.write("\n")
    else:
        # Иначе создаем и добавляем первый элемент
        with open(log_file, 'w') as json_file:
            json.dump({1: oms_event_to_log}, json_file, indent=3, sort_keys=True)
            json_file.write("\n")
