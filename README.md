# oem_snmp
Скрипт oem_snmp разработан для интеграции Oracle Enterprise Manager Cloud Control 13с и Zabbix.
Данный скрипт поддерживает два способа отправки сообщений в Zabbix, SNMPv1 trap и Zabbix trap. По умолчанию используются оба способа

# Установка
Для установки необходимо:

1. настроить способ оповещения OS Script в Oracle OEM, указав в качестве вызываемого скрипта ..\bin\snmp.py.
2. в каталоге ..\config скрипта скопировать все файлы настроек из файлов *.json.example в *.json
3. отредактировать emcli.json таким образом, чтобы он указывал на утилиту Emcli (обычно $OMS_HOME\bin\emcli) и URL Oracle OEM (https://oem.example.com:7803/em)
4. отредактировать snmp.json, указать значения групп hostname и zabbix
5. в каталоге ..\\.secure скрипта скопировать все файлы настроек из файлов *.json.example в *.json
6. отредактировать .emcli.json, указав имя пользователя и пароль пользователя Oracle OEM
7. отредактировать .zabbix.json, указав имя пользователя и пароль пользователя Zabbix