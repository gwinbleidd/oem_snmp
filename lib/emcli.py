import subprocess
import os
import json
import re
import datetime
import hashlib
import logging


class Emcli:
    def __init__(self):
        if os.path.isfile(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure',
                                       '.object.json')):
            self.__from_json()
        else:
            try:
                with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'config',
                                       'emcli.json'), 'r') as json_file:
                    self.config = json.load(json_file)
                    self.config.update({'config_checksum': hashlib.sha256(
                        os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'config',
                                     'emcli.json')).hexdigest()})
            except Exception:
                raise Exception('Error loading config.json')

            self.configured = self.__get_configured()
            self.last_configured_check = datetime.datetime.now()
            self.logged_in = self.__get_logged_in()
            self.last_logged_in_check = datetime.datetime.now()

        if self.__check_binary() is None:
            raise Exception('EMCLI binary not found')

    def __check_binary(self):
        def is_exe(fpath):
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

        file_path, file_name = os.path.split(self.config['bin'])

        if file_path:
            if is_exe(self.config['bin']):
                return self.config['bin']
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                exe_file = os.path.join(path, self.config['bin'])
                if is_exe(exe_file):
                    return exe_file

        return None

    def execute(self, *args):
        logging.debug('Executing %s' % ', '.join(args))
        params = list(args)
        params.insert(0, self.config['bin'].encode('ascii'))
        process = subprocess.Popen(params, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return process.stdout.readlines()

    def __get_configured(self):
        output = self.execute('status')
        for line in output:
            if re.match('^Status\s+: Configured$', line):
                logging.debug('Emcli configured')
                return True

        logging.debug('Emcli not configured')
        return False

    def __get_logged_in(self):
        try:
            with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure',
                                   '.emcli.json'), 'r') as json_file:
                self.user = json.load(json_file)
        except Exception:
            raise Exception('Error loading user.json')

        output = self.execute('login', '-username=%s' % self.user['name'], '-password=%s' % self.user['password'])
        self.user = None
        for line in output:
            if re.match('Login successful', line) or re.match('Error: Already logged in', line):
                logging.debug('Emcli logged in')
                return True

        logging.debug('Emcli not logged in')
        return False

    def logout(self):
        output = self.execute('logout')
        for line in output:
            if re.match('Logout successful', line) or re.match('Error: Already logged out', line):
                logging.debug('Emcli logged out')
                self.logged_in = False

    def __to_json(self):
        dump = {'config': self.config,
                'configured': {'state': str(self.configured),
                               'last_check': self.last_configured_check.strftime('%Y-%m-%d %H:%M:%S')},
                'logged_in': {'state': str(self.logged_in),
                              'last_check': self.last_logged_in_check.strftime('%Y-%m-%d %H:%M:%S')}}

        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure',
                               '.object.json'), 'w') as json_file:
            json.dump(dump, json_file, indent=4, sort_keys=True)

        os.chmod(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure',
                              '.object.json'), 0o600)

        logging.debug('Emcli object stored to json')

    def __from_json(self):
        try:
            with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure',
                                   '.object.json'), 'r') as object_file:
                dump = json.load(object_file)
        except Exception:
            raise Exception('Error loading object file')

        config_checksum = hashlib.sha256(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'config',
                         'emcli.json')).hexdigest()

        if config_checksum == dump['config']['config_checksum']:
            self.config = dump['config']
        else:
            try:
                with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'config',
                                       'emcli.json'), 'r') as json_file:
                    self.config = json.load(json_file)
                    self.config.update({'config_checksum': hashlib.sha256(
                        os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'config',
                                     'emcli.json')).hexdigest()})
            except Exception:
                raise Exception('Error loading config.json')

        last_logged_in_check = datetime.datetime.strptime(dump['logged_in']['last_check'], '%Y-%m-%d %H:%M:%S')
        last_configured_check = datetime.datetime.strptime(dump['configured']['last_check'], '%Y-%m-%d %H:%M:%S')

        now = datetime.datetime.now()
        if last_logged_in_check < now + datetime.timedelta(minutes=-45):
            self.logged_in = self.__get_logged_in()
            self.last_logged_in_check = now
        else:
            self.logged_in = True if dump['logged_in']['state'] == 'True' else False
            self.last_logged_in_check = last_logged_in_check
            if not self.logged_in:
                self.logged_in = self.__get_logged_in()
                self.last_logged_in_check = now

        if last_configured_check < now + datetime.timedelta(days=-1):
            self.configured = self.__get_configured()
            self.last_configured_check = now
        else:
            self.configured = True if dump['configured']['state'] == 'True' else False
            self.last_configured_check = last_configured_check

    def get_event_id(self, *args):
        result = []
        if len(args) == 1:
            query = 'SELECT DISTINCT E.EVENT_SEQ_ID FROM SYSMAN.MGMT$EVENTS E WHERE INCIDENT_ID = HEXTORAW(\'%s\')' % \
                    args[0]
            process = self.execute('list', '-sql=%s' % query, '-format=name:csv')

            for line in process:
                match_object = re.search('([ABCDEF0-9]{32})', line)
                if match_object:
                    result.append(match_object.group(1))

            if len(result) != 0:
                logging.debug('Event ID found, %s' % ', '.join(result))
                return result
            else:
                logging.debug('Event ID not found')
                return None
        elif len(args) == 2:
            query = 'SELECT DISTINCT E.EVENT_SEQ_ID FROM SYSMAN.MGMT$EVENTS E WHERE INCIDENT_ID = HEXTORAW (\'%s\') AND SEVERITY = \'%s\'' % (
                args[0], args[1])
            process = self.execute('list', '-sql=%s' % query, '-format=name:csv')

            for line in process:
                match_object = re.search('([ABCDEF0-9]{32})', line)
                if match_object:
                    result.append(match_object.group(1))

            if len(result) != 0:
                logging.debug('Event ID found, %s' % ', '.join(result))
                return result
            else:
                logging.debug('Event ID not found')
                return None

        return None

    def check_message_sent(self, *args):
        query = """SELECT COUNT (*)\
                   FROM   SYSMAN.MGMT$EVENTS  E\
                   JOIN SYSMAN.MGMT$ALERT_HISTORY A ON E.EVENT_ID = A.EVENT_INSTANCE_ID\
                   JOIN SYSMAN.MGMT$ALERT_NOTIF_LOG ANL\
                   ON A.VIOLATION_GUID = ANL.SOURCE_OBJ_GUID\
                   WHERE E.INCIDENT_ID = HEXTORAW (\'%s\') AND E.SEVERITY = \'%s\'""" % (args[0], args[1])
        process = self.execute('list', '-sql=%s' % query, '-format=name:csv')

        for line in process:
            match_object = re.search('(\d+)', line)
            if match_object:
                if match_object.group(1) != '0':
                    logging.debug('Message for ID %s found' % ', '.join(args))
                    return True
        logging.debug('Message for ID %s not found' % ', '.join(args))
        return False

    def __del__(self):
        if self.last_logged_in_check < datetime.datetime.now() + datetime.timedelta(minutes=-40):
            self.logout()
        self.__to_json()
        os.chmod(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure',
                              '.object.json'), 0o600)
